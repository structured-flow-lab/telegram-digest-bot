"""Filter posts before sending them to the LLM."""

from app.storage.repositories import CachedPost

MIN_POST_LENGTH = 40


def filter_posts(posts: list[CachedPost]) -> list[CachedPost]:
    """Drop posts without usable text and exact-duplicate texts.

    Posts are assumed oldest-to-newest; the first occurrence of a duplicate
    text is kept.
    """
    seen_texts: set[str] = set()
    result: list[CachedPost] = []

    for post in posts:
        text = post.text
        if not text or len(text) < MIN_POST_LENGTH:
            continue
        if text in seen_texts:
            continue
        seen_texts.add(text)
        result.append(post)

    return result
