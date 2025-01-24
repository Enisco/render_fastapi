

from typing import Any

from livestream import end_session, start_session
from models.call_session_model import session_json_to_model
from models.participant_model import participant_json_to_model


def handle_webhook_event(body: Any):
    try:
        event_type = body.get("type")

        if event_type == "call.session_participant_joined":
            participant_data = participant_json_to_model(body)
            call_id = str(participant_data.call_cid).split(':')[-1]
            print("Call ID: ", call_id)
            if "GtubeChurch" in str(participant_data.participant.user.name):
                print("Participant Joined Call: ", participant_data.participant.user.name)
                start_session(call_id)
            else:
                print("User joined, not a church")

        elif event_type == "call.session_participant_left":
            participant_data = participant_json_to_model(body)
            call_id = str(participant_data.call_cid).split(':')[-1]
            print("Call ID: ", call_id)
            if "GtubeChurch" in str(participant_data.participant.user.name):
                print("Participant Left Call: ", participant_data.participant.user.name)
                end_session(call_id)
            else:
                print("User left, not a church")
        
        else:
            print("Other event types received: ", event_type)
    
    except Exception as error:
        print("Error occured: ", error)
