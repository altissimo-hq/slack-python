"""slack-python client."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .blocks import (
    actions_block,
    button_element,
    context_block,
    section_block,
)
from .client import SlackClient, SlackSettings
from .service import SlackClientProtocol, SlackService

try:
    __version__ = version("slack-python")
except PackageNotFoundError:  # pragma: no cover — editable install without metadata
    __version__ = "0.1.0"

__all__ = [
    "SlackClient",
    "SlackClientProtocol",
    "SlackService",
    "SlackSettings",
    "__version__",
    "actions_block",
    "button_element",
    "context_block",
    "section_block",
]
