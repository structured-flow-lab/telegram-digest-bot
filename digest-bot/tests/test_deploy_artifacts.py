"""Feature 005 — AC-030 – AC-032, AC-040 – AC-041 — Dockerfile, .dockerignore, README."""

import os

DIGEST_BOT_ROOT = os.path.join(os.path.dirname(__file__), "..")


def _read(relative_path):
    path = os.path.join(DIGEST_BOT_ROOT, relative_path)
    assert os.path.isfile(path), f"{relative_path} does not exist"
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_dockerfile_uses_slim_python_and_installs_requirements():
    """AC-030: Dockerfile based on python:3.12-slim, installs requirements.txt early."""
    content = _read("Dockerfile")

    assert "python:3.12-slim" in content
    assert "requirements.txt" in content
    assert "pip install" in content

    # requirements.txt is copied/installed before the rest of the source (layer caching):
    req_index = content.index("requirements.txt")
    install_index = content.index("pip install")
    copy_app_index = content.find("COPY . ")
    if copy_app_index == -1:
        copy_app_index = content.find("COPY app")
    assert req_index < install_index
    if copy_app_index != -1:
        assert install_index < copy_app_index


def test_dockerfile_runs_main():
    """AC-031: default command runs app/main.py."""
    content = _read("Dockerfile")

    assert "app/main.py" in content
    assert "CMD" in content


def test_dockerignore_excludes_runtime_and_secrets():
    """AC-032: .dockerignore excludes data/, .env, __pycache__, *.session, tests/."""
    content = _read(".dockerignore")

    for entry in ["data", ".env", "__pycache__", ".session", "tests"]:
        assert entry in content, f"{entry!r} missing from .dockerignore"


def test_readme_documents_setup_and_deploy():
    """AC-040: README documents env vars, local setup, Telethon login, Railway deploy."""
    content = _read("README.md").lower()

    assert ".env.example" in content or "env" in content
    assert "pip install" in content
    assert "telethon" in content
    assert "railway" in content
    assert "webhook" in content
    assert "data" in content  # persistent volume for data/


def test_readme_includes_mvp_checklist():
    """AC-041: README maps the 9 PRD MVP success criteria to verification steps."""
    content = _read("README.md").lower()

    assert "digest" in content
    assert "/digest" in content
    assert "/add" in content
    assert "/remove" in content
    assert "/channels" in content
    assert "llm_usage" in content or "usage" in content
