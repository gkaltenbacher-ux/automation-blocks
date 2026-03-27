"""
Block: slack_notifier
Beschreibung: Sendet eine Nachricht an einen Slack-Webhook.
Benötigte Keys: [slack]
"""

import json
import urllib.request

BLOCK_META = {
    "name": "Slack Benachrichtigung",
    "description": "Sendet Nachricht an Slack-Kanal via Webhook",
    "required_keys": ["slack"],
    "version": "1.0",
}


async def execute(input_data: dict, config: dict, context: dict) -> dict:
    log = context["log"]
    get_api_key = context["get_api_key"]

    webhook_url = get_api_key("slack")
    if not webhook_url:
        await log("Kein Slack-Webhook konfiguriert.", "error")
        return {"success": False, "error": "Slack-Webhook fehlt"}

    template = config.get("template", "{message}")
    channel = config.get("channel", "")

    # Template mit Daten füllen
    message = template
    for key, value in input_data.items():
        if isinstance(value, str):
            message = message.replace(f"{{{key}}}", value)
        elif isinstance(value, (int, float)):
            message = message.replace(f"{{{key}}}", str(value))

    # Wenn summary vorhanden, als Nachricht verwenden
    if "{summary}" in template and "summary" in input_data:
        summary = input_data["summary"]
        if isinstance(summary, dict):
            summary = json.dumps(summary, ensure_ascii=False, indent=2)
        message = template.replace("{summary}", str(summary))

    payload = json.dumps({"text": message}).encode()

    try:
        await log(f"Sende Slack-Nachricht...")
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            response = res.read().decode()

        if response == "ok":
            await log("Slack-Nachricht gesendet.")
            return {"success": True, "data": {"sent": True, "message": message}}
        else:
            await log(f"Unerwartete Slack-Antwort: {response}", "warning")
            return {"success": True, "data": {"sent": True, "message": message}}

    except Exception as e:
        await log(f"Fehler beim Senden an Slack: {e}", "error")
        return {"success": False, "error": str(e)}
