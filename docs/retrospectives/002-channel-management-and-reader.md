# Retrospective 002 — Channel Management & Telethon Reader (Phase 1 & 2)

## What we did
Wrote requirement docs for Phase 1 (channel management) and Phase 2 (Telethon reader + posts
cache), added failing specs covering all acceptance criteria, then implemented:
- `app/reader/telethon_client.py` — lazy singleton Telethon client + `ensure_connected`.
- `app/reader/posts.py` — `validate_channel` / `fetch_posts`.
- `app/storage/repositories.py` — `ChannelRepo` and `PostsCacheRepo`.
- `app/bot/handlers.py` + `app/bot/messages.py` + `app/main.py` — `/add /remove /channels` handlers.

All 55 tests pass (13 Phase 0 + 42 new). Closed issues #1, #2, #3 and merged PR#7 (squash) into
`master`.

## What worked
- Spec-first docs (`docs/requirements/feature-002-*.md`, `feature-003-*.md`) gave the test suite
  a clear AC-numbered structure that made cross-referencing tests ↔ requirements ↔ review
  comments easy.
- A code review pass (4 parallel reviewer agents) caught a real bug before merge: `fetch_posts`
  used `iter_messages(offset_date=since)` without `reverse=True`, which would have fetched posts
  *older* than `since` instead of newer against the real Telegram API. Fixed by adding
  `reverse=True` plus a defensive `msg.date >= since` filter.

## What didn't / friction points
- **Spec → failing test → minimal code → green test → commit, one concern per commit** (working
  agreement #4) was not followed at PR granularity: PR#7 bundled the red-test commits *and* three
  feat commits with full implementation in a single PR, and the original PR description claimed
  "no implementation code — all new tests fail," which was factually wrong by the time of review.
  This was caught during code review and the description was corrected before merge, but it cost
  an extra review round.
- The `offset_date`/`reverse` bug was masked by mocks: tests replaced `iter_messages` with a fake
  generator that ignored `offset_date` entirely, so the test suite stayed green even with the
  wrong Telethon call. The bug was only found via manual code review against Telethon's documented
  semantics, not by the test suite.
- A test-isolation bug surfaced and was fixed along the way: popping a module from
  `sys.modules` without clearing the parent package's cached attribute let `from package import
  submodule` and `unittest.mock.patch("pkg.mod...")` resolve to two different module objects
  across tests.

## Decisions to carry forward
- No new ADRs required — Telethon usage already covered by
  [docs/decisions/004-telethon-channel-reader.md](../decisions/004-telethon-channel-reader.md).

## Changes made to CLAUDE.md / constraints / working agreement
- None yet. Proposal for next session: when a PR bundles spec+test+implementation (as happened
  here), the PR description must say so explicitly up front rather than describing it as
  "tests only" — avoids misleading reviewers. Consider adding this as an explicit note under
  working agreement #4 if it recurs.

## Open questions for next session
- Mocking `iter_messages` with a fake generator that ignores its kwargs hides bugs in how those
  kwargs are used (as happened with `offset_date`/`reverse`). Worth considering an assertion on
  call args (`offset_date=since, reverse=True`) in `test_posts_reader.py` to lock in the fix.
- Phase 3 (digest generation) is next per `docs/decisions/002-llm-abstraction.md` — needs its own
  requirements doc before implementation starts.
