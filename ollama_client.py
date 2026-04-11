import requests

from config import OLLAMA_URL, SYSTEM_PROMPT


def get_installed_models() -> list[str]:
    r = requests.get("http://127.0.0.1:11434/api/tags", timeout=30)
    r.raise_for_status()
    data = r.json()
    return [m["name"] for m in data.get("models", [])]


def ask_ollama(user_text: str, history: list[dict], model: str) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": model,
        "stream": False,
        "messages": messages,
    }

    r = requests.post(OLLAMA_URL, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()
    return data["message"]["content"].strip()


def stream_ollama(user_text: str, history: list[dict], model: str):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": model,
        "stream": True,
        "messages": messages,
    }

    with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=300) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            yield line
