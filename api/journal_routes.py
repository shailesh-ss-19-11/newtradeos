from flask import Blueprint, request, jsonify
from sqlalchemy import text
from core.database import get_engine
from auth.user_auth import auth_required

journal_bp = Blueprint('journal', __name__)


@journal_bp.route('', methods=['GET'])
@auth_required
def list_entries():
    symbol = request.args.get('symbol', '').strip()
    rating = request.args.get('rating', '').strip()

    engine = get_engine()
    with engine.connect() as conn:
        where = 'WHERE user_id = :uid'
        params = {'uid': request.user_id}
        if symbol:
            where += ' AND UPPER(symbol) LIKE :sym'
            params['sym'] = f'%{symbol.upper()}%'
        if rating:
            where += ' AND rating = :rating'
            params['rating'] = int(rating)

        rows = conn.execute(
            text(f"""
                SELECT id, trade_ref, symbol, trade_date, rating, emotion,
                       outcome, notes, tags, created_at, updated_at
                FROM trade_journal {where}
                ORDER BY created_at DESC LIMIT 100
            """),
            params
        ).fetchall()

    return jsonify({'entries': [
        {
            'id':        r.id,
            'tradeRef':  r.trade_ref,
            'symbol':    r.symbol,
            'tradeDate': r.trade_date.isoformat() if r.trade_date else None,
            'rating':    r.rating,
            'emotion':   r.emotion,
            'outcome':   r.outcome,
            'notes':     r.notes,
            'tags':      list(r.tags) if r.tags else [],
            'createdAt': r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]}), 200


@journal_bp.route('', methods=['POST'])
@auth_required
def create_entry():
    data      = request.get_json() or {}
    symbol    = (data.get('symbol') or '').strip().upper()
    trade_ref = (data.get('tradeRef') or '').strip()
    trade_date= data.get('tradeDate')
    rating    = data.get('rating')
    emotion   = (data.get('emotion') or '').strip()
    outcome   = (data.get('outcome') or '').strip()
    notes     = (data.get('notes') or '').strip()
    tags      = data.get('tags', [])

    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                INSERT INTO trade_journal
                    (user_id, trade_ref, symbol, trade_date, rating, emotion, outcome, notes, tags)
                VALUES (:uid, :ref, :sym, :td, :rat, :emo, :out, :notes, :tags)
                RETURNING id, created_at
            """),
            {
                'uid': request.user_id, 'ref': trade_ref or None, 'sym': symbol or None,
                'td': trade_date or None, 'rat': rating or None, 'emo': emotion or None,
                'out': outcome or None, 'notes': notes or None,
                'tags': tags if tags else None,
            }
        ).fetchone()

    return jsonify({'id': row.id, 'createdAt': row.created_at.isoformat()}), 201


@journal_bp.route('/<int:entry_id>', methods=['PUT'])
@auth_required
def update_entry(entry_id):
    data = request.get_json() or {}
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE trade_journal
                SET symbol = :sym, trade_date = :td, rating = :rat, emotion = :emo,
                    outcome = :out, notes = :notes, tags = :tags, updated_at = NOW()
                WHERE id = :id AND user_id = :uid
            """),
            {
                'sym':   (data.get('symbol') or '').strip().upper() or None,
                'td':    data.get('tradeDate') or None,
                'rat':   data.get('rating') or None,
                'emo':   (data.get('emotion') or '').strip() or None,
                'out':   (data.get('outcome') or '').strip() or None,
                'notes': (data.get('notes') or '').strip() or None,
                'tags':  data.get('tags') or None,
                'id':    entry_id, 'uid': request.user_id,
            }
        )
    return jsonify({'message': 'Entry updated'}), 200


@journal_bp.route('/<int:entry_id>', methods=['DELETE'])
@auth_required
def delete_entry(entry_id):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM trade_journal WHERE id = :id AND user_id = :uid"),
            {'id': entry_id, 'uid': request.user_id}
        )
    return jsonify({'message': 'Entry deleted'}), 200
