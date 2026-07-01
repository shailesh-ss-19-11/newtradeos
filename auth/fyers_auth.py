import os
import base64
import requests
from dotenv import load_dotenv
from fyers_apiv3 import fyersModel
from auth.token_manager import save_token, load_token, is_token_valid, get_fyers_model

load_dotenv()

_fyers_client = None


def get_fyers_client():
    global _fyers_client

    if is_token_valid():
        token = load_token()
        if token:
            _fyers_client = get_fyers_model(token)
            return _fyers_client

    try:
        access_token = _mobile_otp_login()
        if access_token:
            save_token(access_token)
            _fyers_client = get_fyers_model(access_token)
            return _fyers_client
    except Exception as e:
        print(f"[FyersAuth] Login failed: {e}")
        return None


def _mobile_otp_login() -> str:
    client_id = os.getenv('FYERS_CLIENT_ID')
    secret_key = os.getenv('FYERS_SECRET_KEY')
    redirect_uri = os.getenv('FYERS_REDIRECT_URI')
    pin = os.getenv('FYERS_PIN')

    if not all([client_id, secret_key, redirect_uri, pin]):
        raise Exception("Missing FYERS_CLIENT_ID / FYERS_SECRET_KEY / FYERS_REDIRECT_URI / FYERS_PIN in .env")

    headers = {'Content-Type': 'application/json'}

    # Step 1: Prompt for Fyers client ID or registered mobile number
    fy_id = input("Enter your Fyers Client ID or registered mobile number: ").strip()
    if not fy_id:
        raise Exception("Fyers ID / mobile number is required")

    # Step 2: Trigger OTP to registered mobile
    print("[FyersAuth] Sending OTP to your registered mobile...")
    response = requests.post(
        'https://api-t2.fyers.in/vagator/v2/send_login_otp_v2',
        json={"fy_id": fy_id, "app_id": "2"},
        headers=headers,
        timeout=10
    )
    resp_data = response.json()
    if resp_data.get('s') == 'error' or 'request_key' not in resp_data:
        raise Exception(f"Failed to send OTP: {resp_data}")
    request_key = resp_data['request_key']
    print("[FyersAuth] OTP sent. Check your mobile.")

    # Step 3: User enters the OTP received on mobile
    otp = input("Enter the OTP received on your mobile: ").strip()
    if not otp:
        raise Exception("OTP is required")

    response = requests.post(
        'https://api-t2.fyers.in/vagator/v2/verify_otp',
        json={"request_key": request_key, "otp": otp},
        headers=headers,
        timeout=10
    )
    resp_data = response.json()
    if resp_data.get('s') == 'error' or 'request_key' not in resp_data:
        raise Exception(f"OTP verification failed: {resp_data}")
    request_key = resp_data['request_key']

    # Step 4: Verify PIN (base64 encoded)
    encoded_pin = base64.b64encode(pin.encode()).decode()
    response = requests.post(
        'https://api-t2.fyers.in/vagator/v2/verify_pin_v2',
        json={"request_key": request_key, "identity_type": "pin", "identifier": encoded_pin},
        headers=headers,
        timeout=10
    )
    resp_data = response.json()
    if resp_data.get('s') == 'error':
        raise Exception(f"PIN verification failed: {resp_data}")
    step4_token = resp_data.get('data', {}).get('access_token', '')

    # Step 5: Get auth code
    app_id_without_suffix = client_id.split('-')[0] if '-' in client_id else client_id
    auth_headers = {**headers, 'Authorization': f'Bearer {step4_token}'}
    response = requests.post(
        'https://api.fyers.in/api/v2/token',
        json={
            "fyers_id": fy_id,
            "app_id": app_id_without_suffix,
            "redirect_uri": redirect_uri,
            "appType": "100",
            "code_challenge": "",
            "state": "trading_bot",
            "scope": "",
            "nonce": "",
            "response_type": "code",
            "create_cookie": True
        },
        headers=auth_headers,
        timeout=10
    )
    resp_data = response.json()
    if resp_data.get('s') == 'error' or 'code' not in resp_data:
        raise Exception(f"Failed to get auth code: {resp_data}")
    auth_code = resp_data['code']

    # Step 6: Exchange auth code for access token
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type='code',
        grant_type='authorization_code'
    )
    session.set_token(auth_code)
    token_response = session.generate_token()
    access_token = token_response.get('access_token')
    if not access_token:
        raise Exception(f"Token generation failed: {token_response}")

    print(f"[FyersAuth] Login successful for {fy_id}")
    return access_token


def refresh_client_if_needed(fyers_client):
    if fyers_client is None:
        return get_fyers_client()

    test = fyers_client.get_profile()
    if test.get('s') == 'error' and 'token' in str(test.get('message', '')).lower():
        print("[FyersAuth] Token expired, refreshing...")
        return get_fyers_client()

    return fyers_client


if __name__ == '__main__':
    print("=== Fyers Authentication (Mobile OTP) ===")
    client = get_fyers_client()
    if client:
        profile = client.get_profile()
        print(f"Logged in as: {profile.get('data', {}).get('name', 'Unknown')}")
    else:
        print("Authentication failed.")
