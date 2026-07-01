import json
import os
from datetime import datetime
import pytz
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
TOKEN_FILE = os.path.join(DATA_DIR, 'token.json')
IST = pytz.timezone('Asia/Kolkata')


def save_token(access_token: str) -> None:
    now_ist = datetime.now(IST)
    data = {
        "access_token": access_token,
        "created_date": now_ist.strftime("%Y-%m-%d"),
        "created_at": now_ist.isoformat()
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TOKEN_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_token() -> str | None:
    # Env var takes priority — useful for manually injecting today's token
    env_token = os.getenv('FYERS_ACCESS_TOKEN', '').strip()
    if env_token:
        return env_token
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, 'r') as f:
            data = json.load(f)
        return data.get('access_token')
    except Exception:
        return None


def is_token_valid() -> bool:
    # Env var is always treated as valid (manually set by operator)
    if os.getenv('FYERS_ACCESS_TOKEN', '').strip():
        return True
    if not os.path.exists(TOKEN_FILE):
        return False
    try:
        with open(TOKEN_FILE, 'r') as f:
            data = json.load(f)
        if not data.get('access_token'):
            return False
        today = datetime.now(IST).strftime("%Y-%m-%d")
        return data.get('created_date') == today
    except Exception:
        return False


def get_fyers_model(access_token: str):
    client_id = os.getenv('FYERS_CLIENT_ID')
    fyers = fyersModel.FyersModel(
        client_id=client_id,
        is_async=False,
        token=access_token,
        log_path=''
    )
    return fyers
