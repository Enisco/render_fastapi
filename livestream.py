import time
import stream

from getstream import Stream
from getstream.models import CallRequest, CallSettingsRequest
from getstream.models import RecordSettingsRequest
from getstream.models import UserRequest

from utils.string_utils import generate_unique_string

api_key = "gcwwb5wde69h"
api_secret = "mdmaxcad9yqbvp39yc45h39b2ebjcjwzu7pevfpnk7jnxa4dnkvraxpntc643ztm"

call_type = "livestream"
# admin_call_role = 'gtubeadmin'
admin_call_role = "admin"
user_call_role = "user"
live_recording_storage = "stream-s3"


# ----------------------- Generate Token for User --------------------------


def get_user_token(user_id):
    try:
        client = stream.connect(api_key, api_secret)
        user_token = client.create_user_token(user_id)
        print("User Token generated for " + user_id + ": " + user_token)

        response = {
            "status": False,
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
        # TODO: Call endpoint to update event on Backend

    except Exception as error:
        print("\n\n Error going live call: ", error)
        handle_exception(error)


# -------------- End Session: Stop Live and Stop Recording  --------------


def end_session(call_id):
    try:
        client = Stream(api_key=api_key, api_secret=api_secret)
        call = client.video.call(call_type=call_type, id=call_id)

        stopLive = call.stop_live()
        stopRecording = call.stop_recording()
        # TODO: Eject all watchers, close live and end session
        print(f"Stopped Live Call and Recording")

    except Exception as error:
        handle_exception(error)


# -------------- Upload Video Recording: Get Recording and Upload to Church Videos --------------


def upload_recording(call_id):
    try:
        time.sleep(30)  # Delay for 30 seconds
        client = Stream(api_key=api_key, api_secret=api_secret)
        call = client.video.call(call_type=call_type, id=call_id)

        list_recordings = call.list_recordings()
        print("\n\n List of recordings: ", list_recordings.data)
        recording_url = f"https://gospeltube533267336299.s3.us-east-2.amazonaws.com/{live_recording_storage}/{call_type}_{call_id}/{list_recordings.data.recordings[0].filename}"
        print("\n\n ------ Recordings URL: ", recording_url)

        # TODO: Call endpoint to upload recorded livestream here

    except Exception as error:
        handle_exception(error)


# ---------------------------Error Handlers------------------------------------


def handle_exception(error):
    # Handle all exceptions
    response = {"status": False, "message": str(error)}
    print("Error occured: ", str(response))
    return response, 500
