import os
import re
import pandas as pd
from tqdm import tqdm

from src.grading.python_runner import test_python
from src.grading.java_runner import test_java
from src.tutoring.patch_utils import apply_patch_with_fallback

def normalize_output(x):
    if pd.isna(x):
        return ""
    text = str(x).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.strip().split("\n")]
    return "\n".join(lines).strip()

def run_tests_for_case(case_row, tests_df, student_code):
    question_id = case_row["question_id"]
    language = case_row["language"]
    tester_code = case_row.get("tester", "")

    qtests = tests_df[tests_df["question_id"] == question_id].sort_values("test_number")

    n_passed = 0
    n_failed = 0
    first_failed_test_number = None
    first_fail_expected = ""
    first_fail_actual = ""
    first_fail_stderr = ""
    first_fail_stage = ""

    for _, test_row in qtests.iterrows():
        test_code = test_row["testcode"]
        expected = normalize_output(test_row["expected"])

        if language == "python":
            run_result = test_python(student_code, test_code, tester_code=tester_code)
        elif language == "java":
            run_result = test_java(student_code, test_code, tester_code=tester_code)
        else:
            run_result = {
                "success": False,
                "stdout": "",
                "stderr": f"Unsupported language: {language}",
                "stage": "unsupported",
                "timed_out": False,
            }

        actual = normalize_output(run_result.get("stdout", ""))
        success = bool(run_result.get("success", False))
        stderr = str(run_result.get("stderr", "") or "")
        stage = str(run_result.get("stage", "") or "")

        passed = success and (actual == expected)

        if passed:
            n_passed += 1
        else:
            n_failed += 1
            if first_failed_test_number is None:
                first_failed_test_number = test_row["test_number"]
                first_fail_expected = expected
                first_fail_actual = actual
                first_fail_stderr = stderr
                first_fail_stage = stage

    return {
        "n_passed": n_passed,
        "n_failed": n_failed,
        "passed_all": n_failed == 0,
        "first_failed_test_number": first_failed_test_number,
        "first_fail_expected": first_fail_expected,
        "first_fail_actual": first_fail_actual,
        "first_fail_stderr": first_fail_stderr,
        "first_fail_stage": first_fail_stage,
    }


def main():
    years = ["19_20", "20_21", "21_22"]

    os.makedirs("outputs/patch_results/best_patch", exist_ok=True)
    os.makedirs("outputs/patch_results/comparison", exist_ok=True)

    for year in years:

        feedbacks = pd.read_parquet(f"outputs/feedbacks/{year}_response.parquet")
        fails = pd.read_parquet(f"outputs/failed_cases/{year}_failed_cases.parquet")
        tests = pd.read_parquet(f"outputs/{year}/hamburg_tests.parquet")

        merged = feedbacks.merge(
            fails[
                [
                    "case_id",
                    "question_id",
                    "student_id",
                    "language",
                    "student_code",
                    "tester",
                    "failed_tests",
                    "passed_test",
                    "total_test",
                    "first_failed_test_number",
                    "first_fail_expected",
                    "first_fail_actual",
                    "first_fail_stderr",
                ]
            ],
            on=["case_id", "question_id", "student_id", "language"],
            how="inner",
        )

        results = []

        for _, row in tqdm(merged.iterrows(), total=len(merged), desc=f"Applying patches {year}"):
            original_code = row["student_code"]
            replace_block = row.get("replace_block", "")
            with_block = row.get("with_block", "")

            n_passed_before = int(row["passed_test"])
            n_failed_before = int(row["failed_tests"])

            parsed_ok = (
                str(row.get("json_parse_status", "")) in {"direct_json", "trimmed_json"}
            )

            if not parsed_ok:
                patched_code = original_code
                patch_applied = False
                patch_status = "json_parse_failed"
                after = {
                    "n_passed": n_passed_before,
                    "n_failed": n_failed_before,
                    "passed_all": False,
                    "first_failed_test_number": row.get("first_failed_test_number"),
                    "first_fail_expected": row.get("first_fail_expected", ""),
                    "first_fail_actual": row.get("first_fail_actual", ""),
                    "first_fail_stderr": row.get("first_fail_stderr", ""),
                    "first_fail_stage": "",
                }
            else:
                patched_code, patch_applied, patch_status = apply_patch_with_fallback(
                    original_code,
                    replace_block,
                    with_block,
                    row.get("target_function", "UNKNOWN"),
                    row["language"],
                    )
                if patch_applied:
                    after = run_tests_for_case(row, tests, patched_code)

                    if after["n_failed"] > n_failed_before:
                        patched_code = original_code
                        patch_applied = False
                        patch_status = "made_things_worse_reverted"
                        after = {
                            "n_passed": n_passed_before,
                            "n_failed": n_failed_before,
                            "passed_all": False,
                            "first_failed_test_number": row.get("first_failed_test_number"),
                            "first_fail_expected": row.get("first_fail_expected", ""),
                            "first_fail_actual": row.get("first_fail_actual", ""),
                            "first_fail_stderr": row.get("first_fail_stderr", ""),
                            "first_fail_stage": "",
                        }
                else:
                    after = {
                        "n_passed": n_passed_before,
                        "n_failed": n_failed_before,
                        "passed_all": False,
                        "first_failed_test_number": row.get("first_failed_test_number"),
                        "first_fail_expected": row.get("first_fail_expected", ""),
                        "first_fail_actual": row.get("first_fail_actual", ""),
                        "first_fail_stderr": row.get("first_fail_stderr", ""),
                        "first_fail_stage": "",
                    }

            results.append(
                {
                    "case_id": row["case_id"],
                    "question_id": row["question_id"],
                    "student_id": row["student_id"],
                    "language": row["language"],
                    "candidate_id": row["candidate_id"],
                    "temperature": row["temperature"],
                    "prompt_bug_type": row["prompt_bug_type"],
                    "json_parse_status": row["json_parse_status"],
                    "target_function": row["target_function"],
                    "replace_block": row["replace_block"],
                    "with_block": row["with_block"],

                    "n_passed_before": n_passed_before,
                    "n_failed_before": n_failed_before,
                    "n_passed_after": after["n_passed"],
                    "n_failed_after": after["n_failed"],
                    "delta_passed": after["n_passed"] - n_passed_before,
                    "delta_failed": after["n_failed"] - n_failed_before,
                    "passed_all_after": after["passed_all"],

                    "patch_applied": patch_applied,
                    "patch_status": patch_status,
                    "patched_code": patched_code,

                    "first_failed_test_after": after["first_failed_test_number"],
                    "first_fail_expected_after": after["first_fail_expected"],
                    "first_fail_actual_after": after["first_fail_actual"],
                    "first_fail_stderr_after": after["first_fail_stderr"],
                    "first_fail_stage_after": after["first_fail_stage"],
                }
            )

        output_df = pd.DataFrame(results)
        output_df.to_csv(f"outputs/patch_results/{year}_patch.csv", index=False)

        best_df = (
            output_df.sort_values(
                by=["case_id", "passed_all_after", "delta_failed", "delta_passed"],
                ascending=[True, False, True, False]
            )
            .groupby("case_id")
            .head(1)
            .copy()
        )

        comparison_df = best_df.merge(fails[["case_id", "student_code"]], on="case_id", how="left")

        comparison_df = comparison_df[
            [
                "case_id",
                "question_id",
                "student_id",
                "language",
                "candidate_id",
                "patch_status",
                "patch_applied",
                "student_code",
                "patched_code",
                "replace_block",
                "with_block",
            ]
        ]

        comparison_df.to_csv(f"outputs/patch_results/comparison/{year}_original_vs_patched.csv", index=False)
        best_df.to_csv(f"outputs/patch_results/best_patch/{year}_best_patch_per_case.csv", index=False)

        print("\nPatch status:")
        print(output_df["patch_status"].value_counts(dropna=False))

        print("\nBest-per-case summary:")
        print(f"Total failed cases: {best_df['case_id'].nunique()}")
        print(f"Passed all after patch: {(best_df['passed_all_after'] == True).sum()}")
        print(f"Improved cases: {(best_df['delta_failed'] < 0).sum()}")
        print(f"No change: {(best_df['delta_failed'] == 0).sum()}")


if __name__ == "__main__":
    main()