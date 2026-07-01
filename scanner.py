import os
import sys
import time
import threading
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force UTF-8 output on Windows so Unicode chars in log messages don't crash
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

load_dotenv()

IST = pytz.timezone('Asia/Kolkata')
last_scan_time = None
_rt_monitor_started = False

from core.db_storage import (
    init_data_files, load_config,
    save_signal, get_active_trades, get_today_pnl,
    update_trade, mark_target_hit, save_error, load_trades
)
from core.data_fetcher import fetch_quotes, fetch_historical
from core.realtime_feed import get_feed_instance, get_ltp_from_feed
from core import combined_engine, correlation_guard, news_filter, ml_filter
from core.order_executor import execute_signal
from bot.telegram_bot import (
    send_signal, send_target_hit, send_stop_loss_hit,
    send_eod_summary, send_daily_login_alert, send_error_alert,
    send_market_open_alert, send_weekly_report, send_premarket_report
)


def _check_upstox_token() -> bool:
    from auth.upstox_auth import verify_upstox_token
    return verify_upstox_token()


def _start_realtime_feed():
    """Start the Fyers WebSocket feed for all configured symbols."""
    global _rt_monitor_started
    try:
        syms_cfg = load_config().get('symbols', {})
        all_symbols = syms_cfg.get('equity', []) + syms_cfg.get('indices', [])
        feed = get_feed_instance(all_symbols)
        if feed and not feed._running:
            feed.start()
            print(f"[Scanner] Realtime WebSocket feed started ({len(all_symbols)} symbols)")
    except Exception as e:
        print(f"[Scanner] Realtime feed start error: {e}")

    if not _rt_monitor_started:
        t = threading.Thread(target=_realtime_monitor_loop, daemon=True)
        t.start()
        _rt_monitor_started = True
        print("[Scanner] Realtime monitor thread started (1-second interval)")


def _realtime_monitor_loop():
    """Background thread: checks active trades against WebSocket ticks every 1 second."""
    _account_balance_cache = [0.0, 0.0]  # [value, last_refresh_ts]

    def _get_balance():
        now = time.time()
        if now - _account_balance_cache[1] > 60:
            try:
                config = load_config()
                _account_balance_cache[0] = float(os.getenv('ACCOUNT_BALANCE', config['trading']['accountBalance']))
            except Exception:
                pass
            _account_balance_cache[1] = now
        return _account_balance_cache[0] or 500000.0

    while True:
        try:
            feed = get_feed_instance()
            if feed and feed._running:
                active_trades = get_active_trades()
                if active_trades:
                    balance = _get_balance()
                    for trade in active_trades:
                        sym = trade.get('symbol')
                        ltp = get_ltp_from_feed(sym)
                        if ltp:
                            try:
                                _monitor_trade(trade, {sym: {'ltp': ltp}}, balance)
                            except Exception as te:
                                save_error({"module": "scanner.rt_monitor", "message": str(te), "symbol": sym or ''})
        except Exception:
            pass
        time.sleep(1)


def job_daily_login():
    print(f"[Scanner] Running daily startup at {datetime.now(IST).strftime('%H:%M:%S')}")
    try:
        if _check_upstox_token():
            send_daily_login_alert(True, "Upstox Analytics")
            print("[Scanner] Upstox token present — starting feed and pre-fetch")
            _start_realtime_feed()

            config = load_config()
            syms_cfg = config.get('symbols', {})
            all_symbols = syms_cfg.get('equity', []) + syms_cfg.get('indices', [])
            print(f"[Scanner] Pre-fetching data for {len(all_symbols)} symbols...")
            for sym in all_symbols:
                try:
                    fetch_historical(sym, '15')
                    fetch_historical(sym, '60')
                except Exception:
                    pass
        else:
            send_daily_login_alert(False)
            print("[Scanner] UPSTOX_ANALYTICS_TOKEN missing in .env")
    except Exception as e:
        save_error({"module": "scanner.job_daily_login", "message": str(e), "symbol": ""})
        send_error_alert("scanner.job_daily_login", str(e))


def job_premarket_scan():
    print(f"[Scanner] Pre-market scan at {datetime.now(IST).strftime('%H:%M:%S')}")
    try:
        if not _check_upstox_token():
            return

        syms_cfg = load_config().get('symbols', {})
        all_symbols = syms_cfg.get('equity', [])[:10] + syms_cfg.get('indices', [])
        quotes = fetch_quotes(all_symbols)

        gap_ups = []
        gap_downs = []
        for sym, q in quotes.items():
            if not q:
                continue
            ltp = q.get('ltp', 0)
            prev_close = q.get('close', 0)
            if prev_close and ltp:
                gap_pct = (ltp - prev_close) / prev_close * 100
                short = sym.split(':')[1].replace('-EQ', '').replace('-INDEX', '') if ':' in sym else sym
                if gap_pct > 0.5:
                    gap_ups.append((short, gap_pct))
                elif gap_pct < -0.5:
                    gap_downs.append((short, abs(gap_pct)))

        send_market_open_alert(syms_cfg, quotes)
        send_premarket_report(gap_ups, gap_downs, quotes, syms_cfg)
        print(f"[Scanner] Pre-market: {len(gap_ups)} gap-ups, {len(gap_downs)} gap-downs")

    except Exception as e:
        save_error({"module": "scanner.job_premarket_scan", "message": str(e), "symbol": ""})
        send_error_alert("scanner.job_premarket_scan", str(e))


def job_main_scan():
    global last_scan_time

    now = datetime.now(IST)
    print(f"[Scanner] Main scan cycle at {now.strftime('%H:%M:%S')}")

    try:
        if not _check_upstox_token():
            print("[Scanner] No Upstox token, skipping scan")
            return

        config = load_config()
        trading_cfg = config['trading']
        account_balance = float(os.getenv('ACCOUNT_BALANCE', trading_cfg['accountBalance']))
        max_risk        = trading_cfg['maxRiskPerTrade']
        max_capital_pct         = trading_cfg.get('maxCapitalPerTrade', 0.20)
        min_strategies          = trading_cfg['minStrategiesConfirmed']
        min_strategies_volatile = trading_cfg.get('minStrategiesVolatile', 7)
        min_rr                  = trading_cfg['minRiskReward']
        min_vol_ratio           = trading_cfg.get('minVolRatio', 1.2)
        max_active              = trading_cfg['maxActiveTrades']
        max_daily_loss_pct = trading_cfg['maxDailyLoss']

        syms_cfg = config.get('symbols', {})
        active_trades = get_active_trades()
        today_pnl = get_today_pnl()

        # Gate 7: Max active trades
        if len(active_trades) >= max_active:
            print(f"[Scanner] Max active trades reached ({max_active}), skipping signal generation")
        else:
            equity_symbols = syms_cfg.get('equity', [])
            index_symbols = syms_cfg.get('indices', [])

            # ─── EQUITY SCAN ─────────────────────────────────────────────────
            for symbol in equity_symbols:
                try:
                    signal = combined_engine.run(
                        symbol=symbol,
                        
                        account_balance=account_balance,
                        max_risk_pct=max_risk,
                        max_capital_pct=max_capital_pct,
                        min_strategies=min_strategies,
                        min_strategies_volatile=min_strategies_volatile,
                        min_rr=min_rr,
                        min_vol_ratio=min_vol_ratio,
                        active_trades=active_trades,
                        today_pnl=today_pnl,
                        max_daily_loss=max_daily_loss_pct
                    )
                    if signal:
                        if not _pass_all_guards(signal, symbol, active_trades):
                            continue
                        trade_id = save_signal(signal)
                        signal['tradeId'] = trade_id
                        send_signal(signal)
                        _place_order(signal)
                        feed = get_feed_instance()
                        if feed:
                            feed.subscribe_symbols([symbol])
                        active_trades = get_active_trades()  # refresh
                        print(f"[Scanner] Signal: {signal['type']} {symbol} @ {signal['entryPrice']} [{trade_id}]")

                        if len(active_trades) >= max_active:
                            break

                except Exception as sym_e:
                    save_error({"module": "scanner.equity_scan", "message": str(sym_e), "symbol": symbol})
                    print(f"[Scanner] Error scanning {symbol}: {sym_e}")

            # ─── INDEX SCAN ──────────────────────────────────────────────────
            for symbol in index_symbols:
                if len(active_trades) >= max_active:
                    break
                try:
                    signal = combined_engine.run(
                        symbol=symbol,
                        
                        account_balance=account_balance,
                        max_risk_pct=max_risk,
                        max_capital_pct=max_capital_pct,
                        min_strategies=min_strategies,
                        min_strategies_volatile=min_strategies_volatile,
                        min_rr=min_rr,
                        min_vol_ratio=min_vol_ratio,
                        active_trades=active_trades,
                        today_pnl=today_pnl,
                        max_daily_loss=max_daily_loss_pct
                    )
                    if signal:
                        if not _pass_all_guards(signal, symbol, active_trades):
                            continue
                        trade_id = save_signal(signal)
                        signal['tradeId'] = trade_id
                        send_signal(signal)
                        _place_order(signal)
                        feed = get_feed_instance()
                        if feed:
                            feed.subscribe_symbols([symbol])
                        active_trades = get_active_trades()
                        print(f"[Scanner] Index Signal: {signal['type']} {symbol} @ {signal['entryPrice']} [{trade_id}]")

                except Exception as sym_e:
                    save_error({"module": "scanner.index_scan", "message": str(sym_e), "symbol": symbol})

        # ─── MONITOR ACTIVE TRADES ───────────────────────────────────────────
        active_trades = get_active_trades()
        if active_trades:
            active_symbols = [t['symbol'] for t in active_trades if t.get('symbol')]

            batch_quotes = {}
            for i in range(0, len(active_symbols), 50):
                batch = active_symbols[i:i+50]
                try:
                    batch_q = fetch_quotes(batch)
                    batch_quotes.update(batch_q)
                except Exception as qe:
                    save_error({"module": "scanner.monitor_quotes", "message": str(qe), "symbol": ""})

            for trade in active_trades:
                try:
                    _monitor_trade(trade, batch_quotes, account_balance)
                except Exception as te:
                    save_error({"module": "scanner.monitor_trade", "message": str(te), "symbol": trade.get('symbol', '')})

        last_scan_time = datetime.now(IST).isoformat()
        print(f"[Scanner] Scan complete. Active trades: {len(get_active_trades())}")

    except Exception as e:
        save_error({"module": "scanner.job_main_scan", "message": str(e), "symbol": ""})
        send_error_alert("scanner.job_main_scan", str(e))
        print(f"[Scanner] Scan error: {e}")


def _pass_all_guards(signal: dict, symbol: str, active_trades: list) -> bool:
    """Run correlation, news, and ML guards. Returns True if signal should proceed."""

    # Guard 1: Correlation — block if same sector already has an open position
    try:
        corr_ok, corr_reason = correlation_guard.is_allowed(symbol, active_trades)
        if not corr_ok:
            print(f"[Scanner] Correlation BLOCKED: {symbol} — {corr_reason}")
            return False
        print(f"[Scanner] Correlation OK: {corr_reason}")
    except Exception as e:
        print(f"[Scanner] Correlation guard error for {symbol}: {e}")

    # Guard 2: News sentiment — block on strong negative news
    try:
        news = news_filter.analyze(symbol)
        if news.get('blocked'):
            print(f"[Scanner] News BLOCKED: {symbol} — {news.get('reason')}")
            return False
        if news.get('reason'):
            print(f"[Scanner] News: {symbol} — {news.get('reason')}")
    except Exception as e:
        print(f"[Scanner] News filter error for {symbol}: {e}")

    # Guard 3: ML filter — block if predicted profit probability < 35 %
    try:
        ml = ml_filter.predict(signal)
        if not ml.get('allowed', True):
            print(f"[Scanner] ML BLOCKED: {symbol} — {ml.get('reason')}")
            return False
        print(f"[Scanner] ML: {symbol} — {ml.get('reason')}")
    except Exception as e:
        print(f"[Scanner] ML filter error for {symbol}: {e}")

    return True


def _place_order(signal: dict) -> None:
    """Place a paper or live order and log the result. Never raises."""
    try:
        result = execute_signal(signal)
        if result:
            print(
                f"[OrderExecutor] {result.get('mode','?').upper()} | "
                f"{result.get('status')} | {result.get('symbol')} "
                f"× {result.get('qty')} | ID: {result.get('orderId')}"
            )
    except Exception as e:
        print(f"[OrderExecutor] order failed for {signal.get('symbol')}: {e}")


def _monitor_trade(trade: dict, quotes: dict, account_balance: float):
    sym         = trade.get('symbol')
    trade_id    = trade.get('tradeId')
    signal_type = trade.get('type')
    entry       = float(trade.get('entryPrice', 0))
    sl          = float(trade.get('stopLoss', 0))
    atr         = float(trade.get('atr', 0))
    t1          = float(trade.get('target1', 0) or 0)
    t2          = float(trade.get('target2', 0) or 0)
    t3          = float(trade.get('target3', 0) or 0)

    quote = quotes.get(sym, {})
    ltp   = float(quote.get('ltp', 0) or 0)
    if not ltp:
        return

    # Check stop loss — guard: sl must be a real positive price
    sl_hit = sl > 0 and ((signal_type == 'BUY' and ltp <= sl) or (signal_type == 'SELL' and ltp >= sl))
    if sl_hit:
        size = int(trade.get('positionSize', 0) or 0)
        pnl  = (ltp - entry) * size if signal_type == 'BUY' else (entry - ltp) * size
        if update_trade(trade_id, {'exitPrice': ltp, 'exitReason': 'STOP_LOSS_HIT'}):
            send_stop_loss_hit({
                'tradeId':           trade_id,
                'displaySymbol':     trade.get('displaySymbol'),
                'profitLoss':        round(pnl, 2),
                'profitLossPercent': round(pnl / (entry * size) * 100, 2) if entry * size else 0,
            }, ltp)
            print(f"[Scanner] SL Hit: {sym} @ {ltp}")
        else:
            print(f"[Scanner] SL Hit detected but DB update failed: {sym}")
        return

    t1_hit = trade.get('target1Hit', False)
    t2_hit = trade.get('target2Hit', False)
    t3_hit = trade.get('target3Hit', False)

    # ── Trailing stop loss logic ───────────────────────────────────────────────
    # After T1: move SL to breakeven (entry)
    # After T2: trail SL by 1×ATR behind current price
    if t2_hit and atr > 0:
        if signal_type == 'BUY':
            trailing_sl = round(ltp - atr, 2)
            if trailing_sl > sl:
                update_trade(trade_id, {'notes': f'Trailing SL moved to {trailing_sl}'})
                # Update the stopLoss directly via raw db call
                try:
                    from core.database import get_engine
                    from sqlalchemy import text
                    engine = get_engine()
                    with engine.begin() as conn:
                        conn.execute(
                            text("UPDATE trades SET stop_loss = :sl, notes = :note WHERE trade_id = :id"),
                            {"sl": trailing_sl, "note": f"Trail SL @ {trailing_sl}", "id": trade_id}
                        )
                    print(f"[Scanner] Trailing SL updated: {sym} → {trailing_sl}")
                except Exception as tsl_e:
                    print(f"[Scanner] Trailing SL update error: {tsl_e}")
        else:  # SELL
            trailing_sl = round(ltp + atr, 2)
            if trailing_sl < sl:
                try:
                    from core.database import get_engine
                    from sqlalchemy import text
                    engine = get_engine()
                    with engine.begin() as conn:
                        conn.execute(
                            text("UPDATE trades SET stop_loss = :sl, notes = :note WHERE trade_id = :id"),
                            {"sl": trailing_sl, "note": f"Trail SL @ {trailing_sl}", "id": trade_id}
                        )
                    print(f"[Scanner] Trailing SL updated: {sym} → {trailing_sl}")
                except Exception:
                    pass

    elif t1_hit and not t2_hit and entry != sl:
        # Move SL to breakeven after T1
        be_sl = entry
        if (signal_type == 'BUY' and be_sl > sl) or (signal_type == 'SELL' and be_sl < sl):
            try:
                from core.database import get_engine
                from sqlalchemy import text
                engine = get_engine()
                with engine.begin() as conn:
                    conn.execute(
                        text("UPDATE trades SET stop_loss = :sl, notes = :note WHERE trade_id = :id"),
                        {"sl": be_sl, "note": "SL moved to breakeven after T1", "id": trade_id}
                    )
                print(f"[Scanner] SL moved to breakeven: {sym} @ {be_sl}")
            except Exception:
                pass

    # ── Target checks — guard: target must be a real positive price ────────────
    if not t1_hit and t1 > 0:
        if (signal_type == 'BUY' and ltp >= t1) or (signal_type == 'SELL' and ltp <= t1):
            if mark_target_hit(trade_id, 1, ltp):
                send_target_hit(trade, 1, ltp)
                print(f"[Scanner] T1 Hit: {sym} @ {ltp}")

                # Partial exit — close 50 % of position at T1
                original_qty = int(trade.get('positionSize', 0) or 0)
                if original_qty > 0:
                    half_qty     = max(1, original_qty // 2)
                    remaining    = original_qty - half_qty
                    exit_signal  = {
                        'symbol':        sym,
                        'displaySymbol': trade.get('displaySymbol'),
                        'type':          'SELL' if signal_type == 'BUY' else 'BUY',
                        'positionSize':  half_qty,
                        'entryPrice':    ltp,
                    }
                    _place_order(exit_signal)
                    if remaining > 0:
                        update_trade(trade_id, {'positionSize': remaining})
                        print(f"[Scanner] Partial exit: sold {half_qty}, {remaining} remaining — {sym}")
                    else:
                        update_trade(trade_id, {'exitPrice': ltp, 'exitReason': 'T1_FULL_EXIT'})
                        print(f"[Scanner] Full exit at T1 (qty=1): {sym} @ {ltp}")
            else:
                print(f"[Scanner] T1 Hit detected but DB update failed: {sym}")

    elif not t2_hit and t2 > 0:
        if (signal_type == 'BUY' and ltp >= t2) or (signal_type == 'SELL' and ltp <= t2):
            if mark_target_hit(trade_id, 2, ltp):
                send_target_hit(trade, 2, ltp)
                print(f"[Scanner] T2 Hit: {sym} @ {ltp}")
            else:
                print(f"[Scanner] T2 Hit detected but DB update failed: {sym}")

    elif not t3_hit and t3 > 0:
        if (signal_type == 'BUY' and ltp >= t3) or (signal_type == 'SELL' and ltp <= t3):
            if mark_target_hit(trade_id, 3, ltp):
                send_target_hit(trade, 3, ltp)
                if update_trade(trade_id, {'exitPrice': ltp, 'exitReason': 'ALL_TARGETS_HIT'}):
                    print(f"[Scanner] T3 Hit + Closed: {sym} @ {ltp}")
                else:
                    print(f"[Scanner] T3 Hit notified but trade close DB update failed: {sym}")
            else:
                print(f"[Scanner] T3 Hit detected but DB update failed: {sym}")


def job_eod_close():
    print(f"[Scanner] EOD close at {datetime.now(IST).strftime('%H:%M:%S')}")
    try:
        active_trades = get_active_trades()

        if not active_trades:
            print("[Scanner] No active trades to close at EOD")
        else:
            symbols = [t['symbol'] for t in active_trades if t.get('symbol')]
            quotes = {}
            for i in range(0, len(symbols), 50):
                batch_q = fetch_quotes(symbols[i:i+50])
                quotes.update(batch_q)

            for trade in active_trades:
                sym = trade.get('symbol', '')
                ltp = quotes.get(sym, {}).get('ltp', 0) or trade.get('entryPrice', 0)
                update_trade(trade['tradeId'], {
                    'exitPrice': ltp,
                    'exitReason': 'EOD_CLOSE'
                })
                print(f"[Scanner] EOD closed {sym} @ {ltp}")

        config = load_config()
        account_balance = float(os.getenv('ACCOUNT_BALANCE', config['trading']['accountBalance']))
        today_str = datetime.now(IST).strftime('%Y-%m-%d')
        data = load_trades()
        send_eod_summary(today_str, data['trades'], account_balance)

    except Exception as e:
        save_error({"module": "scanner.job_eod_close", "message": str(e), "symbol": ""})
        send_error_alert("scanner.job_eod_close", str(e))


def job_weekly_report():
    print(f"[Scanner] Weekly report at {datetime.now(IST).strftime('%H:%M:%S')}")
    try:
        config = load_config()
        account_balance = float(os.getenv('ACCOUNT_BALANCE', config['trading']['accountBalance']))
        today = datetime.now(IST)
        week_start = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        week_end = today.strftime('%Y-%m-%d')
        data = load_trades()
        send_weekly_report(week_start, week_end, data['trades'], account_balance)
    except Exception as e:
        save_error({"module": "scanner.job_weekly_report", "message": str(e), "symbol": ""})
        send_error_alert("scanner.job_weekly_report", str(e))


def job_token_refresh():
    """Upstox Analytics Token is long-lived (1 year) — no daily refresh needed."""
    print(f"[Scanner] Token check at {datetime.now(IST).strftime('%H:%M:%S')}")
    ok = _check_upstox_token()
    print(f"[Scanner] Upstox token present: {ok}")


def job_ml_retrain():
    """Retrain the ML signal filter on Sundays at 8:00 AM using accumulated trade history."""
    print(f"[Scanner] ML retrain at {datetime.now(IST).strftime('%H:%M:%S')}")
    try:
        from core.ml_filter import train
        success = train()
        status  = "completed" if success else "skipped (not enough data)"
        print(f"[Scanner] ML retrain {status}")
    except Exception as e:
        save_error({"module": "scanner.job_ml_retrain", "message": str(e), "symbol": ""})


def main():
    init_data_files()

    scheduler = BlockingScheduler(timezone=IST)

    # Job 0: Token refresh at 8:50 AM, Mon-Fri (before daily login)
    scheduler.add_job(
        job_token_refresh,
        CronTrigger(hour=8, minute=50, day_of_week='mon-fri', timezone=IST),
        id='token_refresh',
        name='Daily Token Refresh'
    )

    # Job 1: Daily login at 8:55 AM, Mon-Fri
    scheduler.add_job(
        job_daily_login,
        CronTrigger(hour=8, minute=55, day_of_week='mon-fri', timezone=IST),
        id='daily_login',
        name='Daily Fyers Login'
    )

    # Job 2: Pre-market scan at 9:05 AM, Mon-Fri
    scheduler.add_job(
        job_premarket_scan,
        CronTrigger(hour=9, minute=5, day_of_week='mon-fri', timezone=IST),
        id='premarket_scan',
        name='Pre-market Scan'
    )

    # Job 3: Main scan every minute from 9:15 to 15:20, Mon-Fri
    # 9:15–9:59 (minute 15-59 of hour 9)
    scheduler.add_job(
        job_main_scan,
        CronTrigger(hour='9', minute='15-59', day_of_week='mon-fri', timezone=IST),
        id='main_scan_9',
        name='Main Scan (9h)'
    )
    # 10:00–14:59 (every minute)
    scheduler.add_job(
        job_main_scan,
        CronTrigger(hour='10,11,12,13,14', minute='*', day_of_week='mon-fri', timezone=IST),
        id='main_scan_10_14',
        name='Main Scan (10-14h)'
    )
    # 15:00–15:20 (minute 0-20 of hour 15)
    scheduler.add_job(
        job_main_scan,
        CronTrigger(hour='15', minute='0-20', day_of_week='mon-fri', timezone=IST),
        id='main_scan_15',
        name='Main Scan (15h)'
    )

    # Job 4: EOD close at 3:35 PM, Mon-Fri
    scheduler.add_job(
        job_eod_close,
        CronTrigger(hour=15, minute=35, day_of_week='mon-fri', timezone=IST),
        id='eod_close',
        name='EOD Trade Close'
    )

    # Job 5: Weekly report on Sunday at 10:00 AM
    scheduler.add_job(
        job_weekly_report,
        CronTrigger(day_of_week='sun', hour=10, minute=0, timezone=IST),
        id='weekly_report',
        name='Weekly Performance Report'
    )

    # Job 6: ML model retrain on Sunday at 8:00 AM
    scheduler.add_job(
        job_ml_retrain,
        CronTrigger(day_of_week='sun', hour=8, minute=0, timezone=IST),
        id='ml_retrain',
        name='ML Model Retrain'
    )

    print("=" * 60)
    print("  STOCK & OPTIONS TRADING PREDICTION SYSTEM")
    print("=" * 60)
    print(f"  Timezone: Asia/Kolkata (IST)")
    print(f"  Scan interval: 1 minute")
    print(f"  Market hours: 09:15 - 15:20")
    print("=" * 60)
    print("  Scheduled jobs:")
    for job in scheduler.get_jobs():
        print(f"  - {job.name}")
    print("=" * 60)

    print("\n[Scanner] Running immediate login check...")
    try:
        job_daily_login()
    except Exception as e:
        print(f"[Scanner] Initial login check failed: {e}")

    print("[Scanner] Starting scheduler. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n[Scanner] Stopped by user.")
        scheduler.shutdown()


if __name__ == '__main__':
    main()
