"""Unit tests for Slack client, service, and Block Kit helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from altissimo.slack import (
    SlackClient,
    SlackClientProtocol,
    SlackService,
    SlackSettings,
    actions_block,
    button_element,
    context_block,
    section_block,
)


def test_slack_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test environment variable loading and validation in SlackSettings."""
    monkeypatch.delenv("SLACK_ORG_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)

    with pytest.raises(ValueError, match="Neither SLACK_ORG_BOT_TOKEN nor SLACK_BOT_TOKEN is set"):
        SlackSettings.from_env()

    # Test fallback to SLACK_BOT_TOKEN
    monkeypatch.setenv("SLACK_BOT_TOKEN", "fallback-token")
    settings = SlackSettings.from_env()
    assert settings.bot_token == "fallback-token"

    # Test preference for SLACK_ORG_BOT_TOKEN
    monkeypatch.setenv("SLACK_ORG_BOT_TOKEN", "org-token")
    settings = SlackSettings.from_env()
    assert settings.bot_token == "org-token"


def test_slack_client_lazy_loading() -> None:
    """Test SlackClient lazy loading RuntimeError when dependency is missing."""
    client = SlackClient(SlackSettings(bot_token="test-token"))

    with (
        patch("builtins.__import__", side_effect=ModuleNotFoundError("No module named 'slack_sdk'")),
        pytest.raises(RuntimeError, match="Slack dependency not installed"),
    ):
        client._get_client()


def test_slack_client_post_chat_message() -> None:
    """Test SlackClient post_chat_message delegation to slack_sdk.WebClient."""
    mock_web_client = MagicMock()
    mock_web_client.chat_postMessage.return_value = {"ok": True}

    client = SlackClient(SlackSettings(bot_token="test-token"), client=mock_web_client)
    res = client.post_chat_message(
        channel="C12345",
        text="Hello",
        blocks=[{"type": "section", "text": {"type": "plain_text", "text": "hello"}}],
    )

    assert res == {"ok": True}
    mock_web_client.chat_postMessage.assert_called_once_with(
        channel="C12345",
        text="Hello",
        blocks=[{"type": "section", "text": {"type": "plain_text", "text": "hello"}}],
    )


def test_slack_service_channel_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test SlackService resolve_channel behavior with registry lookup and fallbacks."""
    channels = {
        ("alerts", "dev"): "C_ALERTS_DEV",
        ("alerts", "prod"): "C_ALERTS_PROD",
    }

    # 1. Dev environment
    monkeypatch.setenv("ENV", "dev")
    service = SlackService(channels=channels)
    assert service.resolve_channel("alerts") == "C_ALERTS_DEV"
    # Fallback to #missing-dev in dev environment
    assert service.resolve_channel("missing") == "#missing-dev"

    # 2. Prod environment
    monkeypatch.setenv("ENV", "prod")
    service = SlackService(channels=channels)
    assert service.resolve_channel("alerts") == "C_ALERTS_PROD"
    # Fallback to #missing in prod environment
    assert service.resolve_channel("missing") == "#missing"


def test_slack_service_parse_error() -> None:
    """Test exception parsing for Slack responses."""
    # Test simple exception
    exc = Exception("plain error")
    err, code = SlackService.parse_error(exc)
    assert err == "plain error"
    assert code is None

    # Test Slack response exception mock
    mock_response = MagicMock()
    mock_response.get.return_value = "channel_not_found"
    mock_response.status_code = 404

    class SlackApiError(Exception):
        def __init__(self) -> None:
            self.response = mock_response

    exc_api = SlackApiError()
    err, code = SlackService.parse_error(exc_api)
    assert err == "channel_not_found"
    assert code == 404


def test_slack_service_posting() -> None:
    """Test posting messages with SlackService."""
    mock_client = MagicMock(spec=SlackClientProtocol)
    service = SlackService(client=mock_client, channels={("notify", "dev"): "C123"}, default_env="dev")

    # 1. Success case
    mock_client.post_chat_message.return_value = {"ok": True}
    res = service.post_message(channel_key="notify", text="testing")
    assert res == {"status": "ok"}
    mock_client.post_chat_message.assert_called_once_with(
        channel="C123",
        text="testing",
        blocks=None,
    )

    # 2. RuntimeError/ValueError logging case
    mock_client.post_chat_message.side_effect = RuntimeError("SDK error")
    res_err = service.post_message(channel_key="notify", text="testing")
    assert res_err == {"status": "failed", "error": "SDK error"}

    # 3. Exception parsing case
    mock_response = MagicMock()
    mock_response.get.return_value = "invalid_auth"
    mock_response.status_code = 401

    class SlackApiError(Exception):
        def __init__(self) -> None:
            self.response = mock_response

    mock_client.post_chat_message.side_effect = SlackApiError()
    res_api_err = service.post_message(channel_key="notify", text="testing")
    assert res_api_err == {"status": "failed", "error": "invalid_auth", "status_code": 401}


def test_block_kit_helpers() -> None:
    """Test Block Kit builder helper dictionary generation."""
    assert section_block("Test text") == {
        "type": "section",
        "text": {"type": "mrkdwn", "text": "Test text"},
    }

    assert context_block("Context text") == {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "Context text"}],
    }

    btn = button_element("Click me", "btn_action", "btn_val")
    assert btn == {
        "type": "button",
        "text": {"type": "plain_text", "text": "Click me", "emoji": True},
        "action_id": "btn_action",
        "value": "btn_val",
    }

    assert actions_block([btn]) == {
        "type": "actions",
        "elements": [btn],
    }


def test_slack_service_text_fallback_extraction() -> None:
    """Test that SlackService extracts text from blocks when text is empty."""
    mock_client = MagicMock(spec=SlackClientProtocol)
    service = SlackService(client=mock_client, default_text="Fallback default")

    blocks: list[dict[str, Any]] = [
        {"type": "context", "elements": [{"type": "mrkdwn", "text": "Ignore context"}]},
        {"type": "section", "text": {"type": "mrkdwn", "text": "Extracted section text"}},
    ]

    # 1. Extracted from section block
    service.post_message_raw(channel="C123", text="", blocks=blocks)
    mock_client.post_chat_message.assert_called_with(
        channel="C123",
        text="Extracted section text",
        blocks=blocks,
    )

    # 2. Falls back to default_text when no section block has text
    blocks_no_text: list[dict[str, Any]] = [{"type": "context", "elements": []}]
    service.post_message_raw(channel="C123", text="", blocks=blocks_no_text)
    mock_client.post_chat_message.assert_called_with(
        channel="C123",
        text="Fallback default",
        blocks=blocks_no_text,
    )
