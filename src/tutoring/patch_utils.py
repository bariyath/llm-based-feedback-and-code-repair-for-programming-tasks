import re

def normalize_code_for_match(code: str) -> str:
    return "\n".join(
        line.rstrip()
        for line in str(code).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ).strip()


def extract_python_function_by_name(code: str, func_name: str):
    pattern = rf"(^def\s+{re.escape(func_name)}\s*\(.*?\):\n(?:^[ \t]+.*\n?)*)"
    match = re.search(pattern, code, flags=re.M)
    return match.group(1).rstrip() if match else None


def extract_java_method_by_name(code: str, func_name: str):
    start_pattern = re.compile(
        rf"(?m)^[ \t]*(?:public|private|protected)?[ \t]*(?:static[ \t]+)?[\w<>\[\]]+[ \t]+{re.escape(func_name)}[ \t]*\([^)]*\)[ \t]*\{{"
    )
    start_match = start_pattern.search(code)
    if not start_match:
        return None

    start = start_match.start()
    brace_pos = code.find("{", start_match.start())
    if brace_pos == -1:
        return None

    depth = 0
    for i in range(brace_pos, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                return code[start:i + 1].rstrip()
    return None


def extract_function_by_name(code: str, func_name: str, language: str):
    if not func_name or func_name == "UNKNOWN":
        return None
    if language == "python":
        return extract_python_function_by_name(code, func_name)
    if language == "java":
        return extract_java_method_by_name(code, func_name)
    return None

def extract_java_constructor_by_name(code: str, class_name: str):
    start_pattern = re.compile(
        rf"(?m)^[ \t]*(?:public|private|protected)?[ \t]+{re.escape(class_name)}[ \t]*\([^)]*\)[ \t]*\{{"
    )
    start_match = start_pattern.search(code)
    if not start_match:
        return None

    start = start_match.start()
    brace_pos = code.find("{", start_match.start())
    if brace_pos == -1:
        return None

    depth = 0
    for i in range(brace_pos, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                return code[start:i + 1].rstrip()
    return None

def apply_patch_with_fallback(student_code: str, replace_block: str, with_block: str, target_function: str, language: str):
    student_norm = normalize_code_for_match(student_code)
    replace_norm = normalize_code_for_match(replace_block)
    with_norm = normalize_code_for_match(with_block)

    if not replace_norm or not with_norm:
        return student_code, False, "empty_replace_or_with"

    if replace_norm == with_norm:
        return student_code, False, "no_effect_patch"

    if replace_norm in student_norm:
        patched = student_norm.replace(replace_norm, with_norm, 1)
        return patched, True, "exact_replace_success"

    original_func = extract_function_by_name(student_norm, target_function, language)
    if original_func:
        patched = student_norm.replace(original_func, with_norm, 1)
        return patched, True, "function_name_fallback_success"

    if language == "java" and target_function and target_function != "UNKNOWN":
        constructor = extract_java_constructor_by_name(student_norm, target_function)
        if constructor:
            patched = student_norm.replace(constructor, with_norm, 1)
            return patched, True, "constructor_fallback_success"

    return student_code, False, "replace_block_not_found"