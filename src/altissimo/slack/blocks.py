"""Block Kit builder helpers."""

from __future__ import annotations

from typing import Any


def section_block(text: str) -> dict[str, Any]:
    """Create a section block with markdown text."""
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text,
        },
    }


def context_block(text: str) -> dict[str, Any]:
    """Create a context block with markdown text."""
    return {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": text,
            }
        ],
    }


def actions_block(elements: list[dict[str, Any]]) -> dict[str, Any]:
    """Create an actions block containing interactive elements (e.g. buttons)."""
    return {
        "type": "actions",
        "elements": elements,
    }


def button_element(text: str, action_id: str, value: str | None = None) -> dict[str, Any]:
    """Create a button element for an actions block."""
    element: dict[str, Any] = {
        "type": "button",
        "text": {
            "type": "plain_text",
            "text": text,
            "emoji": True,
        },
        "action_id": action_id,
    }
    if value is not None:
        element["value"] = value
    return element
