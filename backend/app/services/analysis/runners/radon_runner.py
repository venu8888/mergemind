"""Code maintainability and cyclomatic complexity runner."""

from __future__ import annotations

import ast
import logging
import os
import time
from typing import Any

from app.services.analysis.base import (
    AnalysisResult,
    BaseAnalysisRunner,
    CheckStatus,
    CheckType,
    RawFinding,
)

logger = logging.getLogger(__name__)


class RadonRunner(BaseAnalysisRunner):
    """Computes AST-based cyclomatic complexity, docstring coverage, and maintainability metrics."""

    tool_name: str = "radon"
    check_type: CheckType = CheckType.MAINTAINABILITY

    def _compute_complexity(self, node: ast.AST) -> int:
        """Calculate McCabe Cyclomatic Complexity for an AST function/method node."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                ast.If
                | ast.While
                | ast.For
                | ast.AsyncFor
                | ast.ExceptHandler
                | ast.With
                | ast.AsyncWith
                | ast.Assert,
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp):
                complexity += len(child.generators)
        return complexity

    async def run(
        self,
        source_dir: str,
        target_files: list[str] | None = None,
        config_override: dict[str, Any] | None = None,
    ) -> AnalysisResult:
        start_time = time.perf_counter()

        python_files = []
        if target_files:
            for f in target_files:
                abs_f = os.path.join(source_dir, f) if not os.path.isabs(f) else f
                if os.path.exists(abs_f) and f.endswith(".py"):
                    python_files.append(abs_f)
        else:
            for root, _, files in os.walk(source_dir):
                for f in files:
                    if f.endswith(".py"):
                        python_files.append(os.path.join(root, f))

        if not python_files:
            return AnalysisResult(
                check_type=self.check_type,
                status=CheckStatus.SKIPPED,
                duration_ms=0,
                tool_name=self.tool_name,
                raw_stdout="No Python files found for maintainability analysis",
            )

        total_functions = 0
        documented_functions = 0
        complex_functions = 0  # Complexity >= 15
        total_loc = 0
        findings: list[RawFinding] = []

        for fpath in python_files:
            rel_path = os.path.relpath(fpath, source_dir).replace("\\", "/")
            try:
                with open(fpath, "rb") as fp:
                    content_bytes = fp.read()
                content = content_bytes.decode("utf-8", errors="replace")
                total_loc += len(content.splitlines())

                tree = ast.parse(content, filename=fpath)
            except Exception as err:
                logger.debug("Failed to parse AST for %s: %s", rel_path, err)
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                    total_functions += 1
                    docstring = ast.get_docstring(node)
                    if docstring and docstring.strip():
                        documented_functions += 1

                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    score = self._compute_complexity(node)
                    if score >= 10:
                        complex_functions += 1
                        grade = "C" if score <= 15 else ("D" if score <= 30 else "F")
                        findings.append(
                            RawFinding(
                                rule_id="MAINTAINABILITY_COMPLEXITY",
                                message=f"Function '{node.name}' has high cyclomatic complexity of {score} (Grade {grade}). Refactoring recommended.",
                                severity="LOW" if score < 15 else "MEDIUM",
                                file_path=rel_path,
                                start_line=node.lineno,
                                end_line=node.end_lineno or node.lineno,
                                category="MAINTAINABILITY",
                                enclosing_symbol=node.name,
                                is_blocking=False,
                            )
                        )

        docstring_coverage = (
            (documented_functions / total_functions * 100.0) if total_functions > 0 else 100.0
        )
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        metrics = {
            "total_loc": total_loc,
            "total_definitions": total_functions,
            "documented_definitions": documented_functions,
            "docstring_coverage_pct": round(docstring_coverage, 2),
            "complex_functions_count": complex_functions,
        }

        return AnalysisResult(
            check_type=self.check_type,
            status=CheckStatus.PASSED,
            duration_ms=duration_ms,
            findings=findings,
            raw_stdout=f"Analyzed {len(python_files)} files ({total_loc} LOC). Docstring coverage: {docstring_coverage:.1f}%. Highly complex functions: {complex_functions}.",
            tool_name=self.tool_name,
            tool_version="6.0.1",
            metrics=metrics,
        )
