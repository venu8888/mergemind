"""Source code retrieval service with cryptographic Git blob SHA-1 integrity verification."""

import hashlib
import logging
from dataclasses import dataclass
from enum import StrEnum

from app.services.github.classifier import FileCategory, FileClassifier
from app.services.github.client import GitHubClient
from app.services.github.exceptions import GitHubAPIError

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB hard limit


def compute_git_blob_hash(content: bytes) -> str:
    """Compute the Git object SHA-1 hash for blob content.

    Git format: sha1("blob " + str(len(content)) + "\0" + content)
    """
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()  # nosec B324


class RetrievalStatus(StrEnum):
    """Integrity status taxonomy for retrieved source files."""

    VERIFIED_COMPLETE = "VERIFIED_COMPLETE"
    RETRIEVAL_INCOMPLETE = "RETRIEVAL_INCOMPLETE"
    HASH_MISMATCH = "HASH_MISMATCH"
    EXCLUDED_OVERSIZED = "EXCLUDED_OVERSIZED"
    BINARY_UNSUPPORTED = "BINARY_UNSUPPORTED"
    DELETED = "DELETED"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


@dataclass
class RetrievedFile:
    """Metadata and content of an independently verified repository source file."""

    path: str
    status: RetrievalStatus
    blob_sha: str | None = None
    size_bytes: int = 0
    content: str | None = None
    raw_bytes: bytes | None = None
    category: FileCategory = FileCategory.OTHER
    error_message: str | None = None


class SourceRetriever:
    """Retrieves source files for PR analysis with cryptographic tree & blob verification."""

    def __init__(self, client: GitHubClient):
        self.client = client

    async def get_commit_tree(
        self,
        repo_full_name: str,
        commit_sha: str,
    ) -> dict[str, dict[str, any]]:
        """Fetch git tree mapping path -> {'sha': blob_sha, 'size': size, 'mode': mode, 'type': type}.

        If the recursive tree response is truncated (GitHub truncates trees > 100,000 entries
        or > 7 MB), it logs a warning and flags truncated status.
        """
        tree_resp = await self.client.get_tree(repo_full_name, commit_sha, recursive=True)
        is_truncated = tree_resp.get("truncated", False)
        tree_items = tree_resp.get("tree", [])

        tree_map: dict[str, dict[str, any]] = {}
        for item in tree_items:
            path = item.get("path")
            if path:
                tree_map[path] = {
                    "sha": item.get("sha"),
                    "size": item.get("size"),
                    "type": item.get("type"),
                    "mode": item.get("mode"),
                }

        if is_truncated:
            logger.warning(
                "Git tree for %s at %s was truncated by GitHub API. Falling back to targeted tree queries.",
                repo_full_name,
                commit_sha,
            )
            tree_map["__truncated__"] = True

        return tree_map

    async def resolve_file_tree_entry(
        self,
        repo_full_name: str,
        commit_sha: str,
        path: str,
        cached_tree: dict[str, any] | None = None,
    ) -> dict[str, any] | None:
        """Resolve a specific file's tree entry, falling back to directory-by-directory tree if tree was truncated."""
        if cached_tree and not cached_tree.get("__truncated__", False):
            return cached_tree.get(path)

        # If cached tree is present and has the item, return it
        if cached_tree and path in cached_tree and path != "__truncated__":
            return cached_tree[path]

        # Path-specific directory traversal fallback
        parts = path.strip("/").split("/")
        current_sha = commit_sha

        for i, part in enumerate(parts):
            dir_resp = await self.client.get_tree(repo_full_name, current_sha, recursive=False)
            items = dir_resp.get("tree", [])
            match = next((it for it in items if it.get("path") == part), None)
            if not match:
                return None

            is_last = i == len(parts) - 1
            if is_last:
                return {
                    "sha": match.get("sha"),
                    "size": match.get("size"),
                    "type": match.get("type"),
                    "mode": match.get("mode"),
                }
            else:
                if match.get("type") != "tree":
                    return None
                current_sha = match.get("sha")

        return None

    async def retrieve_file(
        self,
        repo_full_name: str,
        commit_sha: str,
        path: str,
        expected_blob_sha: str | None = None,
        expected_size: int | None = None,
    ) -> RetrievedFile:
        """Retrieve and cryptographically verify a single file at an immutable commit SHA."""
        category = FileClassifier.classify(path)

        # 1. Oversized check from tree metadata
        if expected_size is not None and expected_size > MAX_FILE_SIZE_BYTES:
            return RetrievedFile(
                path=path,
                status=RetrievalStatus.EXCLUDED_OVERSIZED,
                blob_sha=expected_blob_sha,
                size_bytes=expected_size,
                category=category,
            )

        # 2. Binary unsupported
        if category == FileCategory.BINARY_UNSUPPORTED:
            return RetrievedFile(
                path=path,
                status=RetrievalStatus.BINARY_UNSUPPORTED,
                blob_sha=expected_blob_sha,
                size_bytes=expected_size or 0,
                category=category,
            )

        # 3. Retrieve raw bytes
        try:
            if expected_blob_sha:
                blob_data = await self.client.get_blob(repo_full_name, expected_blob_sha)
                import base64

                encoding = blob_data.get("encoding")
                if encoding == "base64":
                    raw_bytes = base64.b64decode(blob_data.get("content", ""))
                else:
                    raw_bytes = (blob_data.get("content") or "").encode("utf-8")
            else:
                raw_bytes = await self.client.get_raw_content(repo_full_name, path, commit_sha)
        except GitHubAPIError as exc:
            if exc.status_code == 404:
                return RetrievedFile(
                    path=path,
                    status=RetrievalStatus.NOT_FOUND,
                    category=category,
                    error_message="File or blob not found on GitHub",
                )
            return RetrievedFile(
                path=path,
                status=RetrievalStatus.ERROR,
                category=category,
                error_message=str(exc),
            )

        actual_len = len(raw_bytes)

        # 4. Check size limit
        if actual_len > MAX_FILE_SIZE_BYTES:
            return RetrievedFile(
                path=path,
                status=RetrievalStatus.EXCLUDED_OVERSIZED,
                blob_sha=expected_blob_sha,
                size_bytes=actual_len,
                category=category,
            )

        # 5. Check incomplete stream / truncated transfer
        if expected_size is not None and actual_len != expected_size:
            return RetrievedFile(
                path=path,
                status=RetrievalStatus.RETRIEVAL_INCOMPLETE,
                blob_sha=expected_blob_sha,
                size_bytes=actual_len,
                category=category,
                error_message=f"Received {actual_len} bytes, expected {expected_size} bytes",
            )

        # 6. Cryptographic Git Blob SHA verification
        computed_sha = compute_git_blob_hash(raw_bytes)
        if expected_blob_sha and computed_sha != expected_blob_sha:
            return RetrievedFile(
                path=path,
                status=RetrievalStatus.HASH_MISMATCH,
                blob_sha=computed_sha,
                size_bytes=actual_len,
                category=category,
                error_message=f"Git blob hash mismatch: computed {computed_sha}, expected {expected_blob_sha}",
            )

        # 7. Decode text content
        # Check for binary null byte heuristic
        if b"\x00" in raw_bytes[:1024]:
            return RetrievedFile(
                path=path,
                status=RetrievalStatus.BINARY_UNSUPPORTED,
                blob_sha=computed_sha,
                size_bytes=actual_len,
                category=FileCategory.BINARY_UNSUPPORTED,
            )

        try:
            text_content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text_content = raw_bytes.decode("latin-1", errors="replace")

        return RetrievedFile(
            path=path,
            status=RetrievalStatus.VERIFIED_COMPLETE,
            blob_sha=computed_sha,
            size_bytes=actual_len,
            content=text_content,
            raw_bytes=raw_bytes,
            category=category,
        )

    async def retrieve_files_for_diff(
        self,
        repo_full_name: str,
        commit_sha: str,
        file_paths: list[str],
    ) -> dict[str, RetrievedFile]:
        """Retrieve source files corresponding to changed diff paths at an immutable commit SHA."""
        tree = await self.get_commit_tree(repo_full_name, commit_sha)
        results: dict[str, RetrievedFile] = {}

        for path in file_paths:
            entry = await self.resolve_file_tree_entry(repo_full_name, commit_sha, path, tree)
            if not entry:
                # File may be deleted or does not exist at this commit
                results[path] = RetrievedFile(
                    path=path,
                    status=RetrievalStatus.DELETED,
                    category=FileClassifier.classify(path),
                )
                continue

            blob_sha = entry.get("sha")
            size = entry.get("size")
            file_result = await self.retrieve_file(
                repo_full_name=repo_full_name,
                commit_sha=commit_sha,
                path=path,
                expected_blob_sha=blob_sha,
                expected_size=size,
            )
            results[path] = file_result

        return results
