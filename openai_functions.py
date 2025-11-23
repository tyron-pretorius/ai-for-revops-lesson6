import os, json
from typing import Dict
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONV_ID_FILE = os.path.join(SCRIPT_DIR, "sfdc_id_to_conv_id.json")

def _load_conv_id_mapping() -> Dict[str, str]:
    """
    Load the Salesforce ID to conversation ID mapping from file.
    Creates the file if it doesn't exist.
    
    Returns:
        Dictionary mapping Salesforce IDs to conversation IDs
    """
    if os.path.exists(CONV_ID_FILE):
        try:
            with open(CONV_ID_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If file is corrupted or can't be read, return empty dict
            return {}
    else:
        # Create empty file if it doesn't exist
        with open(CONV_ID_FILE, 'w') as f:
            json.dump({}, f)
        return {}

def _save_conv_id_mapping(mapping: Dict[str, str]):
    """
    Save the Salesforce ID to conversation ID mapping to file.
    
    Args:
        mapping: Dictionary mapping Salesforce IDs to conversation IDs
    """
    with open(CONV_ID_FILE, 'w') as f:
        json.dump(mapping, f, indent=2)

def get_or_create_conv_id(salesforce_id: str) -> str:
    """
    Get or create a conversation ID for a Salesforce Contact/Lead ID.
    Stores the mapping in sfdc_id_to_conv_id.json file.
    
    Args:
        salesforce_id: The Salesforce Contact or Lead ID
    
    Returns:
        Conversation ID string
    """
    # Load existing mappings
    mapping = _load_conv_id_mapping()
    
    # Check if conversation ID already exists
    if salesforce_id in mapping:
        return mapping[salesforce_id]
    
    # Create new conversation
    conv = client.conversations.create()  # returns { id: "conv_..." , ... }
    conv_id = conv.id
    
    # Save to mapping and persist to file
    mapping[salesforce_id] = conv_id
    _save_conv_id_mapping(mapping)
    
    return conv_id

MODEL = "gpt-5"
PROMPT_ID = "pmpt_691e92d851248190a52f04f35cf34b1a065c1f5998efcb1e"

def create_openai_response(input: str, sfdc_id: str) -> str:

    # Get or create conversation ID using Salesforce ID
    conversation_id = get_or_create_conv_id(sfdc_id)
        
    resp = client.responses.create(
        model=MODEL,
        prompt={"id": PROMPT_ID},
        input=[{"role": "user", "content": input}],
        conversation=conversation_id
    )

    raw = resp.output_text
    #print(json.dumps(resp.model_dump(), indent=2))
    print(raw)
    return raw