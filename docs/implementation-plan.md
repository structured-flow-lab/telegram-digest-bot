# Implementation Plan — Telegram Digest Bot

## Сначала важное: Vercel / GitHub Pages и Python-стек несовместимы

Прежде чем идти дальше, нужно честно разобраться с ограничениями.

**GitHub Pages** — только статика. Никакого серверного кода вообще.

**Vercel** — serverless-функции, но с жёсткими ограничениями:

| Ограничение | Почему это проблема для бота |
|---|---|
| Нет постоянного файлового хранилища | SQLite-файл исчезает между вызовами |
| Timeout функции 10–60 сек | Чтение 5+ каналов + LLM может занять 2–5 минут |
| Нет persistent TCP-соединений | Telethon держит постоянное MTProto-соединение — несовместимо |
| Нет фоновых процессов | python-telegram-bot в polling-режиме не запустить |

**Вывод:** Python + Telethon + SQLite в существующем виде на Vercel не заработает.
Это не workaround — это архитектурное несоответствие.

---

## Рекомендация по стеку

У нас три реальных пути. Рекомендую **Вариант A** для Personal MVP и **Вариант B** для перехода к multi-user.

### Вариант A — Python-бот на Railway + React-фронтенд на Vercel (рекомендую для MVP)

```
Telegram ──► Python-бот (Railway / Render / Fly.io, free tier)
                │  python-telegram-bot (webhook)
                │  Telethon
                │  Claude API
                └─► SQLite (на сервере) или Turso (LibSQL cloud)

Vercel ──► React SPA (только просмотр дайджестов и настроек)
           читает данные через REST API бота
```

**Плюсы:**
- Стек из PRD остаётся нетронутым — Python, Telethon, SQLite.
- Railway free tier: 500 часов/месяц, достаточно для личного бота.
- Vercel получает фронтенд — красивый UI для просмотра истории дайджестов.
- Телеграм-бот работает через webhook, не через polling → не нужен постоянно запущенный процесс.

**Минусы:**
- Два места деплоя (Railway для бота, Vercel для UI).
- Railway может "засыпать" на free tier (cold start ~5 сек).

---

### Вариант B — TypeScript-стек, всё на Vercel (лучше для multi-user)

Если важно, чтобы **весь** проект жил на Vercel:

```
Telegram ──► Vercel Functions (Next.js API routes)
                │  Grammy или Telegraf (webhook, Node.js)
                │  MTProto.js / telegram.js (чтение каналов)
                │  Anthropic SDK (Node.js)
                └─► Turso (LibSQL — SQLite-совместимая cloud БД, free tier)

Vercel ──► Next.js (фронтенд + API в одном проекте)
```

**Плюсы:**
- Один проект, один деплой.
- Turso — это SQLite поверх HTTP, работает из serverless без проблем.
- Grammy отличная замена python-telegram-bot: типобезопасный, webhook-first.
- Нет timeout-проблем для `/digest` — можно использовать Vercel Edge Functions или фоновые задачи через Vercel Cron + очередь.

**Минусы:**
- Нужно переписать Python на TypeScript (1–2 дня работы).
- `telegram.js` / MTProto.js менее стабильны чем Telethon (Telethon — де-факто стандарт).
- Для длинных digest'ов всё равно нужен workaround с timeout (streaming ответа или фоновая задача).

---

### Вариант C — Python-бот локально (без деплоя пока)

Просто запустить локально, деплой отложить. Для Personal MVP — абсолютно нормально.
Vercel/GitHub Pages — для фронтенда, когда он появится.

---

## Моя итоговая рекомендация

**Personal MVP → Вариант A:**
- Пишем Python-бот как задумано в PRD.
- Запускаем локально сначала, деплоим на Railway когда всё работает.
- React-фронтенд на Vercel добавляем позже как отдельный этап.
- Используем Turso вместо SQLite-файла — это SQLite API поверх cloud, меняется только строка подключения.

**Multi-user MVP → Вариант B:**
- Переходим на TypeScript + Next.js + Turso + Grammy.
- Vercel становится единственным местом деплоя.
- Весь Python-код переиспользуем как reference для логики — структура модулей та же.

---

## Стек Personal MVP (Вариант A, уточнённый)

| Слой | Технология | Почему |
|---|---|---|
| Bot interface | python-telegram-bot 21.x (webhook) | Стабильный, async, хорошая документация |
| Channel reader | Telethon 1.36.x | Де-факто стандарт для MTProto в Python |
| Storage | Turso (LibSQL) или SQLite-файл | Turso — тот же SQLite, но работает в cloud |
| Summarization | Claude claude-haiku-4-5 via `anthropic` SDK | Дёшево, быстро, достаточно для дайджестов |
| Config | python-dotenv | Стандарт |
| Hosting (бот) | Railway free tier | 500ч/мес, webhook, нет cold start на платном |
| Hosting (UI) | Vercel | React SPA, статика |
| CI | GitHub Actions | Линтинг + тесты при пуше |

---

## Фазы реализации

### Фаза 0 — Основа (1 день)

Цель: проект запускается, бот отвечает `/start`.

- [ ] Создать структуру папок (`app/`, `app/bot/`, `app/storage/`, etc.)
- [ ] `app/config.py` — все переменные окружения + лимиты
- [ ] `app/storage/db.py` — подключение к SQLite, init schema
- [ ] `app/storage/migrations.py` — создание таблиц при старте
- [ ] `app/main.py` — запуск бота, регистрация handlers
- [ ] `app/bot/handlers.py` — owner-guard middleware + `/start`, `/help`
- [ ] `.env.example`, `requirements.txt`
- [ ] Локальный запуск: бот отвечает только владельцу

**Готово когда:** `python app/main.py` → бот отвечает `/start` только `OWNER_TELEGRAM_ID`.

---

### Фаза 1 — Управление каналами (0.5 дня)

Цель: можно добавлять, удалять, смотреть каналы.

- [ ] `app/storage/repositories.py` — `ChannelRepo`: add, remove, list
- [ ] `app/bot/handlers.py` — `/add`, `/remove`, `/channels`
- [ ] Валидация: канал уже добавлен, лимит 20 каналов
- [ ] `app/bot/messages.py` — все текстовые ответы бота вынесены сюда

**Готово когда:** можно добавить @techcrunch, увидеть его в `/channels`, удалить.

---

### Фаза 2 — Чтение каналов (1 день)

Цель: Telethon читает посты, посты кэшируются.

- [ ] `app/reader/telethon_client.py` — инициализация Telethon, session-файл
- [ ] `app/reader/posts.py` — `fetch_posts(channel, since_date)` → список постов
- [ ] Проверка доступности канала при `/add`
- [ ] `app/storage/repositories.py` — `PostsCacheRepo`: upsert, get_cached
- [ ] Логика кэша: читать только посты новее последнего кэшированного
- [ ] Обработка ошибок: канал недоступен, флуд-лимит Telegram

**Готово когда:** `/add @vc_ru` → бот проверяет доступность и сохраняет. Повторный digest не перечитывает старые посты.

---

### Фаза 3 — Digest pipeline (1.5 дня)

Цель: `/digest 7` возвращает сгруппированный дайджест.

- [ ] `app/digest/collector.py` — собрать посты по всем каналам за N дней (из кэша + дочитать новые)
- [ ] `app/digest/filter.py` — убрать: без текста, слишком короткие, дубликаты, реклама
- [ ] `app/prompts/digest_v1.md` — промпт с инструкцией: выдели темы, дай summary, верни ссылки
- [ ] `app/digest/summarizer.py` — вызов Claude API, парсинг ответа, сохранение usage
- [ ] `app/digest/formatter.py` — форматирование итогового текста для Telegram
- [ ] `app/storage/repositories.py` — `DigestRunRepo`, `LLMUsageRepo`
- [ ] Обработка: пустой digest, LLM-ошибка, timeout

**Готово когда:** `/digest 7` возвращает 3–7 тематических блоков со ссылками.

---

### Фаза 4 — Полировка и деплой (1 день)

Цель: стабильная работа, задеплоено на Railway.

- [ ] Логирование ошибок в таблицу `errors`
- [ ] Сообщение "⏳ Формирую дайджест..." пока идёт обработка
- [ ] Webhook-режим (вместо polling) для деплоя
- [ ] `Dockerfile` или `Procfile` для Railway
- [ ] Деплой на Railway, проверка webhook через ngrok → Railway URL
- [ ] README с инструкцией запуска локально и деплоя

**Готово когда:** бот работает на Railway, все 9 критериев готовности из PRD выполнены.

---

### Фаза 5 — React UI на Vercel (опционально, после MVP)

Цель: веб-интерфейс для просмотра истории дайджестов.

- [ ] REST API на боте: `GET /digests`, `GET /channels` (с API-ключом)
- [ ] React SPA в `app/` (уже есть Vite-скелет)
- [ ] Страницы: список каналов, история дайджестов, просмотр дайджеста
- [ ] Деплой на Vercel

---

## Критические архитектурные решения

### 1. Telethon session-файл
Telethon требует session-файл (`.session`) для авторизации. Локально — просто файл.
На Railway — нужно подключить volume или сохранять session в Turso как blob.
Решение: при первом запуске интерактивная авторизация, session сохраняется в `/data/`.

### 2. Длинный digest не блокирует бота
`/digest` может занять 1–3 минуты. Нужно:
- Сразу ответить "⏳ Формирую дайджест..."
- Запустить pipeline в `asyncio.create_task()`
- Отправить результат когда готово

### 3. Промпт — отдельный файл, версионированный
`app/prompts/digest_v1.md` — не строка в коде.
При изменении промпта создаём `digest_v2.md`, сохраняем версию в `llm_usage`.

### 4. Owner-guard — один раз, на уровне middleware
Не проверять `OWNER_TELEGRAM_ID` в каждом handler.
Один middleware в `main.py` отклоняет всё от чужих пользователей.

### 5. Лимиты — в config, не в коде
```python
MAX_DAYS = 30
MAX_CHANNELS = 20
MAX_POSTS_PER_DIGEST = 300
MAX_POSTS_PER_CHANNEL = 100
```
При переходе к multi-user эти константы станут полями в таблице `plans`.

---

## Что делать прямо сейчас

1. **Подтвердить стек** — Вариант A (Python + Railway) или Вариант B (TypeScript + Vercel)?
2. **Создать `.env`** с реальными ключами (TELEGRAM_BOT_TOKEN, TELEGRAM_API_ID/HASH, ANTHROPIC_API_KEY, OWNER_TELEGRAM_ID).
3. **Получить Telegram API credentials** на [my.telegram.org](https://my.telegram.org) — нужны `api_id` и `api_hash` для Telethon.
4. Начать Фазу 0.
