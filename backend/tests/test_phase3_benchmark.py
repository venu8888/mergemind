"""50-PR Synthetic and Ground-Truth Delta Classification Benchmark Suite.

Evaluates empirical Precision and Recall across:
- 10 pure line shifts (insertions/deletions above defect lines)
- 10 symbol refactorings (functions/methods moved across hunks)
- 10 pre-existing modified contexts (defects inside touched lines)
- 10 genuinely introduced new defects (newly added security/lint issues)
- 10 resolved / fixed defects (defects eliminated in PR)
"""

from __future__ import annotations

import pytest

from app.services.analysis.base import RawFinding
from app.services.github.diff_parser import DiffChunk, DiffLine, FileDiff, LineType
from app.services.verification.delta_classifier import FindingDeltaClassifier


def _make_diff(file_path: str, modified_lines: list[int]) -> list[FileDiff]:
    """Helper to generate a FileDiff with modified line coordinates."""
    diff_lines = [
        DiffLine(
            line_type=LineType.ADDITION, content="+ code", old_line_number=None, new_line_number=lno
        )
        for lno in modified_lines
    ]
    chunk = DiffChunk(
        old_start=1,
        old_lines=10,
        new_start=1,
        new_lines=len(modified_lines),
        header="@@ -1,10 +1,10 @@",
        lines=diff_lines,
    )
    return [
        FileDiff(
            old_path=file_path,
            new_path=file_path,
            change_type="MODIFIED",
            chunks=[chunk],
            additions=len(modified_lines),
            deletions=0,
        )
    ]


@pytest.mark.parametrize("case_id", list(range(1, 51)))
def test_delta_classification_benchmark_case(case_id: int):
    """Test individual benchmark cases out of the 50-PR benchmark suite."""
    classifier = FindingDeltaClassifier()

    # Partition 1: Cases 1-10 -> Pure Line Shifts (Baseline defect shifted down by 20 lines)
    if 1 <= case_id <= 10:
        base_f = RawFinding(
            rule_id=f"E501_shift_{case_id}",
            message=f"Line too long in module_{case_id}",
            severity="LOW",
            category="STYLE",
            file_path=f"src/mod_{case_id}.py",
            start_line=50,
            enclosing_symbol=f"calc_metrics_{case_id}",
            code_snippet=f"total = sum([x for x in range({case_id})])",
        )
        # Shifted to line 75 in head, but snippet & symbol identical; lines 1..25 were added
        head_f = RawFinding(
            rule_id=f"E501_shift_{case_id}",
            message=f"Line too long in module_{case_id}",
            severity="LOW",
            category="STYLE",
            file_path=f"src/mod_{case_id}.py",
            start_line=75,
            enclosing_symbol=f"calc_metrics_{case_id}",
            code_snippet=f"total = sum([x for x in range({case_id})])",
        )
        diff = _make_diff(f"src/mod_{case_id}.py", modified_lines=list(range(1, 26)))
        res = classifier.classify([base_f], [head_f], diff)

        assert len(res.classified_findings) == 1
        assert res.classified_findings[0].delta_status == "EXISTING_BASELINE"
        assert res.existing_baseline_count == 1
        assert res.introduced_count == 0

    # Partition 2: Cases 11-20 -> Symbol Refactors (Moved function/symbol without modifying defect)
    elif 11 <= case_id <= 20:
        base_f = RawFinding(
            rule_id=f"B301_pickle_{case_id}",
            message="Use of pickle.loads is unsafe",
            severity="HIGH",
            category="SECURITY",
            file_path="src/handlers.py",
            start_line=120,
            enclosing_symbol=f"Handler_{case_id}.process",
            code_snippet="return pickle.loads(data)",
        )
        head_f = RawFinding(
            rule_id=f"B301_pickle_{case_id}",
            message="Use of pickle.loads is unsafe",
            severity="HIGH",
            category="SECURITY",
            file_path="src/handlers.py",
            start_line=210,
            enclosing_symbol=f"Handler_{case_id}.process",
            code_snippet="return pickle.loads(data)",
        )
        # Modified lines are at lines 300..320, unrelated to handler
        diff = _make_diff("src/handlers.py", modified_lines=[300, 301, 302])
        res = classifier.classify([base_f], [head_f], diff)

        assert len(res.classified_findings) == 1
        assert res.classified_findings[0].delta_status == "EXISTING_BASELINE"
        assert res.existing_baseline_count == 1
        assert res.introduced_count == 0

    # Partition 3: Cases 21-30 -> Pre-Existing Modified Context
    elif 21 <= case_id <= 30:
        base_f = RawFinding(
            rule_id=f"B101_assert_{case_id}",
            message="Use of assert in production code",
            severity="LOW",
            category="SECURITY",
            file_path="src/auth.py",
            start_line=45,
            enclosing_symbol="verify_token",
            code_snippet=f"assert token is not None, 'invalid token {case_id}'",
        )
        # Line 45 was modified directly in PR
        head_f = RawFinding(
            rule_id=f"B101_assert_{case_id}",
            message="Use of assert in production code",
            severity="LOW",
            category="SECURITY",
            file_path="src/auth.py",
            start_line=45,
            enclosing_symbol="verify_token",
            code_snippet=f"assert token is not None, 'invalid token {case_id}'",
        )
        diff = _make_diff("src/auth.py", modified_lines=[44, 45, 46])
        res = classifier.classify([base_f], [head_f], diff)

        assert len(res.classified_findings) == 1
        assert res.classified_findings[0].delta_status == "PRE_EXISTING_MODIFIED"
        assert res.pre_existing_modified_count == 1
        assert res.introduced_count == 0

    # Partition 4: Cases 31-40 -> Genuinely INTRODUCED NEW Defects
    elif 31 <= case_id <= 40:
        base_findings: list[RawFinding] = []
        head_f = RawFinding(
            rule_id=f"B608_sqli_{case_id}",
            message=f"Possible SQL injection vector in query_{case_id}",
            severity="CRITICAL",
            category="SECURITY",
            file_path=f"src/dao_{case_id}.py",
            start_line=15,
            enclosing_symbol=f"query_user_{case_id}",
            code_snippet=f"db.execute(f'SELECT * FROM users WHERE id = {case_id}')",
            is_blocking=True,
        )
        diff = _make_diff(f"src/dao_{case_id}.py", modified_lines=[14, 15, 16])
        res = classifier.classify(base_findings, [head_f], diff)

        assert len(res.classified_findings) == 1
        assert res.classified_findings[0].delta_status == "INTRODUCED_NEW"
        assert res.introduced_count == 1
        assert res.existing_baseline_count == 0

    # Partition 5: Cases 41-50 -> FIXED IN PR
    else:
        base_f = RawFinding(
            rule_id=f"E711_comparison_{case_id}",
            message="Comparison to None should be 'if cond is None:'",
            severity="LOW",
            category="STYLE",
            file_path="src/utils.py",
            start_line=30,
            enclosing_symbol="cleanse",
            code_snippet="if val == None:",
        )
        # Head completely resolved it; 0 head findings
        head_findings: list[RawFinding] = []
        diff = _make_diff("src/utils.py", modified_lines=[30])
        res = classifier.classify([base_f], head_findings, diff)

        # Baseline finding was classified as FIXED_IN_PR
        assert len(res.classified_findings) == 1
        assert res.classified_findings[0].delta_status == "FIXED_IN_PR"
        assert res.fixed_count == 1
        assert res.introduced_count == 0


def test_delta_benchmark_suite_precision_recall():
    """Aggregate all 50 benchmark cases and calculate empirical Precision and Recall.

    Guarantees:
    - Precision >= 95.0%
    - Recall >= 95.0%
    """
    classifier = FindingDeltaClassifier()

    true_positives = 0  # Expected INTRODUCED_NEW and classified as INTRODUCED_NEW
    false_positives = 0  # Expected NOT INTRODUCED_NEW but classified as INTRODUCED_NEW
    false_negatives = 0  # Expected INTRODUCED_NEW but classified as something else
    true_negatives = 0  # Expected NOT INTRODUCED_NEW and classified as NOT INTRODUCED_NEW

    for case_id in range(1, 51):
        if 1 <= case_id <= 10:
            # Shift -> Expect baseline
            base_f = RawFinding(
                rule_id=f"E501_{case_id}",
                message="Line too long",
                severity="LOW",
                category="STYLE",
                file_path=f"mod_{case_id}.py",
                start_line=50,
                enclosing_symbol="foo",
                code_snippet="code",
            )
            head_f = RawFinding(
                rule_id=f"E501_{case_id}",
                message="Line too long",
                severity="LOW",
                category="STYLE",
                file_path=f"mod_{case_id}.py",
                start_line=80,
                enclosing_symbol="foo",
                code_snippet="code",
            )
            diff = _make_diff(f"mod_{case_id}.py", modified_lines=[1, 2, 3])
            res = classifier.classify([base_f], [head_f], diff)
            is_intro = res.classified_findings[0].delta_status == "INTRODUCED_NEW"
            if is_intro:
                false_positives += 1
            else:
                true_negatives += 1

        elif 11 <= case_id <= 20:
            # Refactor -> Expect baseline
            base_f = RawFinding(
                rule_id=f"B301_{case_id}",
                message="Pickle load",
                severity="HIGH",
                category="SECURITY",
                file_path="mod.py",
                start_line=10,
                enclosing_symbol=f"sym_{case_id}",
                code_snippet="pickle.loads",
            )
            head_f = RawFinding(
                rule_id=f"B301_{case_id}",
                message="Pickle load",
                severity="HIGH",
                category="SECURITY",
                file_path="mod.py",
                start_line=90,
                enclosing_symbol=f"sym_{case_id}",
                code_snippet="pickle.loads",
            )
            diff = _make_diff("mod.py", modified_lines=[200])
            res = classifier.classify([base_f], [head_f], diff)
            is_intro = res.classified_findings[0].delta_status == "INTRODUCED_NEW"
            if is_intro:
                false_positives += 1
            else:
                true_negatives += 1

        elif 21 <= case_id <= 30:
            # Modified context -> Expect PRE_EXISTING_MODIFIED
            base_f = RawFinding(
                rule_id=f"B101_{case_id}",
                message="assert",
                severity="LOW",
                category="SECURITY",
                file_path="mod.py",
                start_line=30,
                enclosing_symbol="auth",
                code_snippet="assert True",
            )
            head_f = RawFinding(
                rule_id=f"B101_{case_id}",
                message="assert",
                severity="LOW",
                category="SECURITY",
                file_path="mod.py",
                start_line=30,
                enclosing_symbol="auth",
                code_snippet="assert True",
            )
            diff = _make_diff("mod.py", modified_lines=[30])
            res = classifier.classify([base_f], [head_f], diff)
            is_intro = res.classified_findings[0].delta_status == "INTRODUCED_NEW"
            if is_intro:
                false_positives += 1
            else:
                true_negatives += 1

        elif 31 <= case_id <= 40:
            # Genuinely new defect -> Expect INTRODUCED_NEW
            head_f = RawFinding(
                rule_id=f"B608_{case_id}",
                message="sqli",
                severity="CRITICAL",
                category="SECURITY",
                file_path="mod.py",
                start_line=10,
                enclosing_symbol="sql",
                code_snippet="select",
            )
            diff = _make_diff("mod.py", modified_lines=[10])
            res = classifier.classify([], [head_f], diff)
            is_intro = res.classified_findings[0].delta_status == "INTRODUCED_NEW"
            if is_intro:
                true_positives += 1
            else:
                false_negatives += 1

        else:
            # Fixed defect -> Expect FIXED_IN_PR
            base_f = RawFinding(
                rule_id=f"E711_{case_id}",
                message="== None",
                severity="LOW",
                category="STYLE",
                file_path="mod.py",
                start_line=15,
                enclosing_symbol="cleanse",
                code_snippet="x == None",
            )
            diff = _make_diff("mod.py", modified_lines=[15])
            res = classifier.classify([base_f], [], diff)
            is_intro = res.classified_findings[0].delta_status == "INTRODUCED_NEW"
            if is_intro:
                false_positives += 1
            else:
                true_negatives += 1

    precision = (
        (true_positives / (true_positives + false_positives)) * 100.0
        if (true_positives + false_positives) > 0
        else 100.0
    )
    recall = (
        (true_positives / (true_positives + false_negatives)) * 100.0
        if (true_positives + false_negatives) > 0
        else 100.0
    )

    print(
        f"\n[BENCHMARK] Evaluated 50 PR Cases: TP={true_positives}, FP={false_positives}, FN={false_negatives}, TN={true_negatives}"
    )
    print(f"[BENCHMARK] Measured Precision: {precision:.2f}% (Threshold: >= 95.0%)")
    print(f"[BENCHMARK] Measured Recall: {recall:.2f}% (Threshold: >= 95.0%)")

    assert precision >= 95.0, f"Precision {precision}% is below 95%"
    assert recall >= 95.0, f"Recall {recall}% is below 95%"
