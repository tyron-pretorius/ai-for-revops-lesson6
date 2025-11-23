import time
from datetime import datetime
from gmail_functions import fetch_new_messages, send_email, gmail, IMPERSONATED_USER
from openai_functions import create_openai_response
from salesforce_functions import find_contact_or_lead_by_email, create_lead, log_sfdc_task

def process_emails(polling_interval: int = 60, max_results: int = 1):
    """
    Main function to fetch emails, look them up in Salesforce, and send AI-generated responses.
    
    Args:
        polling_interval: Delay in seconds between polling cycles (default: 60)
    """
    # Build query to get messages from the last polling_interval seconds
    # Convert seconds to Gmail query format (newer_than supports s, m, h, d)
    if polling_interval < 60:
        time_query = f"newer_than:{polling_interval}s"
    elif polling_interval < 3600:
        minutes = polling_interval // 60
        time_query = f"newer_than:{minutes}m"
    else:
        hours = polling_interval // 3600
        time_query = f"newer_than:{hours}h"
    
    query = f"in:inbox {time_query}"
    
    # Fetch new messages
    email_list = fetch_new_messages(max_results=max_results, query=query)
    
    if not email_list:
        print("No new emails to process.")
        return
    
    print(f"Processing {len(email_list)} email(s)...")
    
    for email_data in email_list:
        subject_line = email_data["subject_line"]
        sender_email = email_data["sender_email"]
        body = email_data["body"]
        first_body = email_data["first_body"]
        thread_id = email_data.get("thread_id")
        message_id = email_data.get("message_id")
        
        print(f"\n{'='*60}")
        print(f"Processing email from: {sender_email}")
        print(f"Subject: {subject_line}")
        
        # Look up sender in Salesforce
        sf_result = find_contact_or_lead_by_email(email=sender_email)
        
        if not sf_result:
            sf_result = create_lead(fields={"email": sender_email, "LastName": "Unknown", "Company": "Unknown"}) #could use AI to parse last name and company from email body
            id = sf_result["id"]
            first_name = "there"
            print(f"  → Created new lead in Salesforce: {id}")
        
        salesforce_id = sf_result["id"]
        first_name = sf_result.get("first_name", None)
        if not first_name: #if first name is empty in SFDC
            first_name = "there"
        
        # Log incoming email as a task in Salesforce
        task_result = log_sfdc_task(person_id=salesforce_id,subject=subject_line, body=body, direction="Inbound")
        
        if task_result.get('success'):
            print(f"  → Logged incoming email as Task: {task_result['id']}")
        else:
            print(f"  → Failed to log incoming email task: {task_result.get('error')}")
        
        # Build input text for AI
        if first_body:
            ai_input = f"Previous message from {IMPERSONATED_USER}:\n{first_body}\n\n---\n\nCurrent message from {sender_email}:\n{body}"
        else:
            ai_input = body
        
        # Get AI response
        try:
            print(f"  → Generating AI response...")
            ai_response = create_openai_response(input=ai_input,sfdc_id=salesforce_id)

            # Convert plain text line breaks to HTML line breaks
            ai_response_html = ai_response.replace('\n', '<br>')
            
            email_body = f"""Hi {first_name},<br><br>{ai_response_html}<br><br>All the best,<br>The Workflow Pro"""

            # Prepare reply subject
            reply_subject = subject_line
            if not reply_subject.lower().startswith("re:"):
                reply_subject = f"Re: {reply_subject}"
            
            # Send reply email in the same thread
            send_email(service=gmail,sender=IMPERSONATED_USER,to=sender_email, subject=reply_subject,
                message_text=email_body, is_html=True, reply_to=IMPERSONATED_USER, thread_id=thread_id, in_reply_to=message_id)
            
            print(f"  → Reply sent successfully to {sender_email}")
            
            # Log outgoing reply email as a task in Salesforce
            task_result = log_sfdc_task(person_id=salesforce_id,subject=reply_subject, body=ai_response, direction="Outbound")
            if task_result.get('success'):
                print(f"  → Logged outgoing email as Task: {task_result['id']}")
            else:
                print(f"  → Failed to log outgoing email task: {task_result.get('error')}")
            
        except Exception as e:
            print(f"  → Error processing email: {e}")
            continue

if __name__ == "__main__":
    polling_interval = 5  # Poll every 5 seconds
    
    #Uncomment for continuous polling:
    while True:
        process_emails(polling_interval=polling_interval)
        time.sleep(polling_interval)
    
    # For single run:
    #process_emails(polling_interval=polling_interval, max_results=3)
