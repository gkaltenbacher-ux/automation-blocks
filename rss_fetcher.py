"""
Block: rss_fetcher
Beschreibung: Ruft einen RSS-Feed ab und findet neue Einträge.
Benötigte Keys: []
"""

import xml.etree.ElementTree as ET
import urllib.request
import hashlib
import json
import os

BLOCK_META = {
    "name": "RSS Fetcher",
    "description": "Ruft RSS-Feed ab und findet neue Einträge",
    "required_keys": [],
    "version": "1.0",
}

CACHE_DIR = "data/rss_cache"


def _get_cache_path(feed_url: str) -> str:
    url_hash = hashlib.md5(feed_url.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{url_hash}.json")


def _load_seen(feed_url: str) -> set:
    path = _get_cache_path(feed_url)
    if os.path.exists(path):
        with open(path, "r") as f:
            return set(json.load(f))
    return set()


def _save_seen(feed_url: str, seen: set):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _get_cache_path(feed_url)
    with open(path, "w") as f:
        json.dump(list(seen), f)


async def execute(input_data: dict, config: dict, context: dict) -> dict:
    log = context["log"]

    feed_url = config.get("url", "")
    max_entries = config.get("max_entries", 10)

    if not feed_url:
        await log("Keine Feed-URL konfiguriert.", "error")
        return {"success": False, "error": "Feed-URL fehlt"}

    try:
        await log(f"Rufe RSS-Feed ab: {feed_url}")
        req = urllib.request.Request(feed_url, headers={"User-Agent": "AutomationBot/1.0"})
        with urllib.request.urlopen(req, timeout=30) as res:
            xml_data = res.read()

        root = ET.fromstring(xml_data)
        seen = _load_seen(feed_url)
        new_entries = []

        # RSS 2.0
        for item in root.findall(".//item")[:max_entries]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            description = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")
            entry_id = link or title

            if entry_id not in seen:
                new_entries.append({
                    "title": title,
                    "link": link,
                    "summary": description[:500],
                    "date": pub_date,
                })
                seen.add(entry_id)

        # Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//atom:entry", ns)[:max_entries]:
            title = entry.findtext("atom:title", "", ns)
            link_el = entry.find("atom:link", ns)
            link = link_el.get("href", "") if link_el is not None else ""
            summary = entry.findtext("atom:summary", "", ns)
            updated = entry.findtext("atom:updated", "", ns)
            entry_id = link or title

            if entry_id not in seen:
                new_entries.append({
                    "title": title,
                    "link": link,
                    "summary": summary[:500],
                    "date": updated,
                })
                seen.add(entry_id)

        _save_seen(feed_url, seen)
        await log(f"{len(new_entries)} neue Einträge gefunden.")
        return {"success": True, "data": {"entries": new_entries, "count": len(new_entries)}}

    except Exception as e:
        await log(f"Fehler beim RSS-Abruf: {e}", "error")
        return {"success": False, "error": str(e)}
