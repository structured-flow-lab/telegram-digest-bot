# ADR 003 — SQLite как хранилище для Personal MVP

## Статус
Принято

## Контекст

Нужно хранить каналы, кэш постов, историю digest-запросов и LLM usage.
Personal MVP — один пользователь, локальный запуск или Railway с одним инстансом.

Варианты рассматривались:
- SQLite (файл рядом с кодом)
- Turso (LibSQL — SQLite поверх HTTP, cloud)
- PostgreSQL (Supabase, Neon, Railway Postgres)

## Решение

Использовать **SQLite** через `aiosqlite` (async-драйвер).

Файл базы данных: `data/digest_bot.sqlite`  
Подключение: `aiosqlite.connect(config.DB_PATH)`

Схема из PRD: `channels`, `posts_cache`, `digest_runs`, `llm_usage`.

Миграции — простой скрипт `migrations.py` с `CREATE TABLE IF NOT EXISTS`.
Для Personal MVP этого достаточно; Alembic добавлять не нужно.

## Последствия

**Плюсы:**
- Нет внешних зависимостей — работает из коробки на любой машине.
- Для одного пользователя производительности более чем достаточно.
- `aiosqlite` полностью async — не блокирует event loop бота.
- При переходе на Turso меняется только строка подключения в `db.py`.
- При переходе на Postgres меняется только `db.py` (все SQL-запросы стандартные).

**Минусы:**
- Файл БД нужно включить в persistent volume на Railway.
- Нет встроенного connection pooling (не нужен при одном пользователе).
- Нет встроенных инструментов для миграций схемы (достаточно `IF NOT EXISTS` сейчас).

## Путь к multi-user

1. Personal MVP: SQLite-файл в `data/`.
2. При деплое на Railway: persistent volume для `data/`.
3. При переходе к multi-user: рассмотреть Turso (если хотим остаться на SQLite-синтаксисе)
   или Postgres (если нужны конкурентные записи от многих пользователей).
   В обоих случаях меняется только `db.py`.
