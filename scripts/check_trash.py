import os
import json
import imapclient
import email
import re
from email.header import decode_header
from datetime import datetime, timedelta
import locale
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app/.env'))
load_dotenv(env_path)
IMAP_SERVER = os.getenv('IMAP_SERVER')
EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')

# Set the locale to German
locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')

TRASH_FILE = os.path.join(os.path.dirname(__file__), '../data/trash.json')

TRASH_COLORS = {
    'braune': 'Braune Tonne',
    'blaue': 'Blaue Tonne',
    'graue': 'Schwarze Tonne',
    'gelbe': 'Gelbe Tonne',
}


def update_trash_status(date_str, color):
    # Load existing trash data
    try:
        with open(TRASH_FILE, 'r') as f:

            trash_data = json.load(f)

    except (FileNotFoundError, json.JSONDecodeError):
        trash_data = {}

    # Add or update the entry
    print(f"Adding: {date_str} -> {color}")
    trash_data[date_str] = color

    # Save to file
    with open(TRASH_FILE, 'w') as f:

        print(f"Updated trash data: {trash_data}")
        json.dump(trash_data, f, indent=4)

def parse_email_body(msg):
    # Get the email body
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(part.get_content_charset())
                break
    else:
        body = msg.get_payload(decode=True).decode(msg.get_content_charset())

    # Extract date and color from body
    date_pattern = r'\b(?:Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag), \d{1,2}\. (?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember) \d{4}\b'
    color_pattern = r'\b(braune|blaue|schwarze|gelbe)\b'
    
    date_match = re.search(date_pattern, body)
    color_match = re.search(color_pattern, body, re.IGNORECASE)
    if date_match and color_match:
        date_str = date_match.group(0)
        color_key = color_match.group(0).lower()
        color = TRASH_COLORS.get(color_key)
        if color:
            update_trash_status(date_str, color)

def check_for_trash_email():
    with imapclient.IMAPClient(IMAP_SERVER) as client:
        client.login(EMAIL, PASSWORD)
        client.select_folder('INBOX')
        messages = client.search('UNSEEN FROM "no-reply@gelsendienste.de"')
        for msg_id in messages:
            raw_message = client.fetch(msg_id, ['RFC822'])[msg_id][b'RFC822']
            msg = email.message_from_bytes(raw_message)
            parse_email_body(msg)

        client.logout()


def cleanup_old_entries():
    DATE_FORMAT = "%A, %d. %B %Y"
    try:
        with open(TRASH_FILE, 'r') as f:
            data = json.load(f)

        today = datetime.now().date()

        # Keep only valid and future dates (including today)
        updated_data = {
            date_str: data[date_str]
            for date_str in data
            if datetime.strptime(date_str, DATE_FORMAT).date() >= today
        }

        # Sort by date (earliest to latest)
        sorted_data = dict(
            sorted(
                updated_data.items(),
                key=lambda item: datetime.strptime(item[0], DATE_FORMAT)
            )
        )

        # Write sorted data back to file
        with open(TRASH_FILE, 'w') as f:
            json.dump(sorted_data, f, indent=4)

        print("Cleanup complete. Updated data:", sorted_data)

    except Exception as e:
        print(f"Cleanup error: {e}")
if __name__ == "__main__":
    try:
        check_for_trash_email()
        cleanup_old_entries()
    except Exception as e:
        print(f"Error: {e}")