"""One place to choose the model, as in the original `get_llm()`.

Set SECURITY_MODEL to any "provider:model" string `init_chat_model` accepts.
The default is the same local Ollama model the parallel pattern uses, so a
test run costs nothing.
"""

import os

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

DEFAULT_MODEL = "ollama:qwen3-coder-next:latest"


def get_llm() -> BaseChatModel:
    # temperature=0 for reproducible verdicts, critical for security tooling.
    return init_chat_model(os.getenv("SECURITY_MODEL", DEFAULT_MODEL), temperature=0)
