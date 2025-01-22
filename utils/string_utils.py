
import random
import string
import time

def generate_unique_string(church_id: str) -> str:
    """
    Generates a unique alphanumeric string based on church_id, current timestamp, and a random component.
    
    Args:
    - church_id (str): The identifier for the church.
    
    Returns:
    - str: A unique alphanumeric string.
    """
    # Get the current timestamp in milliseconds
    timestamp = str(int(time.time() * 1000))
    
    # Generate a random 5-character alphanumeric string
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    
    # Combine the church_id, timestamp, and random_string to generate a unique string
    unique_string = f"{church_id}_{timestamp}_{random_string}"
    
    return unique_string
