from simple_salesforce import Salesforce
import os, dotenv
from datetime import datetime

dotenv.load_dotenv()

def sfdc_connection():
    username = os.environ["SALESFORCE_USER"]
    password = os.environ["SALESFORCE_PASSWORD"]
    security_token = os.environ["SALESFORCE_TOKEN"]

    return Salesforce(
        username=username,
        password=password,
        security_token=security_token,
        client_id="Replit",
    )


def find_contact_or_lead_by_email(email):
    """
    Simplified function to find if an email belongs to a Contact or Lead in Salesforce.
    
    Args:
        email: Email address to search for (string)
    
    Returns:
        Dictionary with 'type' ('contact' or 'lead'), 'id', and 'first_name', or None if not found
        Example: {'type': 'contact', 'id': '003XX000004TmiQYAS', 'first_name': 'John'}
        Example: {'type': 'lead', 'id': '00QXX000004TmiQYAS', 'first_name': 'Jane'}
        Example: None (if not found)
    """
    if not email or not email.strip():
        return None
    
    email = email.strip()
    
    # Get Salesforce connection
    sf = sfdc_connection()
    
    # First, check Contacts
    contact_query = f"SELECT Id, Email, FirstName FROM Contact WHERE Email = '{email}' LIMIT 1"
    contacts = sf.query(contact_query)
    
    if contacts.get('records') and len(contacts['records']) > 0:
        contact = contacts['records'][0]
        return {
            'type': 'contact',
            'id': contact['Id'],
            'first_name': contact.get('FirstName', '')
        }
    
    # If not found as Contact, check Leads
    lead_query = f"SELECT Id, Email, FirstName FROM Lead WHERE Email = '{email}' LIMIT 1"
    leads = sf.query(lead_query)
    
    if leads.get('records') and len(leads['records']) > 0:
        lead = leads['records'][0]
        return {
            'type': 'lead',
            'id': lead['Id'],
            'first_name': lead.get('FirstName', '')
        }
    
    # Not found in either
    return None

def create_lead(fields):
    sf = sfdc_connection()
    response = sf.Lead.create(fields)
    return response

def log_sfdc_task(person_id: str, subject: str, body: str, direction: str = "Inbound"):
    """
    Create a Task in Salesforce to log email activity.
    
    Args:
        person_id: Contact or Lead ID (WhoId)
        subject: Email subject
        body: Email body content
        direction: 'Inbound' or 'Outbound' (default: 'Inbound')
        activity_date: Activity date in YYYY-MM-DD format (default: today)
        sender_email: Sender email address (default: None)
        record_type_id: Record Type ID for the task (default: '012f100000116jjAAA')
        owner_id: Owner ID for the task (default: '005Qk000001pqtdIAA')
        created_by_tool: Tool that created the task (default: 'Email Responder')
    
    Returns:
        Dictionary with 'success' (bool) and 'id' (task ID) if successful, or error info
    """
    
    sf = sfdc_connection()
    
    # Default activity date to today if not provided
    activity_date = datetime.now().strftime('%Y-%m-%d')
    
    task_fields = {
        'RecordTypeId': '012f100000116jjAAA',
        'WhoId': person_id,
        'Subject': subject,
        'ActivityDate': activity_date,
        'Status': 'Completed',
        'OwnerId': '005Qk000001pqtdIAA',
        'Description': body,
        'Type': 'Email',
        'TaskSubType': 'Email',
        'Task_Direction__c': direction,
    }
    
    try:
        response = sf.Task.create(task_fields)
        return {'success': True, 'id': response['id']}
    except Exception as e:
        return {'success': False, 'error': str(e)}