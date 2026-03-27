"""
Block: llm_summarizer
Beschreibung: Fasst Text mit einem LLM zusammen (OpenAI oder Anthropic).
Benötigte Keys: [openai] oder [anthropic]
"""

import json
import urllib.request

BLOCK_META = {
    "name": "LLM Zusammenfassung",
    "description": "Fasst Text mit KI zusammen (OpenAI oder Anthropic)",
    "required_keys": ["openai"],
    "version": "1.0",
}


async def _call_openai(api_key: str, model: str, system_prompt: str, user_content: str) -> str:
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.3,
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        data = json.loads(res.read())
    return data["choices"][0]["message"]["content"]


async def _call_anthropic(api_key: str, model: str, system_prompt: str, user_content: str) -> str:
    payload = json.dumps({
        "model": model,
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        data = json.loads(res.read())
    return data["content"][0]["text"]


async def execute(input_data: dict, config: dict, context: dict) -> dict:
    log = context["log"]
    get_api_key = context["get_api_key"]

    model = config.get("model", "gpt-4o-mini")
    prompt_file = config.get("prompt_file", "")
    output_format = config.get("output_format", "text")
    provider = config.get("provider", "openai")

    # API-Key holen
    api_key = get_api_key(provider)
    if not api_key:
        await log(f"Kein API-Key für '{provider}' gefunden.", "error")
        return {"success": False, "error": f"API-Key für '{provider}' fehlt"}

    # System-Prompt laden
    system_prompt = config.get("prompt", "Fasse den folgenden Text zusammen.")
    if prompt_file:
        try:
            with open(prompt_file, "r") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            await log(f"Prompt-Datei '{prompt_file}' nicht gefunden, verwende Standard-Prompt.", "warning")

    if output_format == "json":
        system_prompt += "\n\nAntworte ausschliesslich als valides JSON."

    # Input vorbereiten
    user_content = ""
    if "emails" in input_data:
        for mail in input_data["emails"]:
            user_content += f"Von: {mail.get('from', '')}\nBetreff: {mail.get('subject', '')}\n{mail.get('body', '')}\n---\n"
    elif "text" in input_data:
        user_content = input_data["text"]
    elif "entries" in input_data:
        for entry in input_data["entries"]:
            user_content += f"Titel: {entry.get('title', '')}\n{entry.get('summary', '')}\n---\n"
    else:
        user_content = json.dumps(input_data, ensure_ascii=False, default=str)

    if not user_content.strip():
        await log("Keine Daten zum Zusammenfassen.", "warning")
        return {"success": True, "data": {"summary": "", "skipped": True}}

    await log(f"Sende an {provider} ({model})...")

    try:
        if provider == "anthropic":
            result = await _call_anthropic(api_key, model, system_prompt, user_content)
        else:
            result = await _call_openai(api_key, model, system_prompt, user_content)

        # JSON parsen wenn gewünscht
        if output_format == "json":
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                await log("LLM-Antwort ist kein valides JSON, gebe Rohtext zurück.", "warning")

        await log("Zusammenfassung erstellt.")
        return {"success": True, "data": {"summary": result}}

    except Exception as e:
        await log(f"Fehler bei LLM-Aufruf: {e}", "error")
        return {"success": False, "error": str(e)}
