# Feature 004 — Digest pipeline (`/digest`)

## Goal

`/digest <days>` and `/digest @channel <days>` produce a thematic, AI-generated digest of
cached + freshly-fetched posts, with links back to the originals. This is the core value
proposition of the bot (Phase 3 of the implementation plan).

## User story

As the bot owner, I want `/digest 7` to read posts from all my channels for the last 7 days,
group them into a handful of themes with short summaries and links, and send me the result —
without blocking the bot while it's working.

## Scope

- `app/llm/base.py` — `LLMResult`, `LLMClient` Protocol, `LLMError`.
- `app/llm/claude.py` — `ClaudeClient` (Anthropic SDK).
- `app/llm/factory.py` — `get_llm_client()`.
- `app/digest/filter.py` — `filter_posts()`.
- `app/digest/collector.py` — `collect_posts()`.
- `app/digest/summarizer.py` — `summarize()`, `DigestError`.
- `app/digest/formatter.py` — `format_digest()`, `format_empty_digest()`.
- `app/storage/repositories.py` — `DigestRunRepo`, `LLMUsageRepo`.
- `app/bot/handlers.py` — `/digest` handler + background `run_digest()`.
- `app/bot/messages.py` — new message templates.
- `app/prompts/digest_v1.md` — versioned prompt.

## Acceptance criteria

### LLM abstraction (app/llm/)

- AC-001: `LLMResult` is a dataclass with fields `text: str`, `input_tokens: int`,
  `output_tokens: int`, `model: str`.
- AC-002: `LLMClient` is a `Protocol` defining
  `async def complete(self, prompt: str, context: str) -> LLMResult`.
- AC-003: `ClaudeClient(model: str)` implements `LLMClient`. `complete(prompt, context)` calls
  the Anthropic SDK (`anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)`,
  `messages.create(...)`) with `prompt` as the system instructions and `context` as the user
  message, and returns an `LLMResult` built from the response (`text` = concatenated text
  blocks, `input_tokens`/`output_tokens` from `response.usage`, `model` = the configured model
  name).
- AC-004: `ClaudeClient.complete()` catches any exception raised by the Anthropic SDK and
  re-raises it wrapped as `LLMError`.
- AC-005: `get_llm_client()` returns a `ClaudeClient(model=config.LLM_MODEL)` when
  `config.LLM_PROVIDER == "claude"`.
- AC-006: `get_llm_client()` raises `ValueError` for any other `config.LLM_PROVIDER` value.

### Filter (app/digest/filter.py)

- AC-010: `filter_posts(posts)` drops posts whose `text` is `None` or empty/whitespace-only.
- AC-011: `filter_posts(posts)` drops posts whose stripped `text` is shorter than
  `MIN_POST_LENGTH = 100` characters.
- AC-012: `filter_posts(posts)` drops exact-duplicate posts — same `text` after
  case-insensitive, whitespace-stripped comparison — keeping only the first occurrence.
- AC-013: `filter_posts(posts)` preserves the relative order of the remaining posts.

### Collector (app/digest/collector.py)

- AC-020: `collect_posts(conn, channels, days)` is `async`, taking an open `aiosqlite.Connection`
  (for `PostsCacheRepo`). For each `Channel`, it determines
  `since = max(latest_cached_at(channel.id), now - days)`-style cutoff, calls
  `fetch_posts(channel.username, since=..., limit=config.MAX_POSTS_PER_CHANNEL)`, upserts the
  result via `PostsCacheRepo.upsert_posts()`, then reads back
  `get_cached_since(channel.id, since=cutoff_for_digest, limit=config.MAX_POSTS_PER_CHANNEL)`.
- AC-021: Returns a tuple `(posts, posts_fetched)` where `posts` is a list of `CollectedPost`
  (cached-post fields plus `channel_username`), merged across all channels and sorted by
  `posted_at` ascending; `posts_fetched` is the total number of posts considered (sum across
  channels before the `MAX_POSTS_PER_DIGEST` cap).
- AC-022: The merged `posts` list is capped at `config.MAX_POSTS_PER_DIGEST`, keeping the most
  recent posts when the cap is exceeded.
- AC-023: If `fetch_posts()` raises `ChannelFetchError` for one channel, that channel is
  skipped (logged as a warning) and the remaining channels are still processed — one bad
  channel must not fail the whole digest.

### Summarizer (app/digest/summarizer.py)

- AC-030: `PROMPT_VERSION = "digest_v1"`. The prompt text is loaded from
  `app/prompts/digest_v1.md` once at import time.
- AC-031: `summarize(posts, llm_client)` is `async`. It builds a single context string — one
  block per post containing channel username, posted date, text, and URL — and calls
  `llm_client.complete(prompt=PROMPT, context=context)`, returning the resulting `LLMResult`.
- AC-032: `summarize(posts, llm_client)` raises `ValueError` if `posts` is empty (callers must
  short-circuit on empty input before calling `summarize`).
- AC-033: If `llm_client.complete()` raises `LLMError`, `summarize()` re-raises it as
  `DigestError` (defined in this module) with a user-readable message.

### Formatter (app/digest/formatter.py)

- AC-040: `format_digest(llm_text, channels, posts_fetched, posts_included)` returns a single
  Markdown string: a header listing the included channels and
  "прочитано {posts_fetched} постов, в дайджест вошло {posts_included}", followed by
  `llm_text` unchanged.
- AC-041: `format_empty_digest(channels)` returns `messages.DIGEST_EMPTY` formatted with the
  channel list — used when no posts survive filtering.
- AC-042: The header produced by `format_digest()` contains no unescaped Markdown special
  characters that would break `parse_mode=ParseMode.MARKDOWN` (channel usernames are wrapped
  in backticks or plain `@username` text without `_`-breaking issues — `@username` characters
  `[A-Za-z0-9_]` are safe inside Markdown V1).

### Repositories (app/storage/repositories.py)

- AC-050: `DigestRunRepo.start(days, channel_filter)` inserts a row into `digest_runs` with
  `status='running'` and returns the new row's `id`.
- AC-051: `DigestRunRepo.finish(run_id, posts_fetched, posts_included, status, error_msg=None)`
  updates the row identified by `run_id`, setting `finished_at = datetime('now')`,
  `posts_fetched`, `posts_included`, `status` (one of `"ok"`, `"empty"`, `"error"`), and
  `error_msg`.
- AC-052: `LLMUsageRepo.record(digest_run_id, result, prompt_version)` inserts a row into
  `llm_usage` with `provider=config.LLM_PROVIDER`, `model=result.model`,
  `prompt_version=prompt_version`, `input_tokens=result.input_tokens`,
  `output_tokens=result.output_tokens`.

### Handler (app/bot/handlers.py)

- AC-060: `/digest` with no arguments replies with `messages.DIGEST_USAGE` and does not start
  a digest run.
- AC-061: `/digest <days>` (or `/digest @channel <days>`) where `days` is not an integer in
  `1..config.MAX_DAYS` replies with `messages.DIGEST_INVALID_DAYS.format(max_days=config.MAX_DAYS)`.
- AC-062: `/digest @channel <days>` where `@channel` is not in `ChannelRepo.list_active()`
  replies with `messages.CHANNEL_NOT_FOUND.format(username=...)`.
- AC-063: On valid input, the handler immediately replies with `messages.DIGEST_STARTED`,
  schedules `run_digest(...)` via `asyncio.create_task()`, and returns without blocking.
- AC-064: `run_digest()` opens a `digest_runs` row via `DigestRunRepo.start()`. If, after
  `collect_posts()` + `filter_posts()`, no posts remain, it sends `format_empty_digest()` to
  the owner and finishes the run with `status="empty"`, `posts_included=0`.
- AC-065: Otherwise, `run_digest()` calls `summarize()`, records usage via
  `LLMUsageRepo.record()`, sends `format_digest()` to the owner, and finishes the run with
  `status="ok"`.
- AC-066: If `collect_posts`, `summarize`, or sending the message raises
  (`ChannelFetchError`, `DigestError`, or any other exception), `run_digest()` logs the
  exception, finishes the run with `status="error"` and `error_msg=str(exc)`, and sends
  `messages.DIGEST_ERROR` to the owner. The bot process must not crash.
- AC-067: `/digest`, like all other commands, respects `owner_guard()` — non-owner messages
  produce no reply.

### Prompt (app/prompts/digest_v1.md)

- AC-070: `app/prompts/digest_v1.md` exists, is non-empty, and instructs the model to: group
  posts into 3–7 thematic clusters, write a 2–4 sentence summary per cluster, include links to
  the original posts, and produce output formatted as Telegram Markdown.

## Out of scope

- Webhook deployment, Dockerfile, README (Feature 005).
- Scheduled/automatic digests.
- Multi-user usage limits.

## Notes

- `CollectedPost` (collector.py) extends `CachedPost` (from Feature 003) with
  `channel_username: str` so the formatter and prompt context can reference the source channel.
- Tests for `ClaudeClient` must mock the Anthropic SDK — no real API calls in the test suite.
- `DigestRunRepo` / `LLMUsageRepo` reuse `app/storage/db.get_connection()`, mirroring
  `ChannelRepo` / `PostsCacheRepo` from Features 002/003.
