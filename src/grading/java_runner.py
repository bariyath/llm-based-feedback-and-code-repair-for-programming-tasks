import subprocess
import tempfile
from pathlib import Path
import re
import pandas as pd

def escape_java_string(code: str) -> str:
    return (
        code
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "")
        .replace("\n", "\\n")
    )

def extract_imports(tester_code: str) -> str:
    imports = []
    for line in tester_code.splitlines():
        stripped = line.strip()
        if stripped.startswith("import "):
            imports.append(stripped)
    imports = sorted(set(imports))

    required = [
        "import java.util.*;",
        "import java.util.ArrayList;",
        "import java.util.Arrays;",
        "import java.lang.Math;",
    ]
    for item in required:
        if item not in imports:
            imports.append(item)

    return "\n".join(sorted(set(imports)))

def remove_jinja_lines(text: str) -> str:
    cleaned = []
    for line in text.splitlines():
        if "{{" in line or "{%" in line or "%}" in line or "}}" in line:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)

def extract_tester_members(tester_code: str) -> str:
    if not tester_code or not str(tester_code).strip():
        return ""

    text = remove_jinja_lines(str(tester_code))

    text = text.replace("public class __tester__", "public class TEMP_CLASS")
    text = text.replace("public class Main", "public class TEMP_CLASS")

    class_match = re.search(r'public\s+class\s+\w+\s*\{(.*)\}\s*$', text, flags=re.S)
    if class_match:
        text = class_match.group(1)

    def remove_method_block(src: str, name: str) -> str:
        pattern = re.compile(rf'(?m)(public|private|protected)?\s*(static\s+)?[\w<>\[\]]+\s+{name}\s*\([^)]*\)\s*\{{')
        while True:
            m = pattern.search(src)
            if not m:
                break
            start = m.start()
            brace_start = src.find("{", m.start())
            depth = 0
            end = brace_start
            while end < len(src):
                if src[end] == "{":
                    depth += 1
                elif src[end] == "}":
                    depth -= 1
                    if depth == 0:
                        end += 1
                        break
                end += 1
            src = src[:start] + "\n" + src[end:]
        return src

    text = remove_method_block(text, "main")
    text = remove_method_block(text, "runTests")

    return text.strip()

def contains_class_definition(code: str) -> bool:
    return bool(re.search(r'\b(class|interface|enum|record)\b', str(code)))

def detect_public_class_name(code: str):
    match = re.search(r'\bpublic\s+class\s+([A-Za-z_]\w*)', str(code))
    return match.group(1) if match else None

def render_java_wrapper(student_code: str, test_code: str, tester_code: str = "") -> str:
    if tester_code is None or pd.isna(tester_code):
        tester_code = ""
    tester_code = str(tester_code)

    student_code = str(student_code).strip()
    test_code = (test_code or "").strip()
    test_code = test_code.replace("__tester__", "Main")
    if not test_code.endswith(";"):
        test_code += ";"

    imports_text = extract_imports(tester_code)
    tester_members = extract_tester_members(tester_code)
    escaped_code = escape_java_string(student_code)

    # Method based submission only
    parts = [
        imports_text,
        "",
        "public class Main {",
        f'    public String studentAnswer = "{escaped_code}";',
        "",
    ]

    if tester_members:
        parts.append(tester_members)
        parts.append("")

    parts.append(student_code)
    parts.append("")
    parts.append("    public static void main(String[] args) {")
    parts.append("        Main main = new Main();")
    parts.append("        main.runTests();")
    parts.append("    }")
    parts.append("")
    parts.append("    public void runTests() {")
    parts.append(f"        {test_code}")
    parts.append("    }")
    parts.append("}")

    return "\n".join(parts)

def render_main_for_class_submission(student_code: str, test_code: str) -> str:
    test_code = (test_code or "").strip()
    if not test_code.endswith(";"):
        test_code += ";"

    escaped_code = escape_java_string(student_code)

    return "\n".join([
        "public class Main {",
        f'    static String studentAnswer = "{escaped_code}";',
        "    public static void main(String[] args) {",
        f"        {test_code}",
        "    }",
        "}",
    ])

def test_java(student_code: str, test_code: str, tester_code="", timeout: int = 8):
    with tempfile.TemporaryDirectory() as tmpdir:
        public_class_name = detect_public_class_name(student_code)

        try:
            if public_class_name:
                # Class based submission
                student_path = Path(tmpdir) / f"{public_class_name}.java"
                main_path = Path(tmpdir) / "Main.java"

                student_path.write_text(str(student_code).strip(), encoding="utf-8")
                main_code = render_main_for_class_submission(student_code, test_code)
                main_path.write_text(main_code, encoding="utf-8")

                compile_result = subprocess.run(
                    ["javac", str(student_path), str(main_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                generated_code = (
                    f" - {public_class_name}.java \n"
                    + student_path.read_text(encoding="utf-8")
                    + "\n\n- Main.java \n"
                    + main_path.read_text(encoding="utf-8")
                )

            else:
                # Method based submission
                java_path = Path(tmpdir) / "Main.java"
                full_code = render_java_wrapper(student_code, test_code, tester_code)
                java_path.write_text(full_code, encoding="utf-8")

                compile_result = subprocess.run(
                    ["javac", str(java_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                generated_code = full_code

            if compile_result.returncode != 0:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": compile_result.stderr.strip(),
                    "returncode": compile_result.returncode,
                    "timed_out": False,
                    "stage": "compile",
                    "generated_code": generated_code,
                }

            run_result = subprocess.run(
                ["java", "-cp", tmpdir, "Main"],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                "success": run_result.returncode == 0,
                "stdout": run_result.stdout.strip(),
                "stderr": run_result.stderr.strip(),
                "returncode": run_result.returncode,
                "timed_out": False,
                "stage": "run",
                "generated_code": generated_code,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout}s",
                "returncode": -1,
                "timed_out": True,
                "stage": "timeout",
                "generated_code": "",
            }