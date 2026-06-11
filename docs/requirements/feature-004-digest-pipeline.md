# Feature 004 — Digest pipeline (LLM summarisation)

## Goal

`/digest <days>` and `/digest @channel <days>` return a thematic digest (3–7
clusters, 2–4 sentence summaries, links to original posts) built from cached +
freshly fetched posts, using Claude via an abstract `LLMClient`.

## User story

As the bot owner, I run `/digest 7` and get a message grouping the last 7 days
of posts across all my channels into a handful of themes, each with a short
summary and links back to the source posts. `/digest @channel 7` does the same
for a single channel.

## Scope

- `app/llm/base.py` — `LLMResult`, `LLMClient` Protocol.
- `app/llm/claude.py` — `ClaudeClient` (Anthropic SDK).
- `app/llm/factory.py` — `get_llm_client()` keyed on `config.LLM_PROVIDER`.
- `app/prompts/digest_v1.md` — prompt template for clustering + summarising.
- `app/digest/collector.py` — gather posts (cache + fresh fetch) for the
  requested scope/period.
- `app/digest/filter.py` — drop posts without usable text / too short /
  duplicates.
- `app/digest/summarizer.py` — call `LLMClient`, parse response into clusters,
  record usage.
- `app/digest/formatter.py` — render clusters into a Telegram message
  (Markdown, links, header).
- `app/storage/repositories.py` — `DigestRunRepo`, `LLMUsageRepo`.
- `app/bot/handlers.py` — `/digest [<@channel>] <days>` handler.

## Acceptance criteria

### LLM abstraction (app/llm/)

- AC-001: `LLMResult` dataclass: `text: str`, `input_tokens: int`,
  `output_tokens: int`, `model: str`.
- AC-002: `LLMClient` Protocol defines
  `async def complete(self, prompt: str, context: str) -> LLMResult`.
- AC-003: `ClaudeClient(model: str)` implements `LLMClient` via the
  `anthropic` SDK's async client; `context` is sent as the user message,
  `prompt` as the system prompt.
- AC-004: `ClaudeClient.complete()` raises `LLMError` (new exception in
  `app/llm/base.py`) wrapping any `anthropic` SDK exception (auth, rate limit,
  timeout, etc.) — callers don't depend on `anthropic`-specific exception types.
- AC-005: `get_llm_client()` returns `ClaudeClient(model=config.LLM_MODEL)`
  when `config.LLM_PROVIDER == "claude"`; raises `ValueError` for unknown
  providers (no other providers implemented yet).

### Prompt (app/prompts/digest_v1.md)

- AC-010: File exists, versioned as `digest_v1.md`. Instructs the model to
  group posts into 3–7 thematic clusters, each with a 2–4 sentence summary,
  and to reference posts by an index/id so the formatter can attach links.
- AC-011: Prompt requests a structured (JSON) response so
  `summarizer.py` can parse it deterministically.

### Collector (app/digest/collector.py)

- AC-020: `async def collect_posts(channel_ids: list[int], since: datetime) -> list[CachedPost]`
  — for each channel: read `PostsCacheRepo.get_cached_since()`, then call
  `fetch_posts()` for anything newer than `latest_cached_at()`, upsert new
  posts into the cache, and return the merged, deduplicated, time-ordered list.
- AC-021: Total returned posts capped at `config.MAX_POSTS_PER_DIGEST`
  (oldest dropped first if over the cap, after sorting newest-relevant).
- AC-022: A `ChannelFetchError` from one channel does not abort the whole
  collection — that channel is skipped, the error is logged, and collection
  continues for the remaining channels. The skipped channel is reported back
  to the caller (for inclusion in the digest header / error summary).

### Filter (app/digest/filter.py)

- AC-030: `def filter_posts(posts: list[CachedPost]) -> list[CachedPost]`
  drops posts where `text` is empty/`None` or shorter than a configurable
  minimum (`MIN_POST_LENGTH = 40` chars, defined in `app/digest/filter.py`).
- AC-031: Drops exact-duplicate `text` (keep the first occurrence,
  oldest-to-newest).

### Summarizer (app/digest/summarizer.py)

- AC-040: `async def summarize(posts: list[CachedPost], llm: LLMClient) -> DigestResult`
  builds the context from `posts` (id, channel, date, text, url), calls
  `llm.complete(prompt, context)` using `digest_v1.md`, and parses the JSON
  response into `DigestResult` (`clusters: list[DigestCluster]`, plus the raw
  `LLMResult` for usage recording).
- AC-041: `DigestCluster`: `title: str`, `summary: str`,
  `post_urls: list[str]`.
- AC-042: If the LLM response is not valid JSON or doesn't match the expected
  shape, raise `SummarizerError` — caller surfaces a user-friendly error
  message (do not crash the bot).
- AC-043: If `posts` is empty, `summarize()` returns a `DigestResult` with an
  empty `clusters` list without calling the LLM (no wasted API call).

### Formatter (app/digest/formatter.py)

- AC-050: `def format_digest(result: DigestResult, header: DigestHeader) -> list[str]`
  returns one or more HTML-formatted messages (matches `ParseMode.HTML` used
  elsewhere in `app/bot/handlers.py`): header (channels included, posts
  fetched, posts included) followed by each cluster as `<b>Title</b>\nsummary\n`
  + linked post references (`<a href="...">N</a>`).
- AC-051: If `result.clusters` is empty, returns a single "nothing to
  summarise" message (header + notice, no clusters block).
- AC-052: Each returned message respects Telegram's 4096-character limit —
  clusters that would overflow the current message start a new one (handler
  sends each list item as a separate `reply_text`).

### Repositories (app/storage/repositories.py)

- AC-060: `DigestRunRepo.create(days, channel_filter) -> int` inserts a row
  with `status='running'`, returns `id`.
- AC-061: `DigestRunRepo.complete(run_id, posts_fetched, posts_included)` sets
  `status='ok'`, `finished_at=now`, and the post counts.
- AC-062: `DigestRunRepo.fail(run_id, error_msg)` sets `status='error'`,
  `finished_at=now`, `error_msg`.
- AC-063: `LLMUsageRepo.record(digest_run_id, provider, model, prompt_version, input_tokens, output_tokens)`
  inserts one row into `llm_usage`.

### Handler (app/bot/handlers.py)

- AC-070: `/digest <days>` — validates `days` is an integer in
  `1..config.MAX_DAYS`; on invalid input, replies with a usage message and
  does not start a run.
- AC-071: `/digest @channel <days>` — same validation, plus the channel must
  be in `ChannelRepo` (owner's saved list); unknown channel → error message.
- AC-072: On valid input, immediately reply "⏳ Формирую дайджест..." and run
  the pipeline in `asyncio.create_task()` (handler returns immediately).
- AC-073: On success, send the formatted digest message(s) and call
  `DigestRunRepo.complete()` + `LLMUsageRepo.record()`.
- AC-074: On any pipeline exception, call `DigestRunRepo.fail()` and reply
  with a generic "что-то пошло не так" message — never crash/leak stack
  traces to the user.
- AC-075: If `collect_posts()` returns zero posts after filtering, reply with
  the "nothing to summarise" message from `formatter.py` and still record the
  run as `ok` with `posts_included=0`.

## Out of scope

- Multiple LLM providers (OpenAI/Gemini) — factory structure supports adding
  them later, not implemented now.
- Scheduled/automatic digests.
- Editing/regenerating a digest in place.
- Comment/discussion-group summaries.

## Notes

- All LLM calls in tests are mocked (`LLMClient` Protocol makes this trivial)
  — no real Anthropic API calls in the test suite.
- `digest_v1.md` is loaded from disk at call time (not embedded as a string)
  so prompt iteration doesn't require code changes; tests can point at a
  fixture prompt file.
