from importlib import import_module
from typing import Any

__all__ = ["MaxClient", "functions", "models", "exceptions", "parser", "bridge", "sync"]


def __getattr__(name: str) -> Any:
    if name == "MaxClient":
        return import_module("maxbridge_client").MaxClient
    if name in {"functions", "models", "exceptions", "parser", "bridge", "sync"}:
        return import_module(f"maxbridge_client.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
