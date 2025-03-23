import os
import json
import imapclient
import email
from email.header import decode_header
from datetime import datetime, timedelta

# File paths
TRASH_FILE = os.path.join(os.path.dirname(__file__), '../data/trash.json')

# Email settings
IMAP_SERVER = 'imap.gmail.com'
EMAIL = 'your-email@gmail.com'
PASSWORD = 'your-email-password'

# Colors to match
TRASH_COLORS = {
    'yellow': 'Trash tomorrow (Yellow)',
    'blue': 'Trash tomorrow (Blue)',
    'black': 'Trash tomorrow (Black)'
}

def update_trash_status(color):
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    new_status = f"{TRASH_COLORS[color]} - {tomorrow}"

    # Save to file
    with open(TRASH_FILE, 'w') as f:
        json.dump({'status': new_status}, f, indent=4)

def reset_trash_status():
    with open(TRASH_FILE, 'w') as f:
        json.dump({'status': 'Morgen keine Müllabfuhr'}, f, indent=4)

def check_for_trash_email():
    with imapclient.IMAPClient(IMAP_SERVER) as client:
        client.login(EMAIL, PASSWORD)
        client.select_folder('INBOX')

        # Search for unread emails from the trash company
        messages = client.search('UNSEEN FROM "trashcompany@example.com"')
        for msg_id in messages:
            raw_message = client.fetch(msg_id, ['RFC822'])[msg_id][b'RFC822']
            msg = email.message_from_bytes(raw_message)

            subject, encoding = decode_header(msg['Subject'])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or 'utf-8')

            print(f"Found email with subject: {subject}")

            if 'yellow' in subject.lower():
                update_trash_status('yellow')
            elif 'blue' in subject.lower():
                update_trash_status('blue')
            elif 'black' in subject.lower():
                update_trash_status('black')

        client.logout()

if __name__ == "__main__":
    try:
        check_for_trash_email()
    except Exception as e:
        print(f"Error: {e}")
