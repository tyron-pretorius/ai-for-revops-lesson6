# Adding Gmail Readonly Scope to Existing Service Account

This guide continues from the [Gmail Service Account Setup Instructions](#) and shows how to add the `https://www.googleapis.com/auth/gmail.readonly` scope to your existing service account configuration.

## Prerequisites

- You have already completed the Gmail Service Account Setup Instructions
- Your service account is configured with domain-wide delegation
- You have access to Google Workspace Admin Console

## Step-by-Step Instructions

### Step 1: Update Domain-Wide Delegation in Google Workspace Admin Console

1. Go to [Google Workspace Admin Console](https://admin.google.com/)
2. Navigate to **Security** > **API Controls** > **Domain-wide Delegation**
3. Find your existing service account entry (the one you created in the previous setup)
4. Click on the entry to edit it, or click **"Edit"** if available
5. In the **OAuth Scopes** field, you should currently see:
   ```
   https://www.googleapis.com/auth/gmail.send
   ```
6. Update it to include both scopes (one per line):
   ```
   https://www.googleapis.com/auth/gmail.send
   https://www.googleapis.com/auth/gmail.readonly
   ```
7. Click **"Update"** or **"Save"** to apply the changes

### Step 2: Verify the Scope in Your Code

1. Open `gmail_functions.py`
2. Verify that line 16 includes both scopes:
   ```python
   SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"]
   ```
3. If it's not already there, add `"https://www.googleapis.com/auth/gmail.readonly"` to the `SCOPES` list

### Step 3: Test the Updated Configuration

You can test if the readonly scope is working by running:

```python
from gmail_functions import get_gmail_service, fetch_new_messages

# Replace with an email from your Google Workspace domain
service = get_gmail_service("user@yourdomain.com")

# Try fetching messages to verify readonly access
messages = fetch_new_messages(max_results=5)
print(f"Successfully fetched {len(messages)} messages!")
```

## Important Notes

⚠️ **Scope Propagation:**
- Changes to domain-wide delegation may take a few minutes to propagate
- If you get permission errors immediately after updating, wait 2-5 minutes and try again

⚠️ **Scope Requirements:**
- `gmail.send`: Allows sending emails on behalf of users
- `gmail.readonly`: Allows reading emails (messages, threads, labels) without modifying them
- Both scopes are required if your application needs to both read and send emails

## Troubleshooting

**Error: "Insufficient permissions" when fetching messages**
- Verify that the readonly scope was added correctly in Admin Console
- Check that both scopes are on separate lines in the OAuth Scopes field
- Ensure there are no extra spaces or typos in the scope URL
- Wait a few minutes for the changes to propagate

**Error: "Access denied" or "Delegation denied"**
- Double-check that the Client ID in Admin Console matches your service account's Unique ID
- Verify the service account still exists in Google Cloud Console
- Try removing and re-adding the domain-wide delegation entry

## Additional Resources

- [Gmail API Scopes Documentation](https://develop.google.com/gmail/api/auth/scopes)
- [Domain-Wide Delegation Guide](https://developers.google.com/identity/protocols/oauth2/service-account#delegatingauthority)

