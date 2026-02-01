import time
import stream
import requests

import asyncio
import threading
from typing import Dict
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
import uuid
import os
from typing import Optional

# AWS Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-2')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'LiveSessionGracePeriods')

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

from getstream import Stream
from getstream.models import CallRequest, CallSettingsRequest
from getstream.models import RecordSettingsRequest
from getstream.models import UserRequest

from utils.string_utils import generate_unique_string

api_key = "gcwwb5wde69h"
api_secret = "mdmaxcad9yqbvp39yc45h39b2ebjcjwzu7pevfpnk7jnxa4dnkvraxpntc643ztm"

call_type = "livestream"
admin_call_role = "admin"
user_call_role = "user"
live_recording_storage = "stream-s3"

main_backend_base_url = "https://uat.gospeltube.tv"
start_live_session_endpoint = "/api/v1/webhook/church/videos/live"
end_live_session_endpoint = "/api/v1/webhook/end-live-stream"


# ----------------------- Generate Token for User --------------------------


def get_user_token(user_id):
    try:
        client = stream.connect(api_key, api_secret)
        user_token = client.create_user_token(user_id)
        print("User Token generated for " + user_id + ": " + user_token)

        response = {
            "status": True,
            "id": user_id,
            "message": "Success",
            "token": user_token,
        }
        return response
    
    except Exception as error:
        handle_exception(error)


# ----------------------- Create New Church Channel --------------------------


def setup_church_livestream_channel(church_id):
    try:
        user_token = stream.connect(api_key, api_secret).create_user_token(church_id)
        print("Token generated for " + church_id + ": " + user_token)

        client = Stream(api_key=api_key, api_secret=api_secret)

        update_call_type_response = client.video.update_call_type(
            name=call_type,
            external_storage=live_recording_storage,
        )
        print(
            "\n Updated Recording Storage: ",
            update_call_type_response.data.external_storage,
        )

        church_call_id = generate_unique_string(church_id)
        call = client.video.call(call_type=call_type, id=church_call_id)

        """
        Initiate church call.
        This starts the call in backstage mode, meaning that users cannot join or interact with the call until the church is going live.
        This is handled when the "start_session()" function is invoked
        """
        create_call_response = call.get_or_create(
            data=CallRequest(
                created_by=UserRequest(
                    id=church_id,
                    name="GtubeChurch " + church_id,
                    role=user_call_role,
                ),
                settings_override=CallSettingsRequest(
                    recording=RecordSettingsRequest(
                        mode="available",
                        quality="1080p",
                        audio_only=False,
                    ),
                ),
            ),
        )
        response = {
            "status": True,
            "message": "Success",
            "call_id": create_call_response.data.call.id,
            "channel_name": create_call_response.data.call.created_by.name,
            "rtmp": create_call_response.data.call.ingress.rtmp.address,
            "stream_key": user_token,
        }
        print(" <<<<<<< Success Response: ", str(response))
        return response

    except Exception as error:
        print("\n Error creating call: ", str(error))
        handle_exception(error)


# -------------- Start New Session: Go Live and Start Recording --------------

def start_session(call_id: str):
    try:
        # Check if there's a pending grace period for this call_id
        check_and_cancel_grace_period(call_id)

        client = Stream(api_key=api_key, api_secret=api_secret)

        #  Go live. This allows viewers to join the call and watch
        go_live = client.video.go_live(
            id=call_id,
            type=call_type,
            recording_storage_name=live_recording_storage,
        )
        print("\n Now live: ", go_live.data)

        # Start Recording livestream
        startRecording = client.video.start_recording(
            id=call_id,
            type=call_type,
            recording_external_storage=live_recording_storage,
        )
        print("\n Recording Started: ", startRecording.data)

        # Call endpoint to update event on the Main Backend        
        headers = {
            "Content-Type": ""
        }

        endpoint = main_backend_base_url + start_live_session_endpoint
        response = requests.post(
            f"http://uat.gospeltube.tv/api/v1/webhook/church/videos/live?callId={call_id}",
            json={},
            headers=headers
        )        
        print(f"Start Live Session Response: \n {response}  \n {response.text}", flush=True)
        try:
            json_data = response.json()
            print(f"JSON Response: {json_data}", flush=True)
        except ValueError:
            print("Response is not in JSON format")

        print("Done starting session", flush=True)

    except Exception as error:
        handle_exception(error)

        
# -------------- AWS DynamoDB Helper Functions --------------

def check_and_cancel_grace_period(call_id: str) -> bool:
    """
    Check if there's a pending grace period for the given call_id and cancel it.
    Returns True if a grace period was found and cancelled, False otherwise.
    """
    try:
        # Try to get the grace period from DynamoDB
        response = table.get_item(
            Key={
                'call_id': call_id
            }
        )
        
        # If a grace period exists
        if 'Item' in response:
            # Delete the grace period entry
            table.delete_item(
                Key={
                    'call_id': call_id
                }
            )
            print(f"Session restart detected for {call_id}, grace period cancelled")
            return True
        
        return False
    except ClientError as e:
        print(f"Error checking grace period for {call_id}: {e}")
        return False

def store_grace_period(call_id: str, expiry_time: datetime) -> bool:
    """
    Store grace period information in DynamoDB.
    Returns True if successful, False otherwise.
    """
    try:
        # Store the grace period in DynamoDB
        # TTL is in Unix timestamp format (seconds since epoch)
        ttl = int(expiry_time.timestamp())
        
        table.put_item(
            Item={
                'call_id': call_id,
                'request_id': str(uuid.uuid4()),  # Generate a unique ID for this request
                'expiry_time': expiry_time.isoformat(),  # Store as ISO format string for readability
                'ttl': ttl,  # DynamoDB TTL attribute
                'created_at': datetime.now().isoformat()
            }
        )
        print(f"Grace period stored for {call_id}, expires at {expiry_time}")
        return True
    except ClientError as e:
        print(f"Error storing grace period for {call_id}: {e}")
        return False

def get_pending_grace_periods() -> list:
    """
    Get all pending grace periods that haven't expired.
    This is useful for initializing timers after application restart.
    """
    try:
        # Scan the table for pending grace periods
        # Note: In production with many items, you might want to use pagination
        now = datetime.now().isoformat()
        response = table.scan(
            FilterExpression='expiry_time > :now',
            ExpressionAttributeValues={
                ':now': now
            }
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error getting pending grace periods: {e}")
        return []

# -------------- Request End Session with Grace Period --------------

def request_end_session(call_id: str):
    """
    Schedule a session to end after a grace period of 2 minutes,
    unless it's restarted during that time.
    """
    try:
        print(f"End session requested for {call_id}, starting 2-minute grace period")
        
        # Calculate expiry time (2 minutes from now)
        grace_period_seconds = 120
        expiry_time = datetime.now() + timedelta(seconds=grace_period_seconds)
        
        # Store grace period in DynamoDB
        if store_grace_period(call_id, expiry_time):
            # Create a timer thread
            def end_session_after_grace():
                print(f"Grace period ended for {call_id}, ending session now")
                # Sleep until the grace period ends
                seconds_to_wait = (expiry_time - datetime.now()).total_seconds()
                if seconds_to_wait > 0:
                    time.sleep(seconds_to_wait)
                
                # Check if the grace period still exists
                # If it doesn't exist, it means it was cancelled
                response = table.get_item(
                    Key={
                        'call_id': call_id
                    }
                )
                
                if 'Item' in response:
                    # Grace period still exists, so end the session
                    print(f"Grace period still in database: {call_id}, ending session now")
                    end_session(call_id)
                    
                    # Delete the grace period
                    table.delete_item(
                        Key={
                            'call_id': call_id
                        }
                    )
            
            # Create and start the timer thread
            timer = threading.Thread(target=end_session_after_grace)
            timer.daemon = True  # Allow the thread to be terminated when the main program exits
            timer.start()
            
            print(f"Grace period timer started for {call_id}")
        else:
            print(f"Failed to store grace period for {call_id}")
    except Exception as error:
        handle_exception(error)

# -------------- Helper function to check if a call is in grace period  --------------

def is_call_in_grace_period(call_id: str) -> bool:
    """
    Check if a call is currently in a grace period.
    Returns True if the call is in grace period, False otherwise.
    """
    try:
        # Try to get the grace period from DynamoDB
        response = table.get_item(
            Key={
                'call_id': call_id
            }
        )
        
        # If a grace period exists, check if it's still valid
        if 'Item' in response:
            item = response['Item']
            expiry_time_str = item['expiry_time']
            expiry_time = datetime.fromisoformat(expiry_time_str)
            
            # Check if the grace period has expired
            if datetime.now() < expiry_time:
                print(f"Call {call_id} is in grace period until {expiry_time}")
                return True
            else:
                # Grace period has expired, clean up the database entry
                table.delete_item(
                    Key={
                        'call_id': call_id
                    }
                )
                print(f"Grace period for {call_id} has expired, cleaned up database entry")
                return False
        
        # No grace period found
        return False
        
    except ClientError as e:
        print(f"Error checking grace period for {call_id}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error checking grace period for {call_id}: {e}")
        return False

# -------------- End Session: Stop Live and Stop Recording  --------------

def end_session(call_id):
    try:
        client = Stream(api_key=api_key, api_secret=api_secret)
        call = client.video.call(call_type=call_type, id=call_id)

        stopLive = call.stop_live()
        stopRecording = call.stop_recording()
        print(f"Stopped Live Call and Recording for {call_id}")
        
    except Exception as error:
        if "call egress is not running" in str(error).lower() or "stream error code 4" in str(error).lower():
            print(f"Recording already ended for {call_id}")
            upload_recording(call_id)
        handle_exception(error)

# -------------- Upload Video Recording: Get Recording and Upload to Church Videos --------------

def upload_recording(call_id):
    try:
        # Check if the call is still in grace period
        if is_call_in_grace_period(call_id):
            print(f"Call {call_id} is still in grace period, skipping call end and recording upload")
            return
    
        client = Stream(api_key=api_key, api_secret=api_secret)
        call = client.video.call(call_type=call_type, id=call_id)

        list_recordings = call.list_recordings()
        print("\n\n List of recordings: ", list_recordings.data)
        recording_url = f"https://{live_recording_storage}.s3.us-east-2.amazonaws.com/gtube_liverecordings_s3bucket/{call_type}_{call_id}/{list_recordings.data.recordings[0].filename}"
        print("\n\n ------ Recordings URL: ", recording_url)

        # Call endpoint to end session and upload recorded livestream on the Main Backend
        headers = {
            "Content-Type": ""
        }

        endpoint = main_backend_base_url + end_live_session_endpoint
        response = requests.put(
            f"http://uat.gospeltube.tv/api/v1/webhook/end-live-stream?recordingUrl={recording_url}&callId={call_id}",
            headers=headers,
        )
        print(f"End Live Session Response: \n {response}  \n {response.text}", flush=True)
        print("Done ending session", flush=True)

    except Exception as error:
        handle_exception(error)

# ---------------------------Error Handlers------------------------------------

def handle_exception(error):
    # Handle all exceptions
    response = {"status": False, "message": str(error)}
    print("Error occured: ", str(response))
    return response, 500

# ---------------------------Application Startup Initialization-----------------

def initialize_grace_periods():
    """
    Initialize timers for any pending grace periods on application startup.
    This ensures grace periods are maintained even if the application restarts.
    """
    pending_grace_periods = get_pending_grace_periods()
    print(f"Found {len(pending_grace_periods)} pending grace periods on startup")
    
    for item in pending_grace_periods:
        call_id = item['call_id']
        expiry_time = datetime.fromisoformat(item['expiry_time'])
        
        # Only initialize if not already expired
        if expiry_time > datetime.now():
            print(f"Initializing timer for call {call_id}, expires at {expiry_time}")
            
            # Create a timer thread
            def end_session_after_grace():
                # Sleep until the grace period ends
                seconds_to_wait = (expiry_time - datetime.now()).total_seconds()
                if seconds_to_wait > 0:
                    time.sleep(seconds_to_wait)
                
                # Check if the grace period still exists
                response = table.get_item(
                    Key={
                        'call_id': call_id
                    }
                )
                
                if 'Item' in response:
                    # Grace period still exists, so end the session
                    print(f"Grace period ended for {call_id}, ending session now")
                    end_session(call_id)
                    upload_recording(call_id)
                    
                    # Delete the grace period
                    table.delete_item(
                        Key={
                            'call_id': call_id
                        }
                    )
            
            # Create and start the timer thread
            timer = threading.Thread(target=end_session_after_grace)
            timer.daemon = True
            timer.start()
        else:
            # Grace period already expired, clean it up
            print(f"Grace period for {call_id} already expired, cleaning up")
            table.delete_item(
                Key={
                    'call_id': call_id
                }
            )

# -------------- FastAPI Application Startup --------------
"""
Example of how to integrate with FastAPI:

@app.on_event("startup")
async def startup_event():
    # Initialize DynamoDB table if it doesn't exist
    try:
        dynamodb.create_table(
            TableName=DYNAMODB_TABLE,
            KeySchema=[
                {
                    'AttributeName': 'call_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'call_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST',
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'ttl'
            }
        )
        print(f"Table {DYNAMODB_TABLE} created successfully")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"Table {DYNAMODB_TABLE} already exists")
        else:
            print(f"Error creating table: {e}")
    
    # Initialize grace periods from DynamoDB
    initialize_grace_periods()
"""