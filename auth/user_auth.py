import os
import datetime
from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from functools import wraps
from flask import request, jsonify
from sqlalchemy import text
from core.database import get_engine

SECRET_KEY = os.getenv('JWT_SECRET', 'tradeos-jwt-secret-key-change-in-production')
TOKEN_MAX_AGE = 7 * 24 * 3600  # 7 days in seconds

_serializer = URLSafeTimedSerializer(SECRET_KEY)


def register_user(email: str, name: str, password: str) -> dict:
    engine = get_engine()
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {'email': email.lower().strip()}
        ).fetchone()
        if existing:
            return {'error': 'Email already registered'}

        password_hash = generate_password_hash(password)
        row = conn.execute(
            text("""
                INSERT INTO users (email, name, password_hash)
                VALUES (:email, :name, :pw_hash)
                RETURNING id, email, name, subscription_tier
            """),
            {'email': email.lower().strip(), 'name': name.strip(), 'pw_hash': password_hash}
        ).fetchone()

    token = _create_token(row.id, row.email)
    return {
        'token': token,
        'user': {
            'id':                row.id,
            'email':             row.email,
            'name':              row.name,
            'subscription_tier': row.subscription_tier,
        }
    }


def login_user(email: str, password: str) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, email, name, password_hash, subscription_tier, is_active FROM users WHERE email = :email"),
            {'email': email.lower().strip()}
        ).fetchone()

    if not row:
        return {'error': 'Invalid email or password'}
    if not row.is_active:
        return {'error': 'Account is inactive'}
    if not check_password_hash(row.password_hash, password):
        return {'error': 'Invalid email or password'}

    token = _create_token(row.id, row.email)
    return {
        'token': token,
        'user': {
            'id':                row.id,
            'email':             row.email,
            'name':              row.name,
            'subscription_tier': row.subscription_tier,
        }
    }


def get_user_by_id(user_id: int) -> Optional[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, email, name, subscription_tier FROM users WHERE id = :id"),
            {'id': user_id}
        ).fetchone()
    if not row:
        return None
    return {'id': row.id, 'email': row.email, 'name': row.name, 'subscription_tier': row.subscription_tier}


def _create_token(user_id: int, email: str) -> str:
    payload = {'user_id': user_id, 'email': email}
    return _serializer.dumps(payload, salt='auth-token')


def _decode_token(token: str) -> dict:
    payload = _serializer.loads(token, salt='auth-token', max_age=TOKEN_MAX_AGE)
    return payload


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '').strip()
        if not token:
            return jsonify({'error': 'Authentication required'}), 401
        try:
            payload = _decode_token(token)
            request.user_id    = payload['user_id']
            request.user_email = payload['email']
        except SignatureExpired:
            return jsonify({'error': 'Session expired, please login again'}), 401
        except (BadSignature, Exception):
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated
