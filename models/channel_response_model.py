from typing import Optional


class ChurchChannelResponse:
    status: Optional[bool]
    message: Optional[str]
    call_id: Optional[str]
    rtmp: Optional[str]
    stream_key: Optional[str]

    def __init__(self, status: Optional[bool], message: Optional[str], call_id: Optional[str], rtmp: Optional[str], stream_key: Optional[str]) -> None:
        self.status = status
        self.message = message
        self.call_id = call_id
        self.rtmp = rtmp
        self.stream_key = stream_key
