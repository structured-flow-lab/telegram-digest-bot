"""AC-030, AC-031 — messages constants."""

from app.bot import messages


def test_start_is_non_empty():
    """AC-030."""
    assert isinstance(messages.START, str)
    assert len(messages.START) > 0


def test_help_contains_help_command():
    """AC-031."""
    assert isinstance(messages.HELP, str)
    assert "/help" in messages.HELP
