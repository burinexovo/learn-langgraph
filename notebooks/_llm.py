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
    """Check whether a live model backend (OpenAI, or Azure AI Foundry) is configured."""
    if os.environ.get("OPENAI_API_KEY"):
        return True
    return bool(os.environ.get("AZURE_AI_ENDPOINT") and os.environ.get("AZURE_AI_API_KEY"))


def get_llm(
    model: str = "gpt-4.1-mini", temperature: float = 0.0, provider: str = "openai"
) -> BaseChatModel:
    """Return a chat model instance, preferring OpenAI and falling back to Azure AI Foundry.

    Args:
        model: Model identifier, e.g. "gpt-4.1-mini" (resolved against provider "openai").
            Ignored when routing through Azure AI Foundry, which uses `OPENAI_MODEL` /
            `ANTHROPIC_MODEL` (the deployment name) instead.
        temperature: Sampling temperature.
        provider: "openai" (default) or "anthropic". Only used to pick which Azure AI
            Foundry deployment to call when there's no `OPENAI_API_KEY`; a plain OpenAI
            key always wins regardless of this value.

    Returns:
        A configured BaseChatModel instance.
    """
    if os.environ.get("OPENAI_API_KEY"):
        return init_chat_model(model, model_provider="openai", temperature=temperature)

    azure_endpoint = os.environ.get("AZURE_AI_ENDPOINT")
    azure_api_key = os.environ.get("AZURE_AI_API_KEY")
    if azure_endpoint and azure_api_key:
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            # claude-opus-5's adaptive thinking rejects a custom `temperature`.
            return ChatAnthropic(
                base_url=azure_endpoint.removesuffix("/openai/v1") + "/anthropic",
                api_key=azure_api_key,
                model=os.environ["ANTHROPIC_MODEL"],
            )

        from langchain_azure_ai.chat_models import AzureAIOpenAIApiChatModel

        return AzureAIOpenAIApiChatModel(
            endpoint=azure_endpoint,
            credential=azure_api_key,
            model=os.environ["OPENAI_MODEL"],
            temperature=temperature,
        )

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
