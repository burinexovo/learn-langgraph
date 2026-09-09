"""Shared LangSmith helper for 11_langsmith_observability.ipynb.

Import this before importing anything from `langchain` / `langgraph` in the
same kernel. `langsmith.utils.get_env_var` is `lru_cache`-d, so the *first*
check of the tracing env vars anywhere in the process is cached for the
process's lifetime -- setting `os.environ[...]` later has no effect. Loading
`.env` here, at the top of the notebook's first cell, avoids that trap.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def has_langsmith_key() -> bool:
    """Check whether a LangSmith API key is configured (current or legacy env var name)."""
    return bool(os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY"))
