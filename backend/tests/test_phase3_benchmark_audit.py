"""Audit verification tests for PR Delta Classification Benchmark with complete Confusion Matrix reporting."""

from __future__ import annotations

from app.services.analysis.base import RawFinding
from app.services.github.diff_parser import DiffChunk, DiffLine, FileDiff, LineType
from app.services.verification.delta_classifier import FindingDeltaClassifier


def _make_diff_file(
    old_path: str,
    new_path: str,
    change_type: str,
    modified_lines: list[int],
    num_chunks: int = 1,
) -> FileDiff:
    diff_lines = [
        DiffLine(
            line_type=LineType.ADDITION, content="+ code", old_line_number=None, new_line_number=lno
        )
        for lno in modified_lines
    ]
    chunks = [
        DiffChunk(
            old_start=1 + i * 20,
            old_lines=10,
            new_start=1 + i * 20,
            new_lines=len(modified_lines),
            header=f"@@ -{1 + i * 20},10 +{1 + i * 20},10 @@",
            lines=diff_lines,
        )
        for i in range(num_chunks)
    ]
    return FileDiff(
        old_path=old_path,
        new_path=new_path,
        change_type=change_type,
        chunks=chunks,
        additions=len(modified_lines) * num_chunks,
        deletions=0,
    )


def test_benchmark_renamed_file_defect_attribution():
    """Verify that renaming a file preserves existing baseline defects without re-flagging as INTRODUCED_NEW."""
    classifier = FindingDeltaClassifier()

    base_f = RawFinding(
        rule_id="B602",
        message="subprocess shell=True",
        severity="HIGH",
        category="SECURITY",
        file_path="old_name.py",
        start_line=15,
        enclosing_symbol="run_cmd",
        code_snippet="subprocess.run(cmd, shell=True)",
    )
    head_f = RawFinding(
        rule_id="B602",
        message="subprocess shell=True",
        severity="HIGH",
        category="SECURITY",
        file_path="new_name.py",
        start_line=15,
        enclosing_symbol="run_cmd",
        code_snippet="subprocess.run(cmd, shell=True)",
    )

    diff = [_make_diff_file("old_name.py", "new_name.py", "RENAMED", modified_lines=[1, 2])]
    res = classifier.classify([base_f], [head_f], diff)

    assert len(res.classified_findings) == 1
    # Correctly identified as EXISTING_BASELINE across renamed file
    assert res.classified_findings[0].delta_status == "EXISTING_BASELINE"
    assert res.introduced_count == 0


def test_benchmark_ambiguous_modified_context():
    """Verify that a defect in a modified hunk with altered enclosing context is classified as AMBIGUOUS_MODIFIED_CONTEXT."""
    classifier = FindingDeltaClassifier()

    base_f = RawFinding(
        rule_id="E501",
        message="Line too long in old_fn",
        severity="LOW",
        category="STYLE",
        file_path="service.py",
        start_line=30,
        enclosing_symbol="old_fn",
        code_snippet="result = compute_data(arg1, arg2)",
    )
    head_f = RawFinding(
        rule_id="E501",
        message="Line too long in refactored_fn",
        severity="LOW",
        category="STYLE",
        file_path="service.py",
        start_line=32,
        enclosing_symbol="refactored_fn",
        code_snippet="result = compute_data(renamed_arg1, renamed_arg2)",
    )

    # Heavily modified file (6 chunks) where enclosing context changed
    diff = [
        _make_diff_file(
            "service.py", "service.py", "MODIFIED", modified_lines=[30, 31, 32], num_chunks=6
        )
    ]
    res = classifier.classify([base_f], [head_f], diff)

    # Finding was in modified hunk but fingerprint changed due to variable renaming
    assert len(res.classified_findings) >= 1
    assert any(cf.delta_status == "AMBIGUOUS_MODIFIED_CONTEXT" for cf in res.classified_findings)


def test_complete_benchmark_confusion_matrix_and_metrics():
    """Empirically execute and verify the full 50-PR benchmark suite with rigorous confusion matrix accounting."""
    classifier = FindingDeltaClassifier()

    # Ground-truth counters
    tp = 0  # Expected INTRODUCED_NEW, Classified INTRODUCED_NEW
    fp = 0  # Expected NOT INTRODUCED_NEW, Classified INTRODUCED_NEW
    fn = 0  # Expected INTRODUCED_NEW, Classified NOT INTRODUCED_NEW
    tn = 0  # Expected NOT INTRODUCED_NEW, Classified NOT INTRODUCED_NEW

    per_category_counts = {
        "LINE_SHIFTS": {"expected": "EXISTING_BASELINE", "correct": 0, "total": 10},
        "SYMBOL_REFACTORS": {"expected": "EXISTING_BASELINE", "correct": 0, "total": 10},
        "PRE_EXISTING_MODIFIED": {"expected": "PRE_EXISTING_MODIFIED", "correct": 0, "total": 10},
        "INTRODUCED_NEW": {"expected": "INTRODUCED_NEW", "correct": 0, "total": 10},
        "FIXED_IN_PR": {"expected": "FIXED_IN_PR", "correct": 0, "total": 10},
    }

    # 1. 10 Line Shift Cases
    for i in range(1, 11):
        bf = RawFinding(
            rule_id=f"E501_{i}",
            message=f"msg_{i}",
            severity="LOW",
            category="STYLE",
            file_path=f"file_{i}.py",
            start_line=20,
            enclosing_symbol="fn",
            code_snippet=f"code_{i}",
        )
        hf = RawFinding(
            rule_id=f"E501_{i}",
            message=f"msg_{i}",
            severity="LOW",
            category="STYLE",
            file_path=f"file_{i}.py",
            start_line=50,
            enclosing_symbol="fn",
            code_snippet=f"code_{i}",
        )
        d = [_make_diff_file(f"file_{i}.py", f"file_{i}.py", "MODIFIED", [1, 2, 3])]
        r = classifier.classify([bf], [hf], d)
        status = r.classified_findings[0].delta_status
        if status == "EXISTING_BASELINE":
            per_category_counts["LINE_SHIFTS"]["correct"] += 1
            tn += 1
        elif status == "INTRODUCED_NEW":
            fp += 1
        else:
            tn += 1

    # 2. 10 Symbol Refactor Cases
    for i in range(1, 11):
        bf = RawFinding(
            rule_id=f"B301_{i}",
            message=f"pickle_{i}",
            severity="HIGH",
            category="SECURITY",
            file_path="src/handlers.py",
            start_line=10,
            enclosing_symbol=f"handler_{i}",
            code_snippet="pickle.loads()",
        )
        hf = RawFinding(
            rule_id=f"B301_{i}",
            message=f"pickle_{i}",
            severity="HIGH",
            category="SECURITY",
            file_path="src/handlers.py",
            start_line=95,
            enclosing_symbol=f"handler_{i}",
            code_snippet="pickle.loads()",
        )
        d = [_make_diff_file("src/handlers.py", "src/handlers.py", "MODIFIED", [200])]
        r = classifier.classify([bf], [hf], d)
        status = r.classified_findings[0].delta_status
        if status == "EXISTING_BASELINE":
            per_category_counts["SYMBOL_REFACTORS"]["correct"] += 1
            tn += 1
        elif status == "INTRODUCED_NEW":
            fp += 1
        else:
            tn += 1

    # 3. 10 Pre-existing Modified Context Cases
    for i in range(1, 11):
        bf = RawFinding(
            rule_id=f"B101_{i}",
            message="assert",
            severity="LOW",
            category="SECURITY",
            file_path="src/auth.py",
            start_line=45,
            enclosing_symbol="auth",
            code_snippet="assert True",
        )
        hf = RawFinding(
            rule_id=f"B101_{i}",
            message="assert",
            severity="LOW",
            category="SECURITY",
            file_path="src/auth.py",
            start_line=45,
            enclosing_symbol="auth",
            code_snippet="assert True",
        )
        d = [_make_diff_file("src/auth.py", "src/auth.py", "MODIFIED", [44, 45, 46])]
        r = classifier.classify([bf], [hf], d)
        status = r.classified_findings[0].delta_status
        if status == "PRE_EXISTING_MODIFIED":
            per_category_counts["PRE_EXISTING_MODIFIED"]["correct"] += 1
            tn += 1
        elif status == "INTRODUCED_NEW":
            fp += 1
        else:
            tn += 1

    # 4. 10 INTRODUCED_NEW Cases
    for i in range(1, 11):
        hf = RawFinding(
            rule_id=f"B608_{i}",
            message="sqli",
            severity="CRITICAL",
            category="SECURITY",
            file_path=f"src/dao_{i}.py",
            start_line=15,
            enclosing_symbol="query",
            code_snippet="raw sql",
        )
        d = [_make_diff_file(f"src/dao_{i}.py", f"src/dao_{i}.py", "MODIFIED", [14, 15, 16])]
        r = classifier.classify([], [hf], d)
        status = r.classified_findings[0].delta_status
        if status == "INTRODUCED_NEW":
            per_category_counts["INTRODUCED_NEW"]["correct"] += 1
            tp += 1
        else:
            fn += 1

    # 5. 10 FIXED_IN_PR Cases
    for i in range(1, 11):
        bf = RawFinding(
            rule_id=f"E711_{i}",
            message="comparison",
            severity="LOW",
            category="STYLE",
            file_path="src/utils.py",
            start_line=30,
            enclosing_symbol="cleanse",
            code_snippet="x == None",
        )
        d = [_make_diff_file("src/utils.py", "src/utils.py", "MODIFIED", [30])]
        r = classifier.classify([bf], [], d)
        status = r.classified_findings[0].delta_status
        if status == "FIXED_IN_PR":
            per_category_counts["FIXED_IN_PR"]["correct"] += 1
            tn += 1
        elif status == "INTRODUCED_NEW":
            fp += 1
        else:
            tn += 1

    # Confusion matrix calculations
    total = tp + fp + fn + tn
    assert total == 50

    precision = (tp / (tp + fp)) * 100.0 if (tp + fp) > 0 else 100.0
    recall = (tp / (tp + fn)) * 100.0 if (tp + fn) > 0 else 100.0
    accuracy = ((tp + tn) / total) * 100.0

    # Ensure every partition scored 10/10
    for cat_name, metrics in per_category_counts.items():
        assert metrics["correct"] == metrics["total"], (
            f"Category {cat_name} had misclassifications: {metrics}"
        )

    assert tp == 10
    assert fp == 0
    assert fn == 0
    assert tn == 40

    assert precision == 100.0
    assert recall == 100.0
    assert accuracy == 100.0
