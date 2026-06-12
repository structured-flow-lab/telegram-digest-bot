# Implementation Plan — Telegram Digest Bot

## Согласованные решения

| Вопрос | Решение |
|---|---|
| Интерфейс | Telegram-бот — он и есть UI, веб-фронтенд не нужен |
| Хостинг | Локально для MVP → Railway когда нужен деплой |
| Bot framework | `python-telegram-bot` 21.x |
| Чтение каналов | `Telethon` 1.36.x |
| База данных | SQLite (файл рядом с кодом) |
| LLM для Personal MVP | Claude Haiku (`claude-haiku-4-5`) через Anthropic API |
| LLM для multi-user | Абстрактный слой `app/llm/` — модель выбирается через конфиг |
| Подготовка к multi-user | Только LLM-абстракция сейчас; таблицы users/планы — во втором MVP |

---

## Стек

```
python-telegram-bot   — бот, команды, middleware
Telethon              — чтение публичных каналов по MTProto
SQLite (aiosqlite)    — локальное хранилище
anthropic SDK         — вызов Claude Haiku
python-dotenv         — переменные окружения
Railway               — хостинг (позже)
```

---

## Структура проекта

```
digest-bot/
├── app/
│   ├── main.py                   — точка входа, запуск бота
│   ├── config.py                 — env-переменные + лимиты
│   ├── bot/
│   │   ├── handlers.py           — /start /add /remove /channels /digest /help
│   │   └── messages.py           — все текстовые ответы бота
│   ├── reader/
│   │   ├── telethon_client.py    — инициализация Telethon, session
│   │   └── posts.py              — fetch_posts(channel, since_date)
│   ├── digest/
│   │   ├── collector.py          — собрать посты по каналам за N дней
│   │   ├── filter.py             — убрать мусор, дубликаты, слишком короткие
│   │   ├── summarizer.py         — вызов LLM-клиента, сохранение usage
│   │   └── formatter.py          — форматирование ответа для Telegram
│   ├── llm/
│   │   ├── base.py               — Protocol: complete(prompt, context) → LLMResult
│   │   ├── claude.py             — ClaudeClient (Anthropic SDK)
│   │   └── factory.py            — get_llm_client() читает LLM_PROVIDER из конфига
│   ├── storage/
│   │   ├── db.py                 — подключение к SQLite
│   │   ├── migrations.py         — создание таблиц при старте
│   │   └── repositories.py       — ChannelRepo, PostsCacheRepo, DigestRunRepo, LLMUsageRepo
│   └── prompts/
│       └── digest_v1.md          — промпт для группировки и суммаризации
├── data/
│   └── digest_bot.sqlite
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

---

## LLM-абстракция (единственная подготовка к multi-user сейчас)

Вместо прямого вызова Claude в `summarizer.py` — один тонкий слой:

```python
# app/llm/base.py
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str

class LLMClient(Protocol):
    async def complete(self, prompt: str, context: str) -> LLMResult: ...

# app/llm/factory.py
def get_llm_client() -> LLMClient:
    provider = config.LLM_PROVIDER  # "claude" | "openai" | "gemini"
    if provider == "claude":
        return ClaudeClient(model=config.LLM_MODEL)
    ...
```

`.env`:
```
LLM_PROVIDER=claude
LLM_MODEL=claude-haiku-4-5-20251001
```

Позже для multi-user: добавить `OpenAIClient`, `GeminiClient` — `summarizer.py` не трогаем.

---

## Фазы реализации

### Фаза 0 — Основа (1 день)
Цель: проект запускается, бот отвечает `/start` только владельцу.

- [ ] Структура папок и пустые файлы
- [ ] `app/config.py` — все env-переменные + лимиты (MAX_DAYS=30, MAX_CHANNELS=20, MAX_POSTS_PER_DIGEST=300, MAX_POSTS_PER_CHANNEL=100)
- [ ] `app/storage/db.py` + `app/storage/migrations.py` — SQLite + схема из PRD
- [ ] `app/main.py` — запуск бота, owner-guard middleware
- [ ] `app/bot/handlers.py` — `/start`, `/help`
- [ ] `app/bot/messages.py` — тексты ответов
- [ ] `.env.example`, `requirements.txt`

**Готово когда:** `python app/main.py` → бот отвечает `/start` только `OWNER_TELEGRAM_ID`, чужие игнорируются.

---

### Фаза 1 — Управление каналами (0.5 дня)
Цель: `/add`, `/remove`, `/channels` работают.

- [ ] `ChannelRepo` в `repositories.py`: add, remove, list, exists
- [ ] Handlers: `/add @channel`, `/remove @channel`, `/channels`
- [ ] Валидация: дубликат, лимит 20 каналов, неверный формат username
- [ ] Ошибки возвращают понятное сообщение, не крашат бота

**Готово когда:** можно добавить @vc_ru, увидеть в `/channels`, удалить.

---

### Фаза 2 — Чтение каналов (1 день)
Цель: Telethon читает посты, кэш работает.

- [ ] `app/reader/telethon_client.py` — инициализация, session-файл в `data/`
- [ ] `app/reader/posts.py` — `fetch_posts(channel_username, since_date) → list[Post]`
- [ ] Проверка доступности канала при `/add` (до сохранения в БД)
- [ ] `PostsCacheRepo` — upsert постов, get_cached_since(channel, date)
- [ ] Логика кэша: запрашивать у Telegram только посты новее `max(posted_at)` в кэше
- [ ] Обработка: канал недоступен, flood wait, пустой канал

**Готово когда:** `/add @vc_ru` проверяет доступность. Повторный digest за тот же период не идёт в Telegram — берёт из кэша.

---

### Фаза 3 — Digest pipeline (1.5 дня)
Цель: `/digest 7` возвращает сгруппированный дайджест.

- [ ] `app/llm/base.py` — `LLMResult`, `LLMClient` Protocol
- [ ] `app/llm/claude.py` — `ClaudeClient` через `anthropic` SDK
- [ ] `app/llm/factory.py` — `get_llm_client()` по конфигу
- [ ] `app/prompts/digest_v1.md` — промпт: выдели 3–7 тем, summary по каждой, верни ссылки
- [ ] `app/digest/collector.py` — собрать посты из кэша + дочитать новые
- [ ] `app/digest/filter.py` — убрать: без текста, <100 символов, дубликаты
- [ ] `app/digest/summarizer.py` — вызов LLM-клиента, сохранение в `llm_usage`
- [ ] `app/digest/formatter.py` — форматирование для Telegram (Markdown, ссылки)
- [ ] `DigestRunRepo`, `LLMUsageRepo` в `repositories.py`
- [ ] Handlers: `/digest <days>`, `/digest @channel <days>`
- [ ] Сразу отвечать "⏳ Формирую дайджест..." → запустить в `asyncio.create_task()`
- [ ] Обработка: пустой дайджест, ошибка LLM, timeout

**Готово когда:** `/digest 7` возвращает 3–7 тематических блоков со ссылками на оригиналы.

---

### Фаза 4 — Полировка и деплой (1 день) ✅ Готово

Цель: стабильная работа, готово к деплою на Railway.

- [x] Логирование ошибок (в таблицу и в консоль)
- [x] ~~Webhook-режим для деплоя~~ — отказались, polling работает и на Railway (см. amended ADR 005)
- [x] `Dockerfile` для Railway
- [x] README: setup локально + деплой на Railway
- [x] Проверить все 9 критериев готовности из PRD

**Готово когда:** все критерии из PRD выполнены, бот работает стабильно локально и на Railway.
См. [feature-006](requirements/feature-006-phase4-polish-deploy.md) и
[retro 006](retrospectives/006-phase4-polish-deploy.md). Бот задеплоен на
Railway и работает (102/102 теста зелёные).

---

## Архитектурные решения

**Owner-guard — один middleware, не в каждом handler**
```python
async def owner_only(update, context, next_handler):
    if update.effective_user.id != config.OWNER_TELEGRAM_ID:
        return  # молча игнорируем
    await next_handler(update, context)
```

**Длинный digest — не блокирует бота**
```python
async def digest_handler(update, context):
    await update.message.reply_text("⏳ Формирую дайджест...")
    asyncio.create_task(run_digest(update, context))
```

**Промпт — файл, не строка**
`app/prompts/digest_v1.md` версионируется. Версия сохраняется в `llm_usage`.
При изменении промпта → новый файл `digest_v2.md`, старые запуски сохраняют историю.

**Лимиты — в `config.py`, не в коде**
Сейчас константы. В multi-user MVP станут полями таблицы `plans`.

**Telethon session**
При первом запуске — интерактивная авторизация через терминал.
Session сохраняется в `data/telethon.session`.
На Railway — подключить persistent volume для папки `data/`.

---

## Что нужно перед стартом

1. **Telegram Bot Token** — создать бота через @BotFather
2. **Telegram API credentials** — `api_id` и `api_hash` на [my.telegram.org](https://my.telegram.org)
3. **Anthropic API key** — завести аккаунт на [console.anthropic.com](https://console.anthropic.com) (отдельно от claude.ai подписки)
4. **OWNER_TELEGRAM_ID** — свой Telegram user ID (можно узнать у @userinfobot)

Всё это идёт в `.env` (не в git).
