import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def llm_feedback(prompt, model="gpt-4.1", temperature=0.0):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1600,
        temperature=temperature,
    )
    text = response.choices[0].message.content
    return text


def safe_json_loads(text: str):
    text = text.strip()

    try:
        return json.loads(text), "direct_json"
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate), "trimmed_json"
        except Exception:
            pass

    return None, "json_parse_failed"