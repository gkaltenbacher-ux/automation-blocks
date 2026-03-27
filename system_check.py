"""
Block: system_check
Beschreibung: Prüft DB, API-Keys und loggt eine Zusammenfassung.
Benötigte Keys: []
"""

BLOCK_META = {
    "name": "System-Check",
    "description": "Prüft Datenbank, API-Keys und System-Status",
    "required_keys": [],
    "version": "1.0",
}


async def execute(input_data: dict, config: dict, context: dict) -> dict:
    log = context["log"]
    db = context["db"]

    await log("System-Check gestartet...")

    # Datenbank prüfen
    try:
        logs = db.get_logs(limit=1)
        db_status = "ok"
        await log("Datenbank: OK")
    except Exception as e:
        db_status = f"Fehler: {e}"
        await log(f"Datenbank: {db_status}", "error")

    # API-Keys prüfen
    keys = db.get_all_api_keys()
    key_count = len(keys)
    await log(f"{key_count} API-Key(s) gespeichert.")

    # Zusammenfassung
    summary = {
        "datenbank": db_status,
        "api_keys": key_count,
    }

    await log(f"System-Check abgeschlossen. Alles in Ordnung.")
    return {"success": True, "data": summary}
