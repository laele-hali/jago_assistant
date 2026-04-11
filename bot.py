import json
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

from tools import get_uptime, get_disk, get_sysinfo, run_command

from config import TELEGRAM_TOKEN, ALLOWED_CHAT_ID, OLLAMA_MODEL, DEFAULT_SESSION
from state import (
    load_default_model,
    get_current_session,
    set_current_session,
    get_session_model,
    set_session_model,
    get_chat_history,
    add_to_history,
    clear_history,
    clear_history_file,
    list_sessions,
    delete_session,
    set_last_used_model,
    get_last_used_model,
)
from ollama_client import get_installed_models, stream_ollama, ask_ollama

CURRENT_DEFAULT_MODEL = load_default_model()


def is_allowed(update: Update) -> bool:
    return str(update.effective_chat.id) == str(ALLOWED_CHAT_ID)

def maybe_use_tool(text: str) -> tuple[str | None, str | None]:
    t = text.lower()

#    print(f"[tool-check] text='{t}'")

    # normalize common phrasing noise
    t = t.replace("?", "").replace("'", "").strip()

    # uptime detection
    if (
        "uptime" in t
        or "how long" in t and ("up" in t or "running" in t)
        or "been up" in t
        or "up for" in t
        or "running for" in t
    ):
        return "uptime", get_uptime()

    # disk detection
    if (
        "disk" in t
        or "storage" in t
        or "space" in t
        or "free space" in t
        or "disk space" in t
    ):
        return "disk", get_disk()

    # cpu / memory detection
    if (
        "cpu" in t
        or "memory" in t
        or "ram" in t
        or "load" in t
        or "usage" in t
    ):
        return "sysinfo", get_sysinfo()

    return None, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text(
        f"Connected to local Ollama.\nDefault model: {CURRENT_DEFAULT_MODEL}"
    )

def choose_model(text: str, default_model: str) -> str:
    t = text.lower()

    # coding / dev detection
    if any(k in t for k in [
        "code", "python", "bash", "script",
        "function", "class", "error", "traceback",
        "debug", "fix", "write a script"
    ]):
        model = "qwen2.5-coder:7b"
        print(f"[model-route] coder selected for: {t}", flush=True)
        return model

    print(f"[model-route] default model used for: {t}", flush=True)
    return default_model

async def model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    chat_id = update.effective_chat.id
    session_name = get_current_session(chat_id)

    session_model = get_session_model(chat_id, CURRENT_DEFAULT_MODEL)
    last_used_model = get_last_used_model(chat_id, session_model)

    await update.message.reply_text(
        f"Current session: {session_name}\n"
        f"Session model: {session_model}\n"
        f"Last used model: {last_used_model}"
    )

async def models(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    chat_id = update.effective_chat.id
    active_model = get_session_model(chat_id, CURRENT_DEFAULT_MODEL)

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

    if get_session_model(chat_id, CURRENT_DEFAULT_MODEL) == CURRENT_DEFAULT_MODEL:
        set_session_model(chat_id, get_session_model(chat_id, CURRENT_DEFAULT_MODEL))

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

    delete_session(chat_id, session_name)

    if get_current_session(chat_id) == session_name:
        set_current_session(chat_id, DEFAULT_SESSION)

    await update.message.reply_text(f"Deleted session: {session_name}")


async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text(get_uptime())


async def disk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text(get_disk())


async def sysinfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text(get_sysinfo())


async def run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    if not context.args:
        await update.message.reply_text("Usage: /run <command>")
        return

    cmd = " ".join(context.args)

    # minimal safety for now
    blocked = ["rm ", "shutdown", "reboot", "mkfs", ":(){:|:&};:"]
    if any(b in cmd for b in blocked):
        await update.message.reply_text("Command blocked.")
        return

    output = run_command(cmd)

    # Telegram limit
    if len(output) > 3500:
        output = output[:3500] + "\n...truncated"

    await update.message.reply_text(output)

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    chat_id = update.effective_chat.id
    session_name = get_current_session(chat_id)

    clear_history(chat_id)
    clear_history_file(chat_id)

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
        "/uptime - show system uptime\n"
        "/disk - show disk usage\n"
        "/sysinfo - show system stats\n"
        "/run <cmd> - run shell command (restricted)\n"
   "Send any normal message to chat with your local model."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        returns

    text = (update.message.text or "").strip()
    if not text:
        return

    chat_id = update.effective_chat.id
    history = get_chat_history(chat_id)
    session_model = get_session_model(chat_id, CURRENT_DEFAULT_MODEL)
    active_model = choose_model(text, session_model)
    set_last_used_model(chat_id, active_model)
    tool_name, tool_result = maybe_use_tool(text)

    if tool_result:
        prompt = (
            f"The user asked: {text}\n\n"
            f"Tool used: {tool_name}\n"
            f"Raw output:\n{tool_result}\n\n"
            "Explain this clearly and practically."
        )

        reply = ask_ollama(prompt, history, active_model)

        await update.message.reply_text(reply[:3500])

        add_to_history(chat_id, "user", text)
        add_to_history(chat_id, "assistant", reply)
        return

    placeholder = await update.message.reply_text("Thinking...")
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    full_reply = ""
    last_sent_text = ""
    last_edit_time = 0.0

    try:
        for raw_line in stream_ollama(text, history, active_model):
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

def main() -> None:
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
    app.add_handler(CommandHandler("uptime", uptime))
    app.add_handler(CommandHandler("disk", disk))
    app.add_handler(CommandHandler("sysinfo", sysinfo))
    app.add_handler(CommandHandler("run", run))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
