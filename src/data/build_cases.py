import os
import pandas as pd

years = ["19_20", "20_21", "21_22"]

for year in years:
    solutions = pd.read_parquet(f"outputs/{year}/hamburg_solutions.parquet")
    tasks = pd.read_parquet(f"outputs/{year}/hamburg_tasks.parquet")

    task_ids = tasks["id"].dropna().unique()
    subset = solutions[solutions["question_id"].isin(task_ids)].copy()

    cases = subset.merge(tasks, left_on= "question_id", right_on = "id", how = "left")
    cases = cases.reset_index(drop = True)
    cases["case_id"] = cases.index

    cases = cases.rename(
        columns={
            "solution": "student_code",
            "language_x": "language",
            "title_eng": "title",
            "task_description_plain_eng": "description",
            "task_description_plain_ger": "description_ger",
            "answer": "reference_answer",
        }
    )

    keep_columns = [
        "case_id",
        "question_id",
        "language",
        "student_id",
        "student_code",
        "title",
        "description",
        "description_ger",
        "skeleton",
        "tester",
        "reference_answer",
    ]

    cases = cases[keep_columns]

    print(f"Year {year} :")
    print("Unique tasks:", cases["question_id"].nunique())
    print("Language Distribution:")
    print(cases["language"].value_counts(dropna=False))
    print("Total cases:", len(cases))

    os.makedirs("outputs/cases", exist_ok=True)
    cases.to_parquet(f"outputs/cases/{year}_cases.parquet", index=False)