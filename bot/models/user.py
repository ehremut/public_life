from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    user_id: int
    username: str
    role: str
    status: str
    request_days: int = 0
    days: int = 0
    remark: str = ""
    xui_id: Optional[str] = None
    config_counter: int = 0
