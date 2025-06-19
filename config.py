import os
import configparser
from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    telegram_token: str = ""
    xui_api_url: str = ""
    xui_login: str = ""
    xui_psw: str = ""
    xui_inbound_id: int = 2
    vpn_backend_type: str = "api"
    vpn_config_path: str = "config.json"
    admin_ids: List[int] = field(default_factory=list)
    qr_logo_path: str = "logo.png"


def _parse_admin_ids(value: str) -> List[int]:
    return [int(x) for x in value.split(',') if x.strip()]


def load_config(path: str = "config.ini") -> Config:
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    sec = parser["bot"] if parser.has_section("bot") else {}
    token = os.getenv("TELEGRAM_TOKEN") or sec.get("telegram_token", "")
    xui_api_url = os.getenv("XUI_API_URL") or sec.get("xui_api_url", "")
    xui_login = os.getenv("XUI_LOGIN") or sec.get("xui_login", "")
    xui_psw = os.getenv("XUI_PSW") or sec.get("xui_psw", "")
    inbound_id = int(os.getenv("XUI_INBOUND_ID") or sec.get("xui_inbound_id", "2"))
    backend = os.getenv("VPN_BACKEND_TYPE") or sec.get("vpn_backend_type", "api")
    cfg_path = os.getenv("VPN_CONFIG_PATH") or sec.get("vpn_config_path", "config.json")
    admin_ids = os.getenv("ADMIN_IDS") or sec.get("admin_ids", "")
    qr_logo = sec.get("qr_logo_path", "logo.png")
    return Config(
        telegram_token=token,
        xui_api_url=xui_api_url,
        xui_login=xui_login,
        xui_psw=xui_psw,
        xui_inbound_id=inbound_id,
        vpn_backend_type=backend,
        vpn_config_path=cfg_path,
        admin_ids=_parse_admin_ids(admin_ids),
        qr_logo_path=qr_logo,
    )


config = load_config()
