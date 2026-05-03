import pandas as pd


def sanitize(text) -> str:
    if pd.isna(text):
        return ""
    if not isinstance(text, str):
        text = str(text)
    return "".join(c for c in text if c == "\n" or c == "\t" or ord(c) >= 32)


def get_description(row) -> str:
    for key in [
        "description",
        "task_description_plain_eng",
        "task_description_plain_ger",
        "description_eng",
        "description_ger",
    ]:
        if key in row and not pd.isna(row[key]):
            return sanitize(row[key])
    return ""


def detect_bug_type(row) -> str:
    stderr = sanitize(row.get("first_fail_stderr", "")).lower()
    actual = sanitize(row.get("first_fail_actual", "")).lower()

    if "timed out" in stderr or "timeout" in stderr:
        return "timeout"
    if "recursionerror" in stderr or "maximum recursion depth" in stderr:
        return "recursion"
    if "syntaxerror" in stderr or "javac" in stderr or "compile" in stderr:
        return "compile_error"
    if "indexerror" in stderr or "list index out of range" in stderr:
        return "index_error"
    if "nullpointerexception" in stderr:
        return "null_pointer"
    if stderr.strip():
        return "runtime_error"
    if actual.strip():
        return "wrong_output"
    return "unknown"


def candidate_strategy(candidate_id: int) -> str:
    if candidate_id == 1:
        return "Choose the single most likely minimal fix."
    if candidate_id == 2:
        return "Choose a different localized fix, prioritizing null checks, state updates, index updates, or base-case errors when relevant."
    return "Choose one plausible localized fix."


def build_prompt(row, candidate_id: int = 1):
    language = sanitize(row.get("language", ""))
    title = sanitize(row.get("title", ""))
    description = get_description(row)
    student_code = sanitize(row.get("student_code", ""))
    skeleton = sanitize(row.get("skeleton", ""))
    reference_answer = sanitize(row.get("reference_answer", ""))

    test_number = sanitize(row.get("first_failed_test_number", ""))
    expected = sanitize(row.get("first_fail_expected", ""))
    actual = sanitize(row.get("first_fail_actual", ""))
    stderr = sanitize(row.get("first_fail_stderr", ""))

    passed_tests = sanitize(row.get("passed_test", ""))
    failed_tests = sanitize(row.get("failed_tests", ""))
    total_tests = sanitize(row.get("total_test", ""))

    bug_type = detect_bug_type(row)
    strategy = candidate_strategy(candidate_id)

    extra_guidance = ""

    if bug_type == "timeout":
        extra_guidance = """
    For timeout bugs:
    - Check for recursion or infinite loops without a proper base case.
    - Check if recursion reduces the problem size.
    - Ignore operations like pop(0) repeatedly on lists (O(n) each time).
    - Ensure that loops modify variables so they eventually terminate.
    """

    elif bug_type == "unknown":
        extra_guidance = """
    For unknown bugs:
    - Use the failed test, description and reference answer to get to a conclusion.
    - Instead of rewriting the whole program prioritize fixing one local bug.
    """

    elif bug_type == "wrong_output":
        extra_guidance = """
    For wrong-output bugs:
    - Check for edge cases such as empty input or first/last element.
    - Check for off-by-one errors.
    - Verify that comparison operators are correct (>, >=, <, <=).
    - Ensure return values and update steps.
    """
    
    # This is for the year 19_20.
    elif bug_type == "runtime_error":
        extra_guidance = """
    For runtime-error bugs:
    - Check the error message to identify the exact failing access or operation.
    - Check for missing base cases, null checks, invalid parent-child references, and bad index updates.
    - Prioritize fixing the root cause inside one method instead of adding code everywhere to fix it.
    - If the task is a list, tree or array structure then preserve structure invariants after the change.
    """

    prompt = f"""
You are a programming tutor.

A student's solution failed tests. Your task is to identify ONE local bug and propose ONE small fix.

Attempt: {candidate_id}
Approach: {strategy}

Programming language: {language}
Guessed bug type: {bug_type}

{extra_guidance}

Task title: {title}
Task description:
{description}

Student code currently passes {passed_tests}/{total_tests} tests and fails {failed_tests}/{total_tests} tests.

Student code:
```{language}
{student_code}

Task skeleton (if present):
{skeleton}

Reference answer (for understanding intent only; do not copy whole program unless the whole student solution is only one function/method):
{reference_answer}

First failed test:

- test number: {test_number}
- expected output: {expected}
- actual output: {actual}
- error message: {stderr}

Rules:

1. Focus on exactly ONE method or function if possible.
2. The "replace" content must be the complete original buggy function or method copied exactly from the student code.
3. The "with" content must be the corrected complete version of that same function/method.
4. Do not include main code, test code, markdown, prose inside JSON values.
5. Do not return just a code fragment like a loop, an if block, statement or expression.
6. If you are unable to identify one exact full function/method to replace, then set:
    - "target_function" : "UNKNOWN"
    - "replace" : ""
    - "with" : ""

Return valid JSON only with exactly these keys:
{{
"diagnosis": "1-3 short sentences",
"hints": ["hint 1", "hint 2", "hint 3"],
"target_function": "function name or UNKNOWN",
"replace": "exact original full function/method or empty string",
"with": "corrected full function/method or empty string"
}}
""".strip()

    return prompt, bug_type