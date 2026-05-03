import os
import pandas as pd

years = ["19_20", "20_21", "21_22"]

def detect_language(qid):
    qid = str(qid)
    if qid.endswith("python"):
        return "python"
    if qid.endswith("java"):
        return "java"
    return "unknown"

for year in years:
    solutions = pd.read_csv(f"Dataset/hamburg/{year}_solutions.csv")
    tasks = pd.read_csv(f"Dataset/hamburg/{year}_task_descriptions.csv")
    tests = pd.read_csv(f"Dataset/hamburg/{year}_tests.csv")

    solutions["language"] = solutions["question_id"].apply(detect_language)
    tasks["language"] = tasks["id"].apply(detect_language)
    tests["language"] = tests["question_id"].apply(detect_language)

    os.makedirs(f"outputs/{year}", exist_ok = True)

    solutions.to_parquet(f"outputs/{year}/hamburg_solutions.parquet", index = False)
    tasks.to_parquet(f"outputs/{year}/hamburg_tasks.parquet", index = False)
    tests.to_parquet(f"outputs/{year}/hamburg_tests.parquet", index = False)

    print(f"Year {year} :")
    print(tasks["language"].value_counts())
