import os
import pandas as pd
from tqdm import tqdm

from llm_prompts import build_prompt
from llm_client import llm_feedback, safe_json_loads

N_CANDIDATES = 2
CANDIDATE_TEMPERATURES = {
    1: 0.0,
    2: 0.2,
}


def main():
    years = ["19_20", "20_21", "21_22"]

    os.makedirs("outputs/feedbacks", exist_ok=True)
    for year in years:
        failed_cases = pd.read_parquet(f"outputs/failed_cases/{year}_failed_cases.parquet")

        print("\nLanguage distribution:")
        print(failed_cases["language"].value_counts(dropna=False))

        outputs = []

        for _, row in tqdm(failed_cases.iterrows(), total=len(failed_cases), desc=f"Generating feedback {year}"):
            for candidate_id in range(1, N_CANDIDATES + 1):
                prompt, prompt_bug_type = build_prompt(row, candidate_id=candidate_id)
                temperature = CANDIDATE_TEMPERATURES[candidate_id]

                raw_feedback = llm_feedback(prompt, temperature=temperature)
                parsed_json, parse_status = safe_json_loads(raw_feedback)

                if parsed_json is None:
                    parsed_json = {
                        "diagnosis": "",
                        "hints": [],
                        "target_function": "UNKNOWN",
                        "replace": "",
                        "with": "",
                    }

                outputs.append(
                    {
                        "case_id": row["case_id"],
                        "question_id": row["question_id"],
                        "student_id": row["student_id"],
                        "language": row["language"],
                        "candidate_id": candidate_id,
                        "temperature": temperature,
                        "prompt_bug_type": prompt_bug_type,
                        "prompt": prompt,
                        "raw_feedback": raw_feedback,
                        "json_parse_status": parse_status,
                        "diagnosis": parsed_json.get("diagnosis", ""),
                        "hints": parsed_json.get("hints", []),
                        "target_function": parsed_json.get("target_function", parsed_json.get("target-function", "UNKNOWN")),
                        "replace_block": parsed_json.get("replace", ""),
                        "with_block": parsed_json.get("with", ""),
                    }
                )

        output_df = pd.DataFrame(outputs)
        output_df.to_parquet(f"outputs/feedbacks/{year}_response.parquet", index=False)
        output_df.to_csv(f"outputs/feedbacks/{year}_response.csv", index=False)

if __name__ == "__main__":
    main()
