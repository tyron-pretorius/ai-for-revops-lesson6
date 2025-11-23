import os
import json
import base64
import re
from email.message import EmailMessage

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ---------- Config ----------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(SCRIPT_DIR, "gmail_auth.json")

# Read + send
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"]

CHECKPOINT_FILE = os.path.join(SCRIPT_DIR, "last_msg.json")
IMPERSONATED_USER = "tyron@theworkflowpro.com"  # the mailbox you're reading/sending as

# ---------- Gmail service ----------

def get_gmail_service(user_email: str):
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    delegated_credentials = credentials.with_subject(user_email)
    return build("gmail", "v1", credentials=delegated_credentials)

gmail = get_gmail_service(IMPERSONATED_USER)

# ---------- Send email ----------

def send_email(service, sender: str, to: str, cc: str = "", subject: str = "", message_text: str = "", reply_to: str = "", is_html: bool = False, thread_id: str = None, in_reply_to: str = None):
    """
    Send an email using the Gmail API.
    
    Args:
        service: Gmail service object
        sender: Sender email address
        to: Recipient email address
        cc: CC email address(es) (optional)
        subject: Email subject
        message_text: Email body content
        reply_to: Reply-To header (optional)
        is_html: Whether message_text is HTML (default: False)
        thread_id: Gmail thread ID to reply in the same thread (optional)
        in_reply_to: Message-ID of the email being replied to (optional, for threading)
    """
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    if cc:
        message["Cc"] = cc
    message["Subject"] = subject
    if reply_to:
        message["Reply-To"] = reply_to
    
    # Set threading headers for replies
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = in_reply_to

    if is_html:
        message.set_content(message_text, subtype="html")
    else:
        message.set_content(message_text)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    body = {"raw": raw_message}
    
    # Include threadId in the send request to ensure it's in the same thread
    if thread_id:
        body["threadId"] = thread_id

    sent_message = service.users().messages().send(userId="me", body=body).execute()
    return sent_message

# ---------- Checkpoint helpers ----------

def get_last_msg_id():
    try:
        with open(CHECKPOINT_FILE) as f:
            return json.load(f).get("last_id")
    except FileNotFoundError:
        return None

def save_last_msg_id(msg_id: str):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"last_id": msg_id}, f)

# ---------- Polling & processing ----------

def fetch_new_messages(max_results: int = 10, query: str = None):
    """
    Fetch new messages and return a list of dictionaries with email information.
    
    Returns:
        List of dictionaries, each containing:
        - subject_line: Email subject
        - sender_email: Sender's email address
        - body: The sender's email body (plain text)
        - first_body: First email body if this is the second email and first was from IMPERSONATED_USER, else None
        - thread_id: Gmail thread ID for threading replies
        - message_id: Message-ID header for threading replies
    """
    last_id = get_last_msg_id()

    resp = gmail.users().messages().list(userId="me",maxResults=max_results,q=query).execute()

    messages = resp.get("messages", [])

    new_messages = []

    if last_id:
        # We have a checkpoint; stop at the last seen ID
        for m in messages:
            if m["id"] == last_id:
                break
            new_messages.append(m)
    else:
        # First run: all messages returned by the query
        new_messages = messages[:]

    # Save newest message ID as new checkpoint for next run
    if messages:
        save_last_msg_id(messages[0]["id"])

    # Process messages and build result list
    result = []
    
    # process oldest → newest for nicer ordering
    for m in reversed(new_messages):
        full = gmail.users().messages().get(userId="me", id=m["id"], format="full").execute()
        
        # Get thread information
        thread_id = full["threadId"]
        thread = gmail.users().threads().get(userId="me", id=thread_id, format="full").execute()
        messages_in_thread = thread.get("messages", [])
        
        # Find the index of current message in thread
        current_index = None
        for idx, tmsg in enumerate(messages_in_thread, start=1):
            if tmsg["id"] == full["id"]:
                current_index = idx
                break
        
        # Extract information from current message
        headers = full["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
        sender_email = extract_sender_email(full)
        body_text = extract_message_body(full)
        
        # Skip if no plain text
        if body_text == "No plain text present":
            continue
        
        # Check if this is second message and first was from IMPERSONATED_USER
        first_body = None
        if current_index == 2:
            first_msg = messages_in_thread[0]
            first_msg_sender = extract_sender_email(first_msg)
            
            if first_msg_sender == IMPERSONATED_USER:
                first_msg_body = extract_message_body(first_msg)
                if first_msg_body != "No plain text present":
                    first_body = first_msg_body
        
        # Extract Message-ID for threading
        message_id = next((h["value"] for h in headers if h["name"] == "Message-ID"), "")
        
        result.append({
            "subject_line": subject,
            "sender_email": sender_email,
            "body": body_text,
            "first_body": first_body,
            "thread_id": thread_id,
            "message_id": message_id
        })
    
    return result


def extract_message_body(msg):
    """
    Tries to pull out the text/plain body from a message.
    If there is no text/plain part anywhere, returns 'No plain text present'.
    """
    payload = msg.get("payload", {})
    body = ""

    def _get_body(part):
        data = part.get("body", {}).get("data")
        if not data:
            return ""
        decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return decoded

    # If multipart, look for text/plain parts only
    if "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain":
                body_part = _get_body(part)
                if body_part:
                    body += body_part
    else:
        # Single-part message – only accept if it's text/plain
        mime_type = payload.get("mimeType", "")
        if mime_type == "text/plain":
            body = _get_body(payload)

    body = (body or "").strip()
    if not body:
        return "No plain text present"
    return body

def extract_sender_email(msg):
    """
    Extract sender email address from a message.
    Returns the sender's email address.
    """
    headers = msg["payload"]["headers"]
    from_header = next((h["value"] for h in headers if h["name"] == "From"), "")
    
    # Extract email from "Name <email@example.com>" format
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_header)
    return match.group(0) if match else from_header.strip()
