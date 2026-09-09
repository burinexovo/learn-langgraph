"""Shared LLM getter for all notebooks in this course.

Centralizing this in one place means switching provider/model only
requires editing this file, not every notebook.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool

load_dotenv()


def has_api_key() -> bool:
    """Check whether OPENAI_API_KEY is configured in the environment."""
    return bool(os.environ.get("OPENAI_API_KEY"))


def get_llm(model: str = "gpt-4.1-mini", temperature: float = 0.0) -> BaseChatModel:
    """Return a chat model instance via LangChain's provider-agnostic init_chat_model.

    Args:
        model: Model identifier, e.g. "gpt-4.1-mini" (resolved against provider "openai").
        temperature: Sampling temperature.

    Returns:
        A configured BaseChatModel instance.
    """
    return init_chat_model(model, model_provider="openai", temperature=temperature)


class FakeToolChatModel(GenericFakeChatModel):
    """A scriptable fake chat model that also accepts `.bind_tools()`.

    `GenericFakeChatModel` does not implement `bind_tools`, so it can't be
    dropped into `create_agent` / `ToolNode` pipelines out of the box. This
    subclass makes `bind_tools` a no-op (the tool schema isn't validated;
    the scripted responses already decide which tool_calls to emit), which
    is enough to run every LangGraph agent pattern in this course fully
    offline, with real (not skipped) executed output.
    """

    def bind_tools(self, tools: Iterable[BaseTool], **kwargs: Any) -> "FakeToolChatModel":
        return self


def scripted_model(responses: list[AIMessage | str]) -> FakeToolChatModel:
    """Build a `FakeToolChatModel` that replays `responses` in order, one per call.

    Args:
        responses: A sequence of `AIMessage` (use this when a step should emit
            tool_calls) or plain strings (plain text replies).

    Returns:
        A chat-model-compatible object usable anywhere a real model is expected.
    """
    return FakeToolChatModel(messages=iter(responses))
