import os
import pandas as pd
from tqdm import tqdm

from src.grading.python_runner import test_python
from src.grading.java_runner import test_java

def normalize_output(x):
    if pd.isna(x):
        return ""
    text = str(x).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.strip().split("\n")]
    return "\n".join(lines).strip()


def run_single_test(case_row, test_row, student_code):
    language = case_row["language"]
    tester_code = case_row.get("tester", "")

    if language == "python":
        run_result = test_python(student_code, test_row["testcode"], tester_code=tester_code)
    elif language == "java":
        run_result = test_java(student_code, test_row["testcode"], tester_code=tester_code)
    else:
        run_result = {
            "success": False,
            "stdout": "",
            "stderr": f"Unsupported language: {language}",
            "returncode": -1,
            "timed_out": False,
            "stage": "unsupported",
        }

    expected = normalize_output(test_row["expected"])
    actual = normalize_output(run_result.get("stdout", ""))
    passed = bool(run_result.get("success", False)) and (actual == expected)

    return {
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "stderr": str(run_result.get("stderr", "") or ""),
        "timed_out": bool(run_result.get("timed_out", False)),
        "stage": run_result.get("stage", "unknown"),
    }


def single_case_evaluation(case_row, tests_df):
    question_id = case_row["question_id"]
    qtests = tests_df[tests_df["question_id"] == question_id].sort_values("test_number")

    results = []
    for _, test_row in qtests.iterrows():
        res = run_single_test(case_row, test_row, case_row["student_code"])
        results.append(
            {
                "case_id": case_row["case_id"],
                "question_id": question_id,
                "student_id": case_row["student_id"],
                "language": case_row["language"],
                "test_number": test_row["test_number"],
                "is_example": test_row.get("is_example", False),
                **res,
            }
        )
    return results


def main():
    years = ["19_20", "20_21", "21_22"]

    os.makedirs("outputs/grading", exist_ok=True)

    for year in years:
        cases = pd.read_parquet(f"outputs/cases/{year}_cases.parquet")
        tests = pd.read_parquet(f"outputs/{year}/hamburg_tests.parquet")

        all_results = []

        for _, case_row in tqdm(cases.iterrows(), total=len(cases), desc="Evaluating cases"):
            all_results.extend(single_case_evaluation(case_row, tests))

        results_df = pd.DataFrame(all_results)
        results_df.to_parquet(f"outputs/grading/{year}_test_results.parquet", index=False)

        summary = (
            results_df.groupby(["case_id", "question_id", "student_id", "language"])
            .agg(
                total_test=("passed", "count"),
                passed_test=("passed", "sum"),
            )
            .reset_index()
        )

        summary["failed_tests"] = summary["total_test"] - summary["passed_test"]
        summary["passed_all"] = summary["failed_tests"] == 0

        first_failed = (
            results_df[~results_df["passed"]]
            .sort_values(["case_id", "test_number"])
            .groupby("case_id")
            .first()
            .reset_index()[["case_id", "test_number", "expected", "actual", "stderr", "stage", "timed_out"]]
            .rename(
                columns={
                    "test_number": "first_failed_test_number",
                    "expected": "first_fail_expected",
                    "actual": "first_fail_actual",
                    "stderr": "first_fail_stderr",
                    "stage": "first_fail_stage",
                    "timed_out": "first_fail_timed_out",
                }
            )
        )

        summary = summary.merge(first_failed, on="case_id", how="left")
        summary.to_parquet(f"outputs/grading/{year}_case_results.parquet", index=False)
        print(summary["passed_all"].value_counts(dropna=False))


if __name__ == "__main__":
    main()