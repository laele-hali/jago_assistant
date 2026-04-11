import json
import os
from collections import defaultdict

from config import DEFAULT_SESSION, MAX_HISTORY_MESSAGES, MEMORY_BASE_DIR, MODEL_FILE, OLLAMA_MODEL

current_sessions = {}
session_histories = defaultdict(list)
session_models = {}
last_used_models = {}

def load_default_model() -> str:
    model = OLLAMA_MODEL
    try:
        if os.path.exists(MODEL_FILE):
            with open(MODEL_FILE, "r", encoding="utf-8") as f:
                loaded = f.read().strip()
                if loaded:
                    model = loaded
    except Exception:
        pass
    return model


def save_default_model(model: str) -> None:
    with open(MODEL_FILE, "w", encoding="utf-8") as f:
        f.write(model + "\n")


def get_session_key(chat_id: int, session_name: str) -> str:
    return f"{chat_id}:{session_name}"


def get_current_session_file(chat_id: int) -> str:
    os.makedirs(MEMORY_BASE_DIR, exist_ok=True)
    return os.path.join(MEMORY_BASE_DIR, f"{chat_id}_current_session.txt")


def get_current_session(chat_id: int) -> str:
    if chat_id in current_sessions:
        return current_sessions[chat_id]

    file_path = get_current_session_file(chat_id)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                session_name = f.read().strip()
                if session_name:
                    current_sessions[chat_id] = session_name
                    return session_name
        except Exception:
            pass

    current_sessions[chat_id] = DEFAULT_SESSION
    return DEFAULT_SESSION


def set_current_session(chat_id: int, session_name: str) -> None:
    current_sessions[chat_id] = session_name
    file_path = get_current_session_file(chat_id)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(session_name + "\n")


def get_session_model(chat_id: int, default_model: str) -> str:
    session_name = get_current_session(chat_id)
    key = get_session_key(chat_id, session_name)
    return session_models.get(key, default_model)


def set_session_model(chat_id: int, model: str) -> None:
    session_name = get_current_session(chat_id)
    key = get_session_key(chat_id, session_name)
    session_models[key] = model


def get_session_file(chat_id: int, session_name: str) -> str:
    chat_dir = os.path.join(MEMORY_BASE_DIR, str(chat_id))
    os.makedirs(chat_dir, exist_ok=True)
    return os.path.join(chat_dir, f"{session_name}.json")


def get_chat_history(chat_id: int) -> list[dict]:
    session_name = get_current_session(chat_id)
    key = get_session_key(chat_id, session_name)
    file_path = get_session_file(chat_id, session_name)

    if key not in session_histories:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    session_histories[key] = json.load(f)
            except Exception:
                session_histories[key] = []
        else:
            session_histories[key] = []

    return session_histories[key]


def add_to_history(chat_id: int, role: str, content: str) -> None:
    session_name = get_current_session(chat_id)
    history = get_chat_history(chat_id)

    history.append({"role": role, "content": content})

    if len(history) > MAX_HISTORY_MESSAGES:
        del history[:-MAX_HISTORY_MESSAGES]

    file_path = get_session_file(chat_id, session_name)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def clear_history(chat_id: int) -> None:
    session_name = get_current_session(chat_id)
    key = get_session_key(chat_id, session_name)
    session_histories[key] = []


def clear_history_file(chat_id: int) -> None:
    session_name = get_current_session(chat_id)
    file_path = get_session_file(chat_id, session_name)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass


def list_sessions(chat_id: int) -> list[str]:
    prefix = f"{chat_id}:"
    names = []

    for key in session_histories.keys():
        if key.startswith(prefix):
            names.append(key.split(":", 1)[1])

    for key in session_models.keys():
        if key.startswith(prefix):
            names.append(key.split(":", 1)[1])

    chat_dir = os.path.join(MEMORY_BASE_DIR, str(chat_id))
    if os.path.isdir(chat_dir):
        for name in os.listdir(chat_dir):
            if name.endswith(".json"):
                names.append(name[:-5])

    if not names:
        names.append(DEFAULT_SESSION)

    return sorted(set(names))

def delete_session(chat_id: int, session_name: str) -> None:
    key = get_session_key(chat_id, session_name)
    session_histories.pop(key, None)
    session_models.pop(key, None)
    last_used_models.pop(key, None)

    file_path = get_session_file(chat_id, session_name)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

def set_last_used_model(chat_id: int, model: str) -> None:
    session_name = get_current_session(chat_id)
    key = get_session_key(chat_id, session_name)
    last_used_models[key] = model


def get_last_used_model(chat_id: int, default_model: str) -> str:
    session_name = get_current_session(chat_id)
    key = get_session_key(chat_id, session_name)
    return last_used_models.get(key, default_model)
