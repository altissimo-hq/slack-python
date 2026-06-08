"""Slack service module."""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol

from .client import SlackClient

logger = logging.getLogger(__name__)


class SlackClientProtocol(Protocol):
    """Protocol for Slack client dependency injection."""

    def post_chat_message(
        self,
        *,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Post chat message to channel."""
        ...


class SlackService:
    """Service layer for Slack notifications with environment-aware routing."""

    def __init__(
        self,
        client: SlackClientProtocol | None = None,
        channels: dict[tuple[str, str], str] | None = None,
        default_env: str = "dev",
        default_text: str = "New notification",
    ) -> None:
        """Initialize the Slack service."""
        self._client = client
        self._channels = channels or {}
        self._default_env = default_env
        self._default_text = default_text

    def _get_client(self) -> SlackClientProtocol:
        if self._client is None:
            self._client = SlackClient.from_env()
        return self._client

    def _env(self) -> str:
        return os.environ.get("ENV", self._default_env)

    def resolve_channel(self, key: str) -> str:
        """Return the channel ID for (key, env) from the registry.

        Falls back to #{key} (in prod) or #{key}-{env} (otherwise).
        """
        env = self._env()
        return self._channels.get((key, env), f"#{key}" if env == "prod" else f"#{key}-{env}")

    @staticmethod
    def parse_error(exc: Exception) -> tuple[str, int | None]:
        """Extract the Slack error string and HTTP status code from an exception."""
        response = getattr(exc, "response", None)
        if response is None:
            return str(exc), None

        error: str | None = None
        try:
            getter = getattr(response, "get", None)
            if callable(getter):
                value = getter("error")
                if value is not None:
                    error = str(value)
        except Exception:
            error = None

        status_code = getattr(response, "status_code", None)
        return error or str(exc), status_code

    def post_message(
        self,
        *,
        channel_key: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Resolve the channel and post a chat message safely."""
        channel = self.resolve_channel(channel_key)
        return self.post_message_raw(
            channel=channel,
            text=text,
            blocks=blocks,
        )

    def post_message_raw(
        self,
        *,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Post a chat message directly to a raw channel string (ID or name) safely."""
        if blocks and not text:
            for block in blocks:
                if block.get("type") == "section" and isinstance(block.get("text"), dict):
                    extracted_text = block["text"].get("text", "")
                    if extracted_text:
                        text = str(extracted_text)
                        break
            if not text:
                text = self._default_text

        try:
            self._get_client().post_chat_message(
                channel=channel,
                text=text,
                blocks=blocks,
            )
            return {"status": "ok"}
        except (RuntimeError, ValueError) as exc:
            logger.warning(str(exc))
            return {"status": "failed", "error": str(exc)}
        except Exception as exc:
            error, status_code = self.parse_error(exc)
            logger.error(f"Failed to send Slack Message: {error} {status_code}")
            result: dict[str, Any] = {"status": "failed", "error": error}
            if status_code is not None:
                result["status_code"] = status_code
            return result
