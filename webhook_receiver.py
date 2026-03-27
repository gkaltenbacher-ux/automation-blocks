"""
Block: webhook_receiver
Beschreibung: Empfängt externe Webhooks und leitet Daten in die Pipeline weiter.
Benötigte Keys: []
"""

import json
import urllib.request

BLOCK_META = {
    "name": "Webhook Empfänger",
    "description": "Empfängt Daten von externen Webhooks",
    "required_keys": [],
    "version": "1.0",
}


async def execute(input_data: dict, config: dict, context: dict) -> dict:
    log = context["log"]

    source_url = config.get("source_url", "")
    headers = config.get("headers", {})
    method = config.get("method", "GET").upper()
    data_path = config.get("data_path", "")

    if not source_url:
        # Wenn keine URL, einfach input_data durchreichen
        await log("Kein Source-URL konfiguriert, leite Eingabedaten weiter.")
        return {"success": True, "data": input_data}

    try:
        await log(f"Rufe Webhook-Quelle ab: {source_url}")

        req = urllib.request.Request(source_url, method=method)
        req.add_header("User-Agent", "AutomationBot/1.0")
        for key, value in headers.items():
            req.add_header(key, value)

        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read().decode("utf-8")

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"raw": raw}

        # Optionaler Pfad in die Datenstruktur (z.B. "results.items")
        if data_path:
            for key in data_path.split("."):
                if isinstance(data, dict) and key in data:
                    data = data[key]
                else:
                    await log(f"Pfad '{data_path}' nicht gefunden in Antwort.", "warning")
                    break

        await log("Webhook-Daten empfangen.")
        return {"success": True, "data": data if isinstance(data, dict) else {"items": data}}

    except Exception as e:
        await log(f"Fehler beim Webhook-Abruf: {e}", "error")
        return {"success": False, "error": str(e)}
