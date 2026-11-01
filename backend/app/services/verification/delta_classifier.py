"""Delta finding classification engine comparing base commit against pull request head."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.services.analysis.base import RawFinding
from app.services.github.diff_parser import FileDiff
from app.services.verification.fingerprint import compute_finding_fingerprint

logger = logging.getLogger(__name__)


@dataclass
class ClassifiedFinding:
    """Finding augmented with delta classification status."""

    finding: RawFinding
    fingerprint: str
    delta_status: str  # INTRODUCED_NEW, EXISTING_BASELINE, FIXED_IN_PR, PRE_EXISTING_MODIFIED, AMBIGUOUS_MODIFIED_CONTEXT
    matched_base_fingerprint: str | None = None


@dataclass
class DeltaClassificationResult:
    """Aggregated delta classification results across a pull request."""

    classified_findings: list[ClassifiedFinding] = field(default_factory=list)
    introduced_count: int = 0
    existing_baseline_count: int = 0
    fixed_count: int = 0
    pre_existing_modified_count: int = 0
    ambiguous_count: int = 0
    summary: dict[str, Any] = field(default_factory=dict)


class FindingDeltaClassifier:
    """Compares baseline findings against PR head findings using fingerprints and diff ranges."""

    def classify(
        self,
        base_findings: list[RawFinding],
        head_findings: list[RawFinding],
        diff_files: list[FileDiff] | None = None,
    ) -> DeltaClassificationResult:
        # 1. Index base findings by fingerprint and by (rule_id, file_path)
        base_by_fingerprint: dict[str, list[RawFinding]] = {}
        base_by_rule_file: dict[tuple[str, str], list[RawFinding]] = {}

        for bf in base_findings:
            fp = compute_finding_fingerprint(
                rule_id=bf.rule_id,
                message=bf.message,
                enclosing_symbol=bf.enclosing_symbol,
                code_snippet=bf.code_snippet,
            )
            base_by_fingerprint.setdefault(fp, []).append(bf)
            key = (bf.rule_id, bf.file_path)
            base_by_rule_file.setdefault(key, []).append(bf)

        # Build modified line ranges per file from diff_files if available
        modified_lines_by_file: dict[str, set[int]] = {}
        if diff_files:
            for fd in diff_files:
                target_path = (
                    getattr(fd, "new_path", None)
                    or getattr(fd, "target_path", None)
                    or getattr(fd, "old_path", None)
                    or ""
                )
                lines = set()
                for chunk in fd.chunks:
                    for dline in chunk.lines:
                        l_no = getattr(dline, "new_line_number", None) or getattr(
                            dline, "target_line_no", None
                        )
                        if l_no is not None:
                            lines.add(l_no)
                modified_lines_by_file[target_path] = lines

        classified: list[ClassifiedFinding] = []
        matched_base_fps: set[str] = set()

        introduced_count = 0
        existing_baseline_count = 0
        pre_existing_modified_count = 0
        ambiguous_count = 0

        # 2. Classify each head finding
        for hf in head_findings:
            h_fp = compute_finding_fingerprint(
                rule_id=hf.rule_id,
                message=hf.message,
                enclosing_symbol=hf.enclosing_symbol,
                code_snippet=hf.code_snippet,
            )

            # Match attempt 1: Exact fingerprint match
            if h_fp in base_by_fingerprint and base_by_fingerprint[h_fp]:
                matched_base_fps.add(h_fp)
                # Check if file lines were touched
                mod_lines = modified_lines_by_file.get(hf.file_path, set())
                is_line_touched = (
                    (hf.start_line in mod_lines) if hf.start_line is not None else False
                )

                if is_line_touched:
                    delta_status = "PRE_EXISTING_MODIFIED"
                    pre_existing_modified_count += 1
                else:
                    delta_status = "EXISTING_BASELINE"
                    existing_baseline_count += 1

                classified.append(
                    ClassifiedFinding(
                        finding=hf,
                        fingerprint=h_fp,
                        delta_status=delta_status,
                        matched_base_fingerprint=h_fp,
                    )
                )
                continue

            # Match attempt 2: Same rule and same file with line shift
            # If the file is heavily modified (>5 chunks), line shifts cannot be established with confidence.
            is_heavily_modified = diff_files and any(
                (getattr(fd, "new_path", None) or getattr(fd, "target_path", None)) == hf.file_path
                and len(getattr(fd, "chunks", [])) > 5
                for fd in diff_files
            )
            rule_file_key = (hf.rule_id, hf.file_path)
            if (
                not is_heavily_modified
                and rule_file_key in base_by_rule_file
                and base_by_rule_file[rule_file_key]
            ):
                candidates = base_by_rule_file[rule_file_key]
                best_match = None
                for c in candidates:
                    c_fp = compute_finding_fingerprint(
                        c.rule_id, c.message, c.enclosing_symbol, c.code_snippet
                    )
                    if c_fp not in matched_base_fps:
                        best_match = (c, c_fp)
                        break

                if best_match:
                    matched_base_fps.add(best_match[1])
                    classified.append(
                        ClassifiedFinding(
                            finding=hf,
                            fingerprint=h_fp,
                            delta_status="PRE_EXISTING_MODIFIED",
                            matched_base_fingerprint=best_match[1],
                        )
                    )
                    pre_existing_modified_count += 1
                    continue

            # Match attempt 3: Ambiguity detection
            # If the file was heavily modified and the rule matches across another file or symbol
            if diff_files and any(
                (getattr(fd, "new_path", None) or getattr(fd, "target_path", None)) == hf.file_path
                and len(fd.chunks) > 5
                for fd in diff_files
            ):
                delta_status = "AMBIGUOUS_MODIFIED_CONTEXT"
                ambiguous_count += 1
            else:
                delta_status = "INTRODUCED_NEW"
                introduced_count += 1

            classified.append(
                ClassifiedFinding(
                    finding=hf,
                    fingerprint=h_fp,
                    delta_status=delta_status,
                    matched_base_fingerprint=None,
                )
            )

        # 3. Detect FIXED_IN_PR findings (in base, but absent in head within touched files)
        touched_files = set(modified_lines_by_file.keys())
        fixed_count = 0
        for bf in base_findings:
            bf_fp = compute_finding_fingerprint(
                bf.rule_id, bf.message, bf.enclosing_symbol, bf.code_snippet
            )
            if bf_fp not in matched_base_fps:
                if bf.file_path in touched_files:
                    fixed_count += 1
                    classified.append(
                        ClassifiedFinding(
                            finding=bf,
                            fingerprint=bf_fp,
                            delta_status="FIXED_IN_PR",
                            matched_base_fingerprint=bf_fp,
                        )
                    )

        summary = {
            "introduced_count": introduced_count,
            "existing_baseline_count": existing_baseline_count,
            "fixed_count": fixed_count,
            "pre_existing_modified_count": pre_existing_modified_count,
            "ambiguous_count": ambiguous_count,
            "total_head_findings": len(head_findings),
        }

        return DeltaClassificationResult(
            classified_findings=classified,
            introduced_count=introduced_count,
            existing_baseline_count=existing_baseline_count,
            fixed_count=fixed_count,
            pre_existing_modified_count=pre_existing_modified_count,
            ambiguous_count=ambiguous_count,
            summary=summary,
        )
