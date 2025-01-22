from typing import Optional


class GetTokenResponse:
    status: Optional[bool]
    message: Optional[str]
    user_id: Optional[str]
    token: Optional[str]

    def __init__(self, status: Optional[bool], message: Optional[str], user_id: Optional[str], token: Optional[str]) -> None:
        self.status = status
        self.message = message
        self.user_id = user_id
        self.token = token
