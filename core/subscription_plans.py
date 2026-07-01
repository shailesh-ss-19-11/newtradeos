from typing import Optional

PLANS = {
    'free': {
        'name':                 'Free',
        'price_inr':            0,
        'max_strategies':       2,
        'backtests_per_month':  10,
        'allowed_universes':    ['NIFTY50', 'INDIVIDUAL'],
        'max_period_months':    12,
        'features': [
            '2 saved strategies',
            '10 backtests / month',
            'Nifty 50 universe',
            '1 year history',
            'Basic analytics',
        ],
    },
    'basic': {
        'name':                 'Basic',
        'price_inr':            499,
        'max_strategies':       10,
        'backtests_per_month':  100,
        'allowed_universes':    ['NIFTY50', 'NIFTY100', 'NIFTY150', 'NIFTY200', 'INDIVIDUAL'],
        'max_period_months':    24,
        'features': [
            '10 saved strategies',
            '100 backtests / month',
            'Up to Nifty 200 universe',
            '2 year history',
            'Advanced analytics',
            'Strategy performance tracking',
        ],
    },
    'pro': {
        'name':                 'Pro',
        'price_inr':            999,
        'max_strategies':       None,
        'backtests_per_month':  None,
        'allowed_universes':    ['NIFTY50', 'NIFTY100', 'NIFTY150', 'NIFTY200', 'NIFTY500', 'INDIVIDUAL'],
        'max_period_months':    36,
        'features': [
            'Unlimited strategies',
            'Unlimited backtests',
            'Full Nifty 500 universe',
            '3 year history',
            'Full analytics suite',
            'Strategy performance tracking',
            'Priority support',
        ],
    },
}


def get_plan(tier: str) -> dict:
    return PLANS.get(tier, PLANS['free'])


def check_strategy_limit(user_id: int, tier: str) -> tuple:
    """Returns (allowed: bool, error_msg: str)"""
    plan = get_plan(tier)
    max_s = plan['max_strategies']
    if max_s is None:
        return True, ''

    from core.database import get_engine
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT COUNT(*) AS cnt FROM user_strategies WHERE user_id = :uid"),
            {'uid': user_id}
        ).fetchone()

    if row.cnt >= max_s:
        return False, (
            f"Strategy limit reached ({max_s} on {plan['name']} plan). "
            "Upgrade to add more strategies."
        )
    return True, ''


def check_backtest_limit(user_id: int, tier: str) -> tuple:
    """Returns (allowed: bool, error_msg: str)"""
    plan = get_plan(tier)
    max_bt = plan['backtests_per_month']
    if max_bt is None:
        return True, ''

    from core.database import get_engine
    from sqlalchemy import text
    from datetime import date
    engine = get_engine()
    with engine.connect() as conn:
        first_of_month = date.today().replace(day=1)
        row = conn.execute(
            text("""
                SELECT COUNT(*) AS cnt FROM backtest_runs
                WHERE user_id = :uid AND created_at >= :start
            """),
            {'uid': user_id, 'start': first_of_month}
        ).fetchone()

    if row.cnt >= max_bt:
        return False, (
            f"Monthly backtest limit reached ({max_bt}/month on {plan['name']} plan). "
            "Upgrade for more backtests."
        )
    return True, ''


def get_user_tier(user_id: int) -> str:
    from core.database import get_engine
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT subscription_tier FROM users WHERE id = :id"),
            {'id': user_id}
        ).fetchone()
    return (row.subscription_tier or 'free') if row else 'free'
