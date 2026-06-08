"""Slack API client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SlackSettings:
    """Slack client settings."""

    bot_token: str

    @classmethod
    def from_env(cls) -> SlackSettings:
        """Build settings from environment.

        Looks for SLACK_ORG_BOT_TOKEN first, falling back to SLACK_BOT_TOKEN.
        """
        token = os.environ.get("SLACK_ORG_BOT_TOKEN") or os.environ.get("SLACK_BOT_TOKEN", "")
        if not token:
            raise ValueError("Neither SLACK_ORG_BOT_TOKEN nor SLACK_BOT_TOKEN is set")
        return cls(bot_token=token)


class SlackClient:
    """Thin wrapper around Slack WebClient."""

    def __init__(self, settings: SlackSettings, client: Any = None) -> None:
        """Initialize the Slack client."""
        self._settings = settings
        self._client = client

    @classmethod
    def from_env(cls) -> SlackClient:
        """Create client from environment settings."""
        return cls(SlackSettings.from_env())

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from slack_sdk import WebClient
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "Slack dependency not installed. Install with `poetry install -E slack` or `pip install slack-sdk`."
                ) from exc
            self._client = WebClient(token=self._settings.bot_token)
        return self._client

    def post_chat_message(
        self,
        *,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Post a chat message to Slack."""
        payload: dict[str, Any] = {
            "channel": channel,
            "text": text,
        }
        if blocks is not None:
            payload["blocks"] = blocks
        return self._get_client().chat_postMessage(**payload)
