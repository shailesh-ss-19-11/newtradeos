from flask import Blueprint, request, jsonify
from sqlalchemy import text
from core.database import get_engine
from auth.user_auth import auth_required

paper_bp = Blueprint('paper', __name__)


def _ensure_portfolio(conn, user_id: int) -> int:
    """Return the user's active paper portfolio id, creating one if needed."""
    row = conn.execute(
        text("SELECT id FROM paper_portfolios WHERE user_id = :uid AND is_active = TRUE LIMIT 1"),
        {'uid': user_id}
    ).fetchone()
    if row:
        return row.id
    result = conn.execute(
        text("""
            INSERT INTO paper_portfolios (user_id, name, initial_capital, available_capital)
            VALUES (:uid, 'My Paper Portfolio', 100000, 100000)
            RETURNING id
        """),
        {'uid': user_id}
    ).fetchone()
    return result.id


@paper_bp.route('/portfolio', methods=['GET'])
@auth_required
def get_portfolio():
    engine = get_engine()
    with engine.connect() as conn:
        port = conn.execute(
            text("SELECT * FROM paper_portfolios WHERE user_id = :uid AND is_active = TRUE LIMIT 1"),
            {'uid': request.user_id}
        ).fetchone()

        if not port:
            return jsonify({'portfolio': None, 'positions': [], 'history': []}), 200

        positions = conn.execute(
            text("""
                SELECT * FROM paper_trades
                WHERE portfolio_id = :pid AND status = 'open'
                ORDER BY opened_at DESC
            """),
            {'pid': port.id}
        ).fetchall()

        history = conn.execute(
            text("""
                SELECT * FROM paper_trades
                WHERE portfolio_id = :pid AND status = 'closed'
                ORDER BY closed_at DESC LIMIT 50
            """),
            {'pid': port.id}
        ).fetchall()

    def trade_dict(t):
        cost = t.entry_price * t.quantity
        lp   = t.last_price or t.entry_price
        pnl  = (lp - t.entry_price) * t.quantity if t.status == 'open' else (t.pnl or 0)
        return {
            'id': t.id, 'symbol': t.symbol, 'strategyName': t.strategy_name,
            'side': t.side, 'entryPrice': float(t.entry_price), 'quantity': t.quantity,
            'slPct': float(t.sl_pct or 0), 't1Pct': float(t.t1_pct or 0),
            't2Pct': float(t.t2_pct or 0), 't3Pct': float(t.t3_pct or 0),
            'lastPrice': float(lp), 'exitPrice': float(t.exit_price or 0),
            'exitType': t.exit_type, 'status': t.status,
            'pnl': round(pnl, 2), 'pnlPct': round(pnl / max(cost, 1) * 100, 2),
            'notes': t.notes, 'openedAt': t.opened_at.isoformat() if t.opened_at else None,
            'closedAt': t.closed_at.isoformat() if t.closed_at else None,
        }

    open_pnl = sum((t.last_price or t.entry_price - t.entry_price) * t.quantity for t in positions)

    return jsonify({
        'portfolio': {
            'id': port.id, 'name': port.name,
            'initialCapital':   float(port.initial_capital),
            'availableCapital': float(port.available_capital),
            'openPnl':          round(float(open_pnl), 2),
        },
        'positions': [trade_dict(t) for t in positions],
        'history':   [trade_dict(t) for t in history],
    }), 200


@paper_bp.route('/trade', methods=['POST'])
@auth_required
def open_trade():
    data = request.get_json() or {}
    symbol    = (data.get('symbol') or '').strip().upper()
    qty       = int(data.get('quantity', 1))
    price     = float(data.get('entryPrice', 0))
    sl_pct    = float(data.get('slPct', 2))
    t1_pct    = float(data.get('t1Pct', 3))
    t2_pct    = float(data.get('t2Pct', 5))
    t3_pct    = float(data.get('t3Pct', 7))
    strat     = (data.get('strategyName') or '').strip()
    notes     = (data.get('notes') or '').strip()

    if not symbol or qty < 1 or price <= 0:
        return jsonify({'error': 'symbol, quantity and entryPrice are required'}), 400

    cost = price * qty
    engine = get_engine()
    with engine.begin() as conn:
        port_id = _ensure_portfolio(conn, request.user_id)
        port    = conn.execute(
            text("SELECT available_capital FROM paper_portfolios WHERE id = :id"),
            {'id': port_id}
        ).fetchone()

        if float(port.available_capital) < cost:
            return jsonify({'error': f'Insufficient capital. Need ₹{cost:,.0f}, have ₹{float(port.available_capital):,.0f}'}), 400

        conn.execute(
            text("UPDATE paper_portfolios SET available_capital = available_capital - :cost WHERE id = :id"),
            {'cost': cost, 'id': port_id}
        )
        row = conn.execute(
            text("""
                INSERT INTO paper_trades
                    (portfolio_id, user_id, symbol, strategy_name, entry_price, quantity,
                     sl_pct, t1_pct, t2_pct, t3_pct, last_price, status, notes)
                VALUES (:pid, :uid, :sym, :sname, :ep, :qty, :sl, :t1, :t2, :t3, :ep, 'open', :notes)
                RETURNING id
            """),
            {'pid': port_id, 'uid': request.user_id, 'sym': symbol, 'sname': strat,
             'ep': price, 'qty': qty, 'sl': sl_pct, 't1': t1_pct, 't2': t2_pct, 't3': t3_pct,
             'notes': notes}
        ).fetchone()

    return jsonify({'id': row.id, 'message': 'Paper trade opened'}), 201


@paper_bp.route('/trade/<int:trade_id>/close', methods=['POST'])
@auth_required
def close_trade(trade_id):
    data       = request.get_json() or {}
    exit_price = float(data.get('exitPrice', 0))
    exit_type  = (data.get('exitType') or 'MANUAL').strip().upper()

    if exit_price <= 0:
        return jsonify({'error': 'exitPrice is required'}), 400

    engine = get_engine()
    with engine.begin() as conn:
        trade = conn.execute(
            text("SELECT * FROM paper_trades WHERE id = :id AND user_id = :uid AND status = 'open'"),
            {'id': trade_id, 'uid': request.user_id}
        ).fetchone()

        if not trade:
            return jsonify({'error': 'Trade not found or already closed'}), 404

        pnl      = (exit_price - trade.entry_price) * trade.quantity
        pnl_pct  = pnl / (trade.entry_price * trade.quantity) * 100
        proceeds = exit_price * trade.quantity

        conn.execute(
            text("""
                UPDATE paper_trades
                SET exit_price = :ep, exit_type = :et, status = 'closed',
                    pnl = :pnl, pnl_pct = :pp, closed_at = NOW()
                WHERE id = :id
            """),
            {'ep': exit_price, 'et': exit_type, 'pnl': pnl, 'pp': pnl_pct, 'id': trade_id}
        )
        conn.execute(
            text("""
                UPDATE paper_portfolios
                SET available_capital = available_capital + :proceeds
                WHERE id = :pid
            """),
            {'proceeds': proceeds, 'pid': trade.portfolio_id}
        )

    return jsonify({'message': 'Trade closed', 'pnl': round(pnl, 2), 'pnlPct': round(pnl_pct, 2)}), 200


@paper_bp.route('/trade/<int:trade_id>/price', methods=['PATCH'])
@auth_required
def update_price(trade_id):
    data  = request.get_json() or {}
    price = float(data.get('lastPrice', 0))
    if price <= 0:
        return jsonify({'error': 'lastPrice required'}), 400

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE paper_trades SET last_price = :p
                WHERE id = :id AND user_id = :uid AND status = 'open'
            """),
            {'p': price, 'id': trade_id, 'uid': request.user_id}
        )
    return jsonify({'message': 'Price updated'}), 200


@paper_bp.route('/portfolio/reset', methods=['POST'])
@auth_required
def reset_portfolio():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE paper_trades SET status = 'closed', closed_at = NOW() WHERE user_id = :uid AND status = 'open'"),
            {'uid': request.user_id}
        )
        conn.execute(
            text("""
                UPDATE paper_portfolios
                SET available_capital = initial_capital
                WHERE user_id = :uid AND is_active = TRUE
            """),
            {'uid': request.user_id}
        )
    return jsonify({'message': 'Portfolio reset'}), 200
