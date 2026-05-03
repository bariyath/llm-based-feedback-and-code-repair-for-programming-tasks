import os
import pandas as pd

years = ["19_20", "20_21", "21_22"]

os.makedirs("outputs/failed_cases", exist_ok=True)

for year in years:
    cases = pd.read_parquet(f"outputs/cases/{year}_cases.parquet")
    cases_res = pd.read_parquet(f"outputs/grading/{year}_case_results.parquet")

    failed_cases = cases_res[cases_res["passed_all"] == False].copy()

    merged = failed_cases.merge(
        cases,
        on=["case_id", "question_id", "student_id", "language"],
        how="left"
    )

    merged.to_parquet(f"outputs/failed_cases/{year}_failed_cases.parquet", index=False)

    print("Failed Cases:", len(merged))
    print(merged[["case_id", "question_id", "student_id", "language", "failed_tests"]].head())