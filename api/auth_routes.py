from flask import Blueprint, request, jsonify
from auth.user_auth import register_user, login_user, get_user_by_id, auth_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email    = (data.get('email') or '').strip()
    name     = (data.get('name') or '').strip()
    password = (data.get('password') or '').strip()

    if not email or not name or not password:
        return jsonify({'error': 'Email, name and password are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if '@' not in email:
        return jsonify({'error': 'Invalid email address'}), 400

    result = register_user(email, name, password)
    if 'error' in result:
        return jsonify(result), 409
    return jsonify(result), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email    = (data.get('email') or '').strip()
    password = (data.get('password') or '').strip()

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    result = login_user(email, password)
    if 'error' in result:
        return jsonify(result), 401
    return jsonify(result), 200


@auth_bp.route('/me', methods=['GET'])
@auth_required
def me():
    user = get_user_by_id(request.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user}), 200
