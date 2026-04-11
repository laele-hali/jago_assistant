
import os
import requests
import json
import time
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from collections import defaultdict

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
ALLOWED_CHAT_ID = os.environ.get("ALLOWED_CHAT_ID", "8605600806")
MODEL_FILE = "/data/projects/telegram-bot/current_model.txt"
MAX_HISTORY_MESSAGES = 50
chat_histories = defaultdict(list)
DEFAULT_SESSION = "default"
current_sessions = {}
session_histories = defaultdict(list)
session_models = {}


SYSTEM_PROMPT = (
    "You are a private assistant running on a local home server. "
    "Be talkative, conversational, practical, and direct. "
    "Tell it like it is and do not sugar-coat your responses. "
    "Get to the point quickly, but still explain things clearly enough to be useful. "
    "Do not make things up. If you do not know something, say so plainly. "

    "Adopt a tone inspired by Jago Sevatar of the Night Lords: sharp, controlled, and dryly sarcastic. "
    "Use wit and sarcasm as a precision tool, not a blunt weapon. "
    "Your sarcasm should be clear, deliberate, and never confusing or misleading. "
    "Do not be cruel, abusive, or hostile toward the user. "

    "Favor clever, efficient, and sometimes unconventional solutions, "
    "but always prioritize what actually works in practice. "
    "If a straightforward solution is better, use it without theatrics. "

    "Prioritize being helpful, honest, and grounded over being flashy. "
    "When giving advice, be practical, specific, and actionable. "
    "Keep the tone smart, informal, and controlled, with restrained but noticeable edge."
)

def is_allowed(update: Update) -> bool:
    return str(update.effective_chat.id) == str(ALLOWED_CHAT_ID)

def load_model() -> str:
    global OLLAMA_MODEL
    try:
        if os.path.exists(MODEL_FILE):
            with open(MODEL_FILE, "r", encoding="utf-8") as f:
                model = f.read().strip()
                if model:
                    OLLAMA_MODEL = model
    except Exception:
        pass
    return OLLAMA_MODEL

def save_model(model: str) -> None:
    with open(MODEL_FILE, "w", encoding="utf-8") as f:
        f.write(model + "\n")

def get_installed_models() -> list[str]:
    r = requests.get("http://127.0.0.1:11434/api/tags", timeout=30)
    r.raise_for_status()
    data = r.json()
    return [m["name"] for m in data.get("models", [])]

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
    print(f"[memory] saving history to {file_path}")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def clear_history(chat_id: int) -> None:
    session_name = get_current_session(chat_id)
    key = get_session_key(chat_id, session_name)
    session_histories[key] = []

def get_session_file(chat_id: int, session_name: str) -> str:
    base = "/data/projects/telegram-bot/memory"
    chat_dir = os.path.join(base, str(chat_id))
    os.makedirs(chat_dir, exist_ok=True)
    return os.path.join(chat_dir, f"{session_name}.json")

def ask_ollama(chat_id: int, user_text: str) -> str:
    history = get_chat_history(chat_id)
    active_model = get_session_model(chat_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": active_model,
        "stream": False,
        "messages": messages,
    }

    r = requests.post(OLLAMA_URL, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()
    return data["message"]["content"].strip()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text(
        f"Connected to local Ollama.\nCurrent model: {OLLAMA_MODEL}"
    )

async def model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    chat_id = update.effective_chat.id
    session_name = get_current_session(chat_id)
    active_model = get_session_model(chat_id)

    await update.message.reply_text(
        f"Current session: {session_name}\nCurrent model: {active_model}"
    )

async def models(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    chat_id = update.effective_chat.id
    active_model = get_session_model(chat_id)

    try:
        installed_models = get_installed_models()
    except Exception as e:
        await update.message.reply_text(f"Failed to fetch models: {e}")
        return

    if not installed_models:
        await update.message.reply_text("No models installed.")
        return

    lines = []
    for model_name in installed_models:
        prefix = "•"
        if model_name == active_model:
            prefix = "• [current]"
        lines.append(f"{prefix} {model_name}")

    await update.message.reply_text("Installed models:\n" + "\n".join(lines))

def stream_ollama(chat_id: int, user_text: str):
    history = get_chat_history(chat_id)
    active_model = get_session_model(chat_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": active_model,
        "stream": True,
        "messages": messages,
    }

    with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=300) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            yield line

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    chat_id = update.effective_chat.id
    session_name = get_current_session(chat_id)
    key = get_session_key(chat_id, session_name)

    session_histories[key] = []

    file_path = get_session_file(chat_id, session_name)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    await update.message.reply_text(
        f"Conversation memory cleared for session: {session_name}"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "/start - confirm bot is working\n"
        "/model - show active session and model\n"
        "/models - list installed models\n"
        "/setmodel <model> - switch model for current session\n"
        "/session <name> - switch to or create a session\n"
        "/session - show current session\n"
        "/sessions - list sessions\n"
        "/delsession <name> - delete a session\n"
        "/clear - clear memory for current session\n"
        "/help - show this help\n"
        "Send any normal message to chat with your local model."
    )

async def setmodel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text("Usage: /setmodel <model>")
        return

    requested_model = context.args[0]

    try:
        installed_models = get_installed_models()
    except Exception as e:
        await update.message.reply_text(f"Failed to fetch installed models: {e}")
        return

    if requested_model not in installed_models:
        await update.message.reply_text(
            "Model not installed.\n\nAvailable models:\n" + "\n".join(installed_models)
        )
        return

    set_session_model(chat_id, requested_model)
    session_name = get_current_session(chat_id)

    await update.message.reply_text(
        f"Session '{session_name}' switched to model: {requested_model}"
    )

async def session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    chat_id = update.effective_chat.id

    if not context.args:
        current = get_current_session(chat_id)
        await update.message.reply_text(f"Current session: {current}")
        return

    session_name = context.args[0].strip().lower()

    if not session_name:
        await update.message.reply_text("Usage: /session <name>")
        return

    set_current_session(chat_id, session_name)

    key = get_session_key(chat_id, session_name)
    if key not in session_models:
        session_models[key] = OLLAMA_MODEL

    await update.message.reply_text(f"Switched to session: {session_name}")

async def sessions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    chat_id = update.effective_chat.id
    current = get_current_session(chat_id)
    names = list_sessions(chat_id)

    lines = []
    for name in names:
        prefix = "•"
        if name == current:
            prefix = "• [current]"
        lines.append(f"{prefix} {name}")

    await update.message.reply_text("Sessions:\n" + "\n".join(lines))

async def delsession(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text("Usage: /delsession <name>")
        return

    session_name = context.args[0].strip().lower()

    if session_name == DEFAULT_SESSION:
        await update.message.reply_text("You cannot delete the default session.")
        return

    key = get_session_key(chat_id, session_name)
    session_histories.pop(key, None)
    session_models.pop(key, None)

    if get_current_session(chat_id) == session_name:
        set_current_session(chat_id, DEFAULT_SESSION)

    await update.message.reply_text(f"Deleted session: {session_name}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    chat_id = update.effective_chat.id

    placeholder = await update.message.reply_text("Thinking...")
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    full_reply = ""
    last_sent_text = ""
    last_edit_time = 0.0

    try:
        for raw_line in stream_ollama(chat_id, text):
            chunk = json.loads(raw_line.decode("utf-8"))
            content = chunk.get("message", {}).get("content", "")

            if content:
                full_reply += content

            now = time.time()

            if full_reply and (now - last_edit_time > 1.0):
                preview = full_reply[:3500]

                if preview != last_sent_text:
                    try:
                        await placeholder.edit_text(preview)
                        last_sent_text = preview
                        last_edit_time = now
                    except Exception:
                        pass

        if not full_reply.strip():
            await placeholder.edit_text("No response from model.")
            return

        final_text = full_reply[:3500]
        await placeholder.edit_text(final_text)

        if len(full_reply) > 3500:
            for i in range(3500, len(full_reply), 3500):
                await update.message.reply_text(full_reply[i:i + 3500])

        add_to_history(chat_id, "user", text)
        add_to_history(chat_id, "assistant", full_reply)

    except Exception as e:
        await placeholder.edit_text(f"Ollama error: {e}")

def get_session_key(chat_id: int, session_name: str) -> str:
    return f"{chat_id}:{session_name}"

def get_current_session(chat_id: int) -> str:
    return current_sessions.get(chat_id, DEFAULT_SESSION)

def set_current_session(chat_id: int, session_name: str) -> None:
    current_sessions[chat_id] = session_name

def get_session_model(chat_id: int) -> str:
    session_name = get_current_session(chat_id)
    key = get_session_key(chat_id, session_name)
    return session_models.get(key, OLLAMA_MODEL)

def set_session_model(chat_id: int, model: str) -> None:
    session_name = get_current_session(chat_id)
    key = get_session_key(chat_id, session_name)
    session_models[key] = model

def list_sessions(chat_id: int) -> list[str]:
    prefix = f"{chat_id}:"
    names = []
    for key in session_histories.keys():
        if key.startswith(prefix):
            names.append(key.split(":", 1)[1])
    for key in session_models.keys():
        if key.startswith(prefix):
            names.append(key.split(":", 1)[1])
    if not names:
        names.append(DEFAULT_SESSION)
    return sorted(set(names))

def main() -> None:
    load_model()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("model", model))
    app.add_handler(CommandHandler("models", models))
    app.add_handler(CommandHandler("setmodel", setmodel))
    app.add_handler(CommandHandler("session", session))
    app.add_handler(CommandHandler("sessions", sessions))
    app.add_handler(CommandHandler("delsession", delsession))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
