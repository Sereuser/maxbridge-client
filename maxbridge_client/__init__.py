from .client import MaxClient
# NOTE: importing `functions` here can create an import cycle when the
# `functions/*` modules import `MaxClient`.
# Users can still import it via `from maxbridge_client import functions`.
from . import models
from . import exceptions

__all__ = ['MaxClient', 'functions', 'models', 'exceptions']


def __getattr__(name: str):
    if name == "functions":
        from . import functions as _functions
        return _functions
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
