"""
Block: email_monitor
Beschreibung: Prüft eine IMAP-Inbox auf neue E-Mails.
Benötigte Keys: []
"""

import imaplib
import email
from email.header import decode_header

BLOCK_META = {
    "name": "E-Mail Monitor",
    "description": "Prüft IMAP-Inbox auf neue Nachrichten",
    "required_keys": [],
    "version": "1.0",
}


def _decode_header(header):
    decoded, encoding = decode_header(header)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(encoding or "utf-8", errors="replace")
    return decoded


async def execute(input_data: dict, config: dict, context: dict) -> dict:
    log = context["log"]

    server = config.get("imap_server", "")
    username = config.get("username", "")
    password = config.get("password", "")
    folder = config.get("folder", "INBOX")
    filter_subject = config.get("filter", "")
    max_emails = config.get("max_emails", 10)

    if not server or not username or not password:
        await log("IMAP-Zugangsdaten fehlen in der Konfiguration.", "error")
        return {"success": False, "error": "IMAP-Zugangsdaten fehlen"}

    try:
        await log(f"Verbinde mit {server}...")
        mail = imaplib.IMAP4_SSL(server)
        mail.login(username, password)
        mail.select(folder)

        # Ungelesene E-Mails suchen
        search_criteria = "UNSEEN"
        if filter_subject:
            search_criteria = f'(UNSEEN SUBJECT "{filter_subject}")'

        status, messages = mail.search(None, search_criteria)
        mail_ids = messages[0].split()
        mail_ids = mail_ids[-max_emails:]  # Nur die neuesten

        emails = []
        for mail_id in mail_ids:
            status, msg_data = mail.fetch(mail_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = _decode_header(msg["Subject"] or "")
                    sender = _decode_header(msg["From"] or "")
                    date = msg["Date"] or ""

                    # Text extrahieren
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

                    emails.append({
                        "subject": subject,
                        "from": sender,
                        "date": date,
                        "body": body[:2000],
                    })

        mail.logout()
        await log(f"{len(emails)} neue E-Mail(s) gefunden.")
        return {"success": True, "data": {"emails": emails, "count": len(emails)}}

    except Exception as e:
        await log(f"Fehler beim E-Mail-Abruf: {e}", "error")
        return {"success": False, "error": str(e)}
