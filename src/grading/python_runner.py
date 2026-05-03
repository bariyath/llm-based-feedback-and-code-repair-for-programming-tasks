import os
import subprocess
import pandas as pd
import re
import tempfile
from pathlib import Path


DEFAULT_TIMEOUT = int(os.getenv("PYTHON_RUN_TIMEOUT", "6"))

def clean_tester(tester_code) -> str:
    if tester_code is None or pd.isna(tester_code):
        return ""

    tester_code = str(tester_code)

    marker_candidates = [
        "{{ STUDENT_ANSWER }}",
        "__student_answer__",
        "{% for TEST in TESTCASES %}",
    ]

    cut_pos = len(tester_code)

    for marker in marker_candidates:
        pos = tester_code.find(marker)
        if pos != -1:
            cut_pos = min(cut_pos, pos)

    cleaned = tester_code[:cut_pos].strip()
    return cleaned

def fix_randint_float_bounds(test_code: str) -> str:
    test_code = str(test_code)

    test_code = re.sub(
        r"randint\(([^,\n]+),\s*([0-9]+e[0-9]+)\)",
        r"randint(\1, int(\2))",
        test_code,
        flags=re.I,
    )

    test_code = re.sub(
        r"randint\(([0-9]+e[0-9]+),\s*([^)\n]+)\)",
        r"randint(int(\1), \2)",
        test_code,
        flags=re.I,
    )

    return test_code


def test_python(student_code: str, test_code: str, tester_code: str = "", timeout: int = DEFAULT_TIMEOUT):
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "main.py"

        cleaned_tester = clean_tester(tester_code)
        student_answer_literal = repr(student_code)
        test_code = fix_randint_float_bounds(test_code)

        full_code = f'''__student_answer__ = {student_answer_literal}

{cleaned_tester}

{student_code}

{test_code}
'''
        script_path.write_text(full_code, encoding="utf-8")

        try:
            result = subprocess.run(
                ["python3", str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
                "timed_out": False,
                "stage": "run"
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout}s",
                "returncode": -1,
                "timed_out": True,
                "stage": "timeout"
            }