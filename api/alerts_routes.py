from flask import Blueprint, request, jsonify
from sqlalchemy import text
from core.database import get_engine
from auth.user_auth import auth_required

alerts_bp = Blueprint('alerts', __name__)


@alerts_bp.route('', methods=['GET'])
@auth_required
def list_alerts():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, symbol, display_symbol, condition, target_price,
                       is_active, triggered_at, created_at
                FROM price_alerts
                WHERE user_id = :uid
                ORDER BY created_at DESC
            """),
            {'uid': request.user_id}
        ).fetchall()

    return jsonify({'alerts': [
        {
            'id':            r.id,
            'symbol':        r.symbol,
            'displaySymbol': r.display_symbol or r.symbol,
            'condition':     r.condition,
            'targetPrice':   float(r.target_price),
            'isActive':      r.is_active,
            'triggeredAt':   r.triggered_at.isoformat() if r.triggered_at else None,
            'createdAt':     r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]}), 200


@alerts_bp.route('', methods=['POST'])
@auth_required
def create_alert():
    data    = request.get_json() or {}
    symbol  = (data.get('symbol') or '').strip().upper()
    display = (data.get('displaySymbol') or symbol).strip()
    cond    = (data.get('condition') or '').strip().lower()
    target  = float(data.get('targetPrice', 0))

    if not symbol or cond not in ('above', 'below') or target <= 0:
        return jsonify({'error': 'symbol, condition (above/below) and targetPrice required'}), 400

    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                INSERT INTO price_alerts (user_id, symbol, display_symbol, condition, target_price)
                VALUES (:uid, :sym, :disp, :cond, :price)
                RETURNING id
            """),
            {'uid': request.user_id, 'sym': symbol, 'disp': display, 'cond': cond, 'price': target}
        ).fetchone()

    return jsonify({'id': row.id, 'message': 'Alert created'}), 201


@alerts_bp.route('/<int:alert_id>', methods=['DELETE'])
@auth_required
def delete_alert(alert_id):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM price_alerts WHERE id = :id AND user_id = :uid"),
            {'id': alert_id, 'uid': request.user_id}
        )
    return jsonify({'message': 'Alert deleted'}), 200


@alerts_bp.route('/<int:alert_id>/toggle', methods=['POST'])
@auth_required
def toggle_alert(alert_id):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE price_alerts
                SET is_active = NOT is_active
                WHERE id = :id AND user_id = :uid
            """),
            {'id': alert_id, 'uid': request.user_id}
        )
    return jsonify({'message': 'Alert toggled'}), 200
