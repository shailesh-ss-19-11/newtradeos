import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from core.database import get_engine
from auth.user_auth import auth_required
from core.subscription_plans import PLANS

subscription_bp = Blueprint('subscription', __name__)


@subscription_bp.route('/plans', methods=['GET'])
def get_plans():
    return jsonify({'plans': PLANS}), 200


@subscription_bp.route('/current', methods=['GET'])
@auth_required
def current_subscription():
    engine = get_engine()
    with engine.connect() as conn:
        user = conn.execute(
            text("SELECT subscription_tier, subscription_expires_at FROM users WHERE id = :id"),
            {'id': request.user_id}
        ).fetchone()

        strategy_count = conn.execute(
            text("SELECT COUNT(*) AS cnt FROM user_strategies WHERE user_id = :uid"),
            {'uid': request.user_id}
        ).fetchone()

        first_of_month = datetime.date.today().replace(day=1)
        backtest_count = conn.execute(
            text("""
                SELECT COUNT(*) AS cnt FROM backtest_runs
                WHERE user_id = :uid AND created_at >= :start
            """),
            {'uid': request.user_id, 'start': first_of_month}
        ).fetchone()

    tier = (user.subscription_tier or 'free') if user else 'free'
    plan = PLANS.get(tier, PLANS['free'])

    return jsonify({
        'tier':    tier,
        'plan':    plan,
        'usage': {
            'strategies':        strategy_count.cnt,
            'backtestsThisMonth': backtest_count.cnt,
        },
        'expiresAt': user.subscription_expires_at.isoformat() if (user and user.subscription_expires_at) else None,
    }), 200


@subscription_bp.route('/upgrade', methods=['POST'])
@auth_required
def upgrade_plan():
    data     = request.get_json() or {}
    new_tier = (data.get('tier') or '').strip().lower()

    if new_tier not in PLANS:
        return jsonify({'error': 'Invalid plan tier'}), 400

    engine = get_engine()
    with engine.begin() as conn:
        expires = None
        if new_tier != 'free':
            expires = datetime.datetime.utcnow() + datetime.timedelta(days=30)

        conn.execute(
            text("""
                UPDATE users
                SET subscription_tier = :tier, subscription_expires_at = :exp
                WHERE id = :id
            """),
            {'tier': new_tier, 'exp': expires, 'id': request.user_id}
        )

        updated = conn.execute(
            text("SELECT subscription_tier, subscription_expires_at FROM users WHERE id = :id"),
            {'id': request.user_id}
        ).fetchone()

    return jsonify({
        'message':   f'Plan updated to {PLANS[new_tier]["name"]}',
        'tier':      updated.subscription_tier,
        'expiresAt': updated.subscription_expires_at.isoformat() if updated.subscription_expires_at else None,
    }), 200
