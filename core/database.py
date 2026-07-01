import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

load_dotenv()

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = os.getenv('DATABASE_URL', 'postgresql://localhost/trading_system')
        _engine = create_engine(url, poolclass=QueuePool, pool_size=5, max_overflow=10, future=True)
    return _engine


def init_db():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id            VARCHAR(50) PRIMARY KEY,
                symbol              VARCHAR(50),
                display_symbol      VARCHAR(50),
                type                VARCHAR(10),
                status              VARCHAR(20)     DEFAULT 'ACTIVE',
                entry_price         DECIMAL(12,4),
                stop_loss           DECIMAL(12,4),
                stop_loss_percent   DECIMAL(8,4),
                target1             DECIMAL(12,4),
                target2             DECIMAL(12,4),
                target3             DECIMAL(12,4),
                target4             DECIMAL(12,4),
                target5             DECIMAL(12,4),
                target1_percent     DECIMAL(8,4),
                target2_percent     DECIMAL(8,4),
                target3_percent     DECIMAL(8,4),
                target1_hit         BOOLEAN         DEFAULT FALSE,
                target2_hit         BOOLEAN         DEFAULT FALSE,
                target3_hit         BOOLEAN         DEFAULT FALSE,
                target_hit_log      JSONB           DEFAULT '[]',
                position_size       INTEGER,
                capital_required    DECIMAL(12,2),
                max_loss            DECIMAL(12,2),
                risk_reward         DECIMAL(8,4),
                atr                 DECIMAL(12,4),
                confidence          VARCHAR(20),
                votes               INTEGER,
                multi_tf_alignment  VARCHAR(20),
                strategies          JSONB           DEFAULT '{}',
                options_data        JSONB,
                is_profit           BOOLEAN,
                profit_loss         DECIMAL(12,2),
                profit_loss_pct     DECIMAL(8,4),
                exit_price          DECIMAL(12,4),
                exit_time           TIMESTAMPTZ,
                exit_reason         VARCHAR(50),
                signal_time         TIMESTAMPTZ,
                trade_date          DATE,
                telegram_msg_id     INTEGER,
                notes               TEXT,
                created_at          TIMESTAMPTZ     DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS errors (
                id          SERIAL PRIMARY KEY,
                module      VARCHAR(100),
                message     TEXT,
                symbol      VARCHAR(50),
                timestamp   TIMESTAMPTZ DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                id          SERIAL PRIMARY KEY,
                symbol      VARCHAR(50) UNIQUE,
                results     JSONB,
                run_date    DATE,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id                    SERIAL PRIMARY KEY,
                email                 VARCHAR(255) UNIQUE NOT NULL,
                name                  VARCHAR(255) NOT NULL,
                password_hash         VARCHAR(255) NOT NULL,
                is_active             BOOLEAN         DEFAULT TRUE,
                subscription_tier     VARCHAR(20)     DEFAULT 'free',
                subscription_expires_at TIMESTAMPTZ,
                created_at            TIMESTAMPTZ     DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_strategies (
                id              SERIAL PRIMARY KEY,
                user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
                name            VARCHAR(255)    NOT NULL,
                description     TEXT,
                strategy_type   VARCHAR(100)    NOT NULL,
                parameters      JSONB           DEFAULT '{}',
                timeframe       VARCHAR(10)     DEFAULT 'D',
                is_active       BOOLEAN         DEFAULT TRUE,
                created_at      TIMESTAMPTZ     DEFAULT NOW(),
                updated_at      TIMESTAMPTZ     DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS backtest_runs (
                id              SERIAL PRIMARY KEY,
                user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
                strategy_id     INTEGER REFERENCES user_strategies(id) ON DELETE SET NULL,
                config          JSONB,
                status          VARCHAR(20)     DEFAULT 'pending',
                results         JSONB,
                error_message   TEXT,
                created_at      TIMESTAMPTZ     DEFAULT NOW(),
                completed_at    TIMESTAMPTZ
            )
        """))

        # ── Paper Trading ──────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS paper_portfolios (
                id                  SERIAL PRIMARY KEY,
                user_id             INTEGER REFERENCES users(id) ON DELETE CASCADE,
                name                VARCHAR(255)    NOT NULL DEFAULT 'My Paper Portfolio',
                initial_capital     DECIMAL(15,2)   NOT NULL DEFAULT 100000,
                available_capital   DECIMAL(15,2)   NOT NULL DEFAULT 100000,
                is_active           BOOLEAN         DEFAULT TRUE,
                created_at          TIMESTAMPTZ     DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                id              SERIAL PRIMARY KEY,
                portfolio_id    INTEGER REFERENCES paper_portfolios(id) ON DELETE CASCADE,
                user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
                symbol          VARCHAR(50)     NOT NULL,
                strategy_name   VARCHAR(255),
                side            VARCHAR(4)      NOT NULL DEFAULT 'BUY',
                entry_price     DECIMAL(15,4)   NOT NULL,
                quantity        INTEGER         NOT NULL,
                sl_pct          DECIMAL(5,2),
                t1_pct          DECIMAL(5,2),
                t2_pct          DECIMAL(5,2),
                t3_pct          DECIMAL(5,2),
                last_price      DECIMAL(15,4),
                exit_price      DECIMAL(15,4),
                exit_type       VARCHAR(20),
                status          VARCHAR(20)     DEFAULT 'open',
                pnl             DECIMAL(15,4),
                pnl_pct         DECIMAL(7,4),
                notes           TEXT,
                opened_at       TIMESTAMPTZ     DEFAULT NOW(),
                closed_at       TIMESTAMPTZ
            )
        """))

        # ── Trade Journal ──────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trade_journal (
                id          SERIAL PRIMARY KEY,
                user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
                trade_ref   VARCHAR(100),
                symbol      VARCHAR(50),
                trade_date  DATE,
                rating      INTEGER     CHECK (rating BETWEEN 1 AND 5),
                emotion     VARCHAR(50),
                outcome     VARCHAR(20),
                notes       TEXT,
                tags        TEXT[],
                created_at  TIMESTAMPTZ DEFAULT NOW(),
                updated_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """))

        # ── Notifications ──────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notifications (
                id          SERIAL PRIMARY KEY,
                user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
                type        VARCHAR(50)     NOT NULL,
                title       VARCHAR(255)    NOT NULL,
                message     TEXT,
                data        JSONB,
                is_read     BOOLEAN         DEFAULT FALSE,
                created_at  TIMESTAMPTZ     DEFAULT NOW()
            )
        """))

        # ── Price Alerts ───────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id              SERIAL PRIMARY KEY,
                user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
                symbol          VARCHAR(50)     NOT NULL,
                display_symbol  VARCHAR(100),
                condition       VARCHAR(10)     NOT NULL,
                target_price    DECIMAL(15,4)   NOT NULL,
                is_active       BOOLEAN         DEFAULT TRUE,
                triggered_at    TIMESTAMPTZ,
                created_at      TIMESTAMPTZ     DEFAULT NOW()
            )
        """))

        # ── Strategy Marketplace ───────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS marketplace_strategies (
                id              SERIAL PRIMARY KEY,
                user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
                strategy_id     INTEGER REFERENCES user_strategies(id) ON DELETE CASCADE,
                title           VARCHAR(255)    NOT NULL,
                description     TEXT,
                category        VARCHAR(50),
                tier_required   VARCHAR(20)     DEFAULT 'free',
                subscribers     INTEGER         DEFAULT 0,
                avg_win_rate    DECIMAL(5,2),
                avg_pnl         DECIMAL(15,2),
                is_published    BOOLEAN         DEFAULT TRUE,
                published_at    TIMESTAMPTZ     DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS marketplace_subscriptions (
                id                      SERIAL PRIMARY KEY,
                user_id                 INTEGER REFERENCES users(id) ON DELETE CASCADE,
                marketplace_strategy_id INTEGER REFERENCES marketplace_strategies(id) ON DELETE CASCADE,
                subscribed_at           TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(user_id, marketplace_strategy_id)
            )
        """))

        # ── Optimizer Runs ─────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS optimizer_runs (
                id              SERIAL PRIMARY KEY,
                user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
                strategy_id     INTEGER REFERENCES user_strategies(id) ON DELETE SET NULL,
                config          JSONB,
                status          VARCHAR(20)     DEFAULT 'pending',
                results         JSONB,
                error_message   TEXT,
                created_at      TIMESTAMPTZ     DEFAULT NOW(),
                completed_at    TIMESTAMPTZ
            )
        """))

    print("[Database] Tables ready")
