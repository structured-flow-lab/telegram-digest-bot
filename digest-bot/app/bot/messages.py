"""All bot reply strings — never hard-code text in handlers."""

START = (
    "👋 Привет! Я дайджест-бот.\n\n"
    "Добавляй публичные Telegram-каналы и запрашивай краткий AI-дайджест "
    "за нужный период.\n\n"
    "Напиши /help чтобы увидеть список команд."
)

HELP = (
    "📋 <b>Команды бота</b>\n\n"
    "/start — приветствие\n"
    "/help — этот список\n"
    "/add @channel — добавить канал\n"
    "/remove @channel — удалить канал\n"
    "/channels — список добавленных каналов\n"
    "/digest &lt;days&gt; — дайджест по всем каналам за N дней\n"
    "/digest @channel &lt;days&gt; — дайджест по одному каналу за N дней"
)

# --- Channel management ---

CHANNEL_ADDED = "✅ Канал @{username} добавлен."

CHANNEL_INVALID_FORMAT = (
    "⚠️ Некорректное имя канала. Укажите имя в формате @username "
    "(от 5 до 32 символов: латинские буквы, цифры, подчёркивания)."
)

CHANNEL_ALREADY_EXISTS = "ℹ️ Канал @{username} уже добавлен."

CHANNEL_LIMIT_REACHED = (
    "🚫 Достигнут лимит каналов ({limit}). Удалите канал перед добавлением нового."
)

CHANNEL_REMOVED = "🗑 Канал @{username} удалён."

CHANNEL_NOT_FOUND = "⚠️ Канал @{username} не найден в списке."

CHANNELS_EMPTY = "📭 Список каналов пуст. Добавьте канал через /add @channel."

CHANNELS_HEADER = "📡 <b>Добавленные каналы</b>"

GENERIC_ERROR = "⚠️ Что-то пошло не так. Попробуйте ещё раз позже."

CHANNEL_NOT_FOUND_ON_TELEGRAM = (
    "❌ Канал @{username} не найден в Telegram. Проверьте имя пользователя."
)

CHANNEL_NOT_PUBLIC = (
    "🔒 Канал @{username} не является публичным каналом и не может быть добавлен."
)
