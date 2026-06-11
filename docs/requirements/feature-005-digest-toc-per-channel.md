# Feature 005 — Per-channel "table of contents" digest format

## Background

Feature 004 ([feature-004-digest-pipeline.md](feature-004-digest-pipeline.md), PR #9) shipped a
working `/digest` pipeline, but the output doesn't match the original idea: it produces 3–7
thematic *summaries* (2–4 sentences each) in **one combined message** for all channels.

What the owner actually wants:

- Not a summary of what was said — a **table of contents**: short topic headings she can scan in
  a few seconds, each linking straight to the source post.
- One message **per channel**, so `/digest 7` over a 3-channel selection produces 3 separate
  messages, each scoped to one channel.

This feature revises the prompt, summarizer output shape, formatter, and handler from feature 004
to match. It does not change the collector, filter, repositories, or LLM abstraction layer.

## Goal

`/digest <days>` sends one message per channel in the owner's selection (in saved-channel order).
`/digest @channel <days>` sends one message for that channel. Each message is a scannable list of
topic headings covered by that channel in the period — each heading links to its source post, with
an optional one-sentence note underneath.

## User story

As the bot owner, I haven't opened a channel in a month. I run `/digest @channel 30` and get one
message: a list of headings like a book's table of contents ("New API release", "Team moved
office", "Q&A thread on pricing"), each a tap-through link to the original post, with at most one
short sentence under each saying what it's about. I tap the ones I care about and ignore the rest.

When I run `/digest 7` across my 3 saved channels, I get 3 such messages, one per channel, each
headed with the channel name.

## Scope

- `app/prompts/digest_v2.md` — new prompt version: TOC items instead of thematic summaries.
  `digest_v1.md` stays on disk (unused) for history/reference.
- `app/digest/summarizer.py` — `DigestCluster` → `DigestItem` (title, note, post_urls); `summarize()`
  takes a `prompt_version` (defaults to `"digest_v2"`) and parses the new JSON shape.
- `app/digest/formatter.py` — render one message per channel: channel header + TOC items
  (`<a href="url"><b>Title</b></a>` + optional note line).
- `app/bot/handlers.py` — `/digest` handler iterates channels one at a time: collect → filter →
  summarize → format → send, per channel.
- `app/storage/repositories.py` — `LLMUsageRepo.record()` called once per channel (per LLM call),
  all rows linked to the same `digest_run_id`.

Not changed: `app/digest/collector.py`, `app/digest/filter.py`, `app/llm/*`,
`DigestRunRepo` (still one row per `/digest` invocation).

## Acceptance criteria

### Prompt (app/prompts/digest_v2.md)

- AC-100: New file `digest_v2.md`. Instructs the model to act like it's writing a table of
  contents: scan the numbered posts and produce one entry per distinct topic/event, **not** a
  prose summary.
- AC-101: Each entry has:
  - `title`: a short heading (a few words), in the same language as the posts.
  - `note`: **at most one short sentence** clarifying what the topic is about. May be `""` if the
    title is self-explanatory.
  - `post_indices`: list of 1+ indices of the posts this entry covers (usually 1; group only when
    multiple posts clearly cover the exact same topic/event).
- AC-102: No fixed cluster count (3–7) — one entry per distinct topic, in chronological order
  (oldest first), covering as much of the input as is reasonably distinct. Posts that are pure
  noise (ads, "see you tomorrow"-type filler) may be omitted.
- AC-103: Response is **only** JSON, no surrounding text/fences, in this shape:

  ```json
  {
    "items": [
      {
        "title": "Short heading",
        "note": "One short sentence, or empty string.",
        "post_indices": [3]
      }
    ]
  }
  ```

### Summarizer (app/digest/summarizer.py)

- AC-110: `DigestCluster` renamed to `DigestItem`: `title: str`, `note: str`,
  `post_urls: list[str]`.
- AC-111: `summarize(posts, llm, prompt_version="digest_v2")` loads
  `app/prompts/{prompt_version}.md`, calls the LLM, and parses the `items` shape from AC-103 into
  `DigestResult(items: list[DigestItem], llm_result, prompt_version)`.
- AC-112: Same error handling as feature 004 (AC-042, AC-043): malformed JSON/shape →
  `SummarizerError`; empty `posts` → `DigestResult(items=[], llm_result=None, prompt_version=...)`
  without an LLM call.
- AC-113: `prompt_version` is threaded through to `LLMUsageRepo.record()` (replaces the hardcoded
  `PROMPT_VERSION` constant).

### Formatter (app/digest/formatter.py)

- AC-120: `format_channel_digest(channel: str, result: DigestResult, meta: ChannelDigestMeta) -> list[str]`
  replaces `format_digest`/`DigestHeader`. `ChannelDigestMeta` carries `days: int`,
  `posts_fetched: int`, `posts_included: int`, and `error: str | None` (set when the channel
  failed to fetch — see AC-141).
- AC-121: Header line: `📑 <b>@channel</b> — дайджест за {days} дн. ({posts_included} из
  {posts_fetched} постов)`.
- AC-122: Each `DigestItem` renders as:
  - If `len(post_urls) == 1`: `<a href="{post_urls[0]}"><b>{title}</b></a>`
  - If `len(post_urls) > 1`: `<a href="{post_urls[0]}"><b>{title}</b></a>` followed by extra
    numbered links for the remaining URLs, e.g. `(<a href="{post_urls[1]}">2</a>,
    <a href="{post_urls[2]}">3</a>)`.
  - Followed by `\n{note}` on the next line **only if `note` is non-empty**.
- AC-123: Items are separated by a blank line. If `result.items` is empty, return a single
  message: header + `NOTHING_TO_SUMMARIZE` notice (reuse feature-004 wording).
- AC-124: If `meta.error` is set (channel fetch failed entirely), return a single message:
  header line + `⚠️ Не удалось прочитать канал: {error}` — no items, no LLM call (handler skips
  summarization for that channel; see AC-142).
- AC-125: Telegram 4096-char limit still respected (AC-052 from feature 004): overflow starts a
  new message, each returned as a separate `reply_text`.
- HTML-escaping (AC from PR #9 fix) still applies to `title` and `note`.

### Handler (app/bot/handlers.py)

- AC-130: `/digest <days>` resolves the owner's saved channel list (`ChannelRepo`); validation of
  `days` unchanged from feature 004 (AC-070/071).
- AC-131: One `DigestRunRepo` row per `/digest` invocation (unchanged from AC-060/061/062), but
  `posts_fetched`/`posts_included` recorded on `complete()` are the **sums across all
  channels** in this run.
- AC-132: For each channel, sequentially: `collect_posts([channel_id], since)` → `filter_posts()`
  → `summarize()` (skipped if collection failed or zero posts after filtering) → format → send via
  `reply_text` (one call per message returned by the formatter).
- AC-133: Channels are processed sequentially (not concurrently) to avoid bursting the LLM API and
  to keep message order matching the saved-channel order.
- AC-134: `LLMUsageRepo.record()` is called once per channel that reached `summarize()` (i.e. had
  ≥1 post after filtering), each row tagged with the same `digest_run_id`.
- AC-140: `/digest @channel <days>` — same per-channel flow, scoped to the one channel; sends 1+
  messages (no behavior change vs. feature 004 beyond the new format).
- AC-141: A `ChannelFetchError` for one channel (AC-022 from feature 004) does not abort the run:
  that channel's message is the AC-124 error message, and processing continues with the next
  channel.
- AC-142: If `collect_posts` + `filter_posts` for a channel yield zero posts (no error, just
  nothing in range), send the AC-123 "nothing to summarise" message for that channel — no LLM
  call, no `LLMUsageRepo` row for that channel.
- AC-143: On an unexpected exception during the whole run, behavior matches feature 004 AC-074
  (`DigestRunRepo.fail()` + generic error reply) — but any channel messages already sent before the
  exception remain (partial digest is better than none).
- AC-144: If the owner has zero saved channels, reply with the existing "no channels" message
  (`messages.py`) and do not start a run — same as current behavior for an empty selection.

## Out of scope

- Changing how posts are clustered/grouped beyond "one topic = one TOC entry" (AC-101/102).
- Concurrency/parallelism across channels (AC-133 explicitly sequential for now).
- Changing `digest_v1.md`, `app/digest/collector.py`, `app/digest/filter.py`, `app/llm/*`,
  `DigestRunRepo` schema.
- Per-channel digest run rows (still one `digest_run` row per `/digest` invocation, AC-131).

## Migration notes (vs. feature 004)

| Feature 004 | Feature 005 |
|---|---|
| `DigestCluster(title, summary, post_urls)` | `DigestItem(title, note, post_urls)` — `note` is ≤1 sentence, may be empty |
| `format_digest(result, header) -> list[str]`, one combined message for all channels | `format_channel_digest(channel, result, meta) -> list[str]`, called once per channel |
| `digest_v1.md`, `PROMPT_VERSION = "digest_v1"` constant | `digest_v2.md`, `prompt_version` parameter, default `"digest_v2"` |
| One `LLMUsageRepo` row per `/digest` run | One `LLMUsageRepo` row per channel per run |

Existing tests in `tests/test_digest_formatter.py`, `tests/test_digest_summarizer.py`,
`tests/test_digest_handler.py` need rewriting for the new shapes — per the working agreement this
starts with updated/failing specs before touching implementation.
