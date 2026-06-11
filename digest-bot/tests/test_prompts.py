"""Feature 004 — AC-070 — app/prompts/digest_v1.md."""

import os

PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app", "prompts", "digest_v1.md"
)


def test_digest_v1_prompt_exists_and_is_non_empty():
    """AC-070: prompt file exists and is non-empty."""
    assert os.path.isfile(PROMPT_PATH)
    with open(PROMPT_PATH, encoding="utf-8") as f:
        content = f.read()
    assert content.strip() != ""


def test_digest_v1_prompt_describes_grouping_and_links():
    """AC-070: prompt instructs grouping into 3-7 themes, summaries, and links."""
    with open(PROMPT_PATH, encoding="utf-8") as f:
        content = f.read().lower()

    assert "3" in content and "7" in content
    # Mentions links to original posts (RU or EN wording).
    assert "ссыл" in content or "link" in content
