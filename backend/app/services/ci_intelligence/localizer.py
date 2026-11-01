"""Root-cause localizer correlating stack traces and logs to repository files."""

from __future__ import annotations

from typing import Any


class CIRootCauseLocalizer:
    """Localizes the probable root cause of a CI failure to specific repository files and lines."""

    def localize(
        self,
        failure_category: str,
        primary_error: str,
        localized_files: list[dict[str, Any]],
        changed_files: list[str] | None = None,
    ) -> dict[str, Any]:
        """Correlate extracted error locations with changed files in the commit or PR."""
        changed_set = set(changed_files or [])
        primary_location: dict[str, Any] | None = None
        intersecting_locations: list[dict[str, Any]] = []

        for loc in localized_files:
            file_path = loc.get("file_path", "")
            # Check exact match or basename match with changed files
            if file_path in changed_set or any(cf.endswith(file_path) for cf in changed_set):
                intersecting_locations.append(loc)

        if intersecting_locations:
            primary_location = intersecting_locations[0]
        elif localized_files:
            primary_location = localized_files[0]

        root_cause_analysis = {
            "category": failure_category,
            "primary_error": primary_error,
            "primary_file": primary_location.get("file_path") if primary_location else None,
            "primary_line": primary_location.get("line_number") if primary_location else None,
            "enclosing_symbol": primary_location.get("enclosing_symbol")
            if primary_location
            else None,
            "direct_match_with_diff": bool(intersecting_locations),
            "all_extracted_locations": localized_files,
        }

        # Synthesize advisory AI hypothesis (explicitly marked as advisory, NOT confirmed fact)
        advisory_hypothesis = self._generate_advisory_hypothesis(
            failure_category, primary_error, primary_location
        )

        return {
            "root_cause_analysis": root_cause_analysis,
            "ai_advisory_hypothesis": advisory_hypothesis,
        }

    def _generate_advisory_hypothesis(
        self,
        category: str,
        error: str,
        loc: dict[str, Any] | None,
    ) -> str:
        """Construct an advisory, non-authoritative hypothesis for developer inspection."""
        file_hint = f" in `{loc['file_path']}` (line {loc['line_number']})" if loc else ""

        if category == "TEST_FAILURE":
            return (
                f"[ADVISORY HYPOTHESIS] Unit test assertion failure observed{file_hint}. "
                f"Error signature indicates expected return value or invariant mismatch: '{error}'. "
                f"Review recent implementation changes around this assertion."
            )
        elif category == "LINT_ERROR":
            return (
                f"[ADVISORY HYPOTHESIS] Static linter or syntax rule violation detected{file_hint}. "
                f"Rule message: '{error}'. Ensure code matches formatting conventions and AST grammar."
            )
        elif category == "SECURITY_VIOLATION":
            return (
                f"[ADVISORY HYPOTHESIS] Static security vulnerability flag raised{file_hint}. "
                f"Vulnerability indicator: '{error}'. Input sanitization or query parameterization recommended."
            )
        elif category == "DEPENDENCY_CONFLICT":
            return (
                f"[ADVISORY HYPOTHESIS] Missing module or package version resolution failure. "
                f"Indicator: '{error}'. Check pyproject.toml / requirements.txt dependencies."
            )
        elif category == "TIMEOUT":
            return (
                "[ADVISORY HYPOTHESIS] Job execution exceeded runtime threshold. "
                "Potential causes: unbounded loop, deadlocked resource, or slow external network call."
            )
        elif category == "INFRASTRUCTURE_FAILURE":
            return (
                "[ADVISORY HYPOTHESIS] Infrastructure or environment connectivity issue. "
                "This failure is unlikely to be caused by code defects; runner diagnostics recommended."
            )
        else:
            return (
                f"[ADVISORY HYPOTHESIS] Build or compilation failed{file_hint}. "
                f"Trace: '{error}'. Inspect build configuration and environment dependencies."
            )
