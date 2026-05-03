import pandas as pd

patch = pd.read_csv("outputs/patch_results/19_20_patch.csv")
cases = pd.read_parquet("outputs/cases/19_20_cases.parquet")

merged = patch.merge(
    cases[["case_id", "student_code"]],
    on="case_id",
    how="left"
)

for _, row in merged.iterrows():
    print("\n" + "=" * 80)
    print(f"CASE ID: {row['case_id']}")
    print(f"QUESTION ID: {row['question_id']}")
    print(f"LANGUAGE: {row['language']}")
    print(f"CANDIDATE: {row['candidate_id']}")
    print(f"PATCH APPLIED: {row['patch_applied']}")
    print(f"PATCH STATUS: {row['patch_status']}")
    print(f"PASSED BEFORE: {row['n_passed_before']}")
    print(f"PASSED AFTER: {row['n_passed_after']}")
    print(f"FAILED BEFORE: {row['n_failed_before']}")
    print(f"FAILED AFTER: {row['n_failed_after']}")

    print("\nORIGINAL CODE:")
    print(row["student_code"])

    print("\nPATCHED CODE:")
    print(row["patched_code"])

with open("outputs/patch_results/19_20_original_vs_patched.txt", "w", encoding="utf-8") as f:
    for _, row in merged.iterrows():
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"CASE ID: {row['case_id']}\n")
        f.write(f"QUESTION ID: {row['question_id']}\n")
        f.write(f"LANGUAGE: {row['language']}\n")
        f.write(f"CANDIDATE: {row['candidate_id']}\n")
        f.write(f"PATCH APPLIED: {row['patch_applied']}\n")
        f.write(f"PATCH STATUS: {row['patch_status']}\n")
        f.write(f"PASSED BEFORE: {row['n_passed_before']}\n")
        f.write(f"PASSED AFTER: {row['n_passed_after']}\n")
        f.write(f"FAILED BEFORE: {row['n_failed_before']}\n")
        f.write(f"FAILED AFTER: {row['n_failed_after']}\n")

        f.write("\nORIGINAL CODE:\n")
        f.write(str(row["student_code"]))

        f.write("\n\nPATCHED CODE:\n")
        f.write(str(row["patched_code"]))
        f.write("\n")