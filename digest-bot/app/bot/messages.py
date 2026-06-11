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
