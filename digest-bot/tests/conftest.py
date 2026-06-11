"""Shared test setup.

Several modules (app.config and anything importing it, e.g.
app.storage.repositories) raise RuntimeError at import time if required
env vars are missing. Set sane defaults here so collection doesn't fail;
individual tests (e.g. test_config.py) use monkeypatch to override/remove
these as needed.
"""

import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test:token")
os.environ.setdefault("OWNER_TELEGRAM_ID", "999")
