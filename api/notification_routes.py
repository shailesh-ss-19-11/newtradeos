from flask import Blueprint, request, jsonify
from sqlalchemy import text
from core.database import get_engine
from auth.user_auth import auth_required

notification_bp = Blueprint('notifications', __name__)


def push_notification(user_id: int, type_: str, title: str, message: str = '', data: dict = None):
    """Helper: insert a notification for a user (call from any route/worker)."""
    import json
    engine = get_engine()
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO notifications (user_id, type, title, message, data)
                    VALUES (:uid, :type, :title, :msg, CAST(:data AS jsonb))
                """),
                {
                    'uid': user_id, 'type': type_, 'title': title,
                    'msg': message, 'data': json.dumps(data or {}),
                }
            )
    except Exception:
        pass


@notification_bp.route('', methods=['GET'])
@auth_required
def list_notifications():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, type, title, message, data, is_read, created_at
                FROM notifications
                WHERE user_id = :uid
                ORDER BY created_at DESC LIMIT 50
            """),
            {'uid': request.user_id}
        ).fetchall()

        unread = conn.execute(
            text("SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = :uid AND is_read = FALSE"),
            {'uid': request.user_id}
        ).fetchone()

    return jsonify({
        'unreadCount': unread.cnt,
        'notifications': [
            {
                'id':        r.id,
                'type':      r.type,
                'title':     r.title,
                'message':   r.message,
                'data':      r.data,
                'isRead':    r.is_read,
                'createdAt': r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }), 200


@notification_bp.route('/read-all', methods=['POST'])
@auth_required
def mark_all_read():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE notifications SET is_read = TRUE WHERE user_id = :uid"),
            {'uid': request.user_id}
        )
    return jsonify({'message': 'All notifications marked read'}), 200


@notification_bp.route('/<int:notif_id>/read', methods=['POST'])
@auth_required
def mark_read(notif_id):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE notifications SET is_read = TRUE WHERE id = :id AND user_id = :uid"),
            {'id': notif_id, 'uid': request.user_id}
        )
    return jsonify({'message': 'Marked read'}), 200


@notification_bp.route('/<int:notif_id>', methods=['DELETE'])
@auth_required
def delete_notification(notif_id):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM notifications WHERE id = :id AND user_id = :uid"),
            {'id': notif_id, 'uid': request.user_id}
        )
    return jsonify({'message': 'Deleted'}), 200
