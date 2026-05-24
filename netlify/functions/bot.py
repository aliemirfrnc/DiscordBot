"""
bot.py
Netlify serverless function — Discord HTTP Interactions endpoint.

Handles incoming POST requests from Discord:
  - Verifies Ed25519 request signatures
  - Responds to PING (type 1) health checks
  - Routes APPLICATION_COMMAND (type 2) slash commands

Environment variables (set in Netlify → Site config → Environment variables):
  DISCORD_PUBLIC_KEY  — Application Public Key from Discord Developer Portal
  DISCORD_TOKEN       — Bot token for follow-up REST calls (optional here)
"""

import json
import os

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError


def _verify_signature(public_key_hex: str, signature_hex: str, timestamp: str, body: str) -> bool:
    try:
        verify_key = VerifyKey(bytes.fromhex(public_key_hex))
        verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature_hex))
        return True
    except (BadSignatureError, ValueError):
        return False


def _json_response(status: int, payload: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _handle_command(interaction: dict) -> dict:
    command_name = interaction.get("data", {}).get("name", "")

    if command_name == "ping":
        return _json_response(200, {"type": 4, "data": {"content": "Pong!"}})

    if command_name in ("yardim", "help"):
        return _json_response(200, {
            "type": 4,
            "data": {
                "content": (
                    "**Kullanılabilir Komutlar**\n"
                    "`/ping` — Bağlantı testi\n"
                    "`/yardim` — Bu mesajı göster"
                )
            },
        })

    return _json_response(200, {
        "type": 4,
        "data": {"content": f"Bilinmeyen komut: `{command_name}`"},
    })


def handler(event, context):
    public_key = os.environ.get("DISCORD_PUBLIC_KEY", "")
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    signature = headers.get("x-signature-ed25519", "")
    timestamp = headers.get("x-signature-timestamp", "")
    body = event.get("body") or ""

    if not _verify_signature(public_key, signature, timestamp, body):
        return {"statusCode": 401, "body": "Invalid request signature"}

    try:
        interaction = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return {"statusCode": 400, "body": "Invalid JSON body"}

    interaction_type = interaction.get("type")

    # PING — Discord endpoint verification
    if interaction_type == 1:
        return _json_response(200, {"type": 1})

    # APPLICATION_COMMAND — slash command
    if interaction_type == 2:
        return _handle_command(interaction)

    return {"statusCode": 400, "body": "Unsupported interaction type"}
