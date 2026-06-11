# ADR 005 — Bot framework: python-telegram-bot + Railway hosting

## Статус
Принято

## Контекст

Нужно выбрать:
1. Библиотеку для Telegram-бота (интерфейс команд).
2. Режим работы: polling vs webhook.
3. Хостинг для деплоя.

## Решение

### Bot framework: `python-telegram-bot` 21.x

Зрелая, хорошо документированная async-библиотека.
Поддерживает Application builder, middleware, ConversationHandler.
Активно поддерживается, совместима с Telethon в одном async event loop.

### Режим работы

**Обновлено в feature-006:** polling — и локально, и на Railway. Railway
держит процесс постоянно живым (это не serverless), так что polling работает
там без отличий от локального запуска. Webhook не даёт выигрыша для personal
MVP и потребовал бы новой зависимости (`python-telegram-bot[webhooks]` →
`tornado`). `BOT_MODE`/`WEBHOOK_URL` убраны из конфига — `main.py` всегда
вызывает `run_polling()`. См.
[feature-006](../requirements/feature-006-phase4-polish-deploy.md).

### Хостинг: Railway

Railway — простейший деплой Python-приложений:
- `Dockerfile` или автодетект Python — работает из коробки.
- Persistent volume для `data/` (SQLite + Telethon session).
- Free tier: $5 кредитов при регистрации; личный бот потребляет мало.
- Webhook-URL предоставляется автоматически.

## Последствия

**Плюсы:**
- `python-telegram-bot` и Telethon хорошо уживаются в одном `asyncio` приложении.
- Railway не требует настройки сервера — `git push` → деплой.
- Persistent volume решает проблему SQLite-файла и Telethon session на сервере.

**Минусы:**
- Railway free tier имеет лимиты — при росте нагрузки нужен платный план.
- Webhook требует валидного HTTPS — решается Railway автоматически.
- При масштабировании на multi-user может понадобиться Render или Fly.io
  (лучше подходят для 24/7 long-running процессов).

## Альтернативы хостинга

| Вариант | Плюс | Минус |
|---|---|---|
| Railway | Простой деплой, persistent volumes | Лимиты free tier |
| Render | Хороший free tier | Cold start на бесплатном |
| Fly.io | Гибкий, глобальный | Сложнее в настройке |
| VPS (Hetzner, DigitalOcean) | Полный контроль | Нужна настройка сервера |
| Vercel | — | Несовместим с Telethon и SQLite |

Для Personal MVP — Railway. При переходе к multi-user пересмотреть.
