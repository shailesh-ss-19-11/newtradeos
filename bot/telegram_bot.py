import asyncio
import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
import pytz
from dotenv import load_dotenv

load_dotenv()

IST = pytz.timezone('Asia/Kolkata')

_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
_chat_ids = [cid.strip() for cid in os.getenv('TELEGRAM_CHAT_IDS', os.getenv('TELEGRAM_CHAT_ID', '')).split(',') if cid.strip()]


def run_async(coro) -> Optional[object]:
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    except Exception as e:
        print(f"[Telegram] run_async error: {e}")
        from core.db_storage import save_error
        save_error({"module": "telegram_bot", "message": f"run_async error: {e}", "symbol": ""})
        return None


async def _send_message_async(text: str, parse_mode: str = 'HTML') -> Optional[int]:
    if not _bot_token or not _chat_ids:
        print(f"[Telegram] Token/ChatID not configured. Message: {text[:80]}")
        return None

    from telegram import Bot
    last_msg_id = None
    async with Bot(token=_bot_token) as bot:
        for chat_id in _chat_ids:
            try:
                msg = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    disable_web_page_preview=True
                )
                last_msg_id = msg.message_id
            except Exception as e:
                print(f"[Telegram] Failed to send to {chat_id}: {e}")
    return last_msg_id


def _send_with_retry(text: str, parse_mode: str = 'HTML') -> Optional[int]:
    for attempt in range(2):
        try:
            msg_id = run_async(_send_message_async(text, parse_mode))
            return msg_id
        except Exception as e:
            if attempt == 0:
                time.sleep(3)
            else:
                from core.db_storage import save_error
                save_error({"module": "telegram_bot._send", "message": str(e), "symbol": ""})
                return None
    return None


def _fmt_price(v) -> str:
    if v is None:
        return 'N/A'
    return f"₹{float(v):,.2f}"


def _fmt_pct(v) -> str:
    if v is None:
        return 'N/A'
    return f"{float(v):.2f}%"


def send_signal(trade: dict) -> Optional[int]:
    try:
        t = trade
        signal_time = t.get('signalTime', '')
        try:
            dt = datetime.fromisoformat(signal_time)
            time_str = dt.strftime('%H:%M:%S IST')
            date_str = dt.strftime('%d-%b-%Y')
        except Exception:
            now_ist = datetime.now(IST)
            time_str = now_ist.strftime('%H:%M:%S IST')
            date_str = now_ist.strftime('%d-%b-%Y')

        strategies = t.get('strategies', {})
        strategy_lines = []
        strategy_order = ['candlestick', 'trend', 'momentum', 'breakout',
                          'support_resistance', 'volume', 'reversal', 'options']
        for name in strategy_order:
            s = strategies.get(name, {})
            sig = s.get('signal', 'NEUTRAL')
            icon = '✅' if sig in ('BUY', 'SELL') else '❌'
            confs = s.get('confirmations', [])
            conf_str = ', '.join(confs[:2]) if confs else sig
            strategy_lines.append(f"{icon} <b>{name.replace('_', ' ').title()}</b>: {conf_str}")

        opts = t.get('optionsData') or {}
        options_section = ''
        if opts:
            mp = opts.get('max_pain', 'N/A')
            pcr_val = opts.get('pcr', 'N/A')
            ce_r = opts.get('ce_resistance', 'N/A')
            pe_s = opts.get('pe_support', 'N/A')
            options_section = (
                f"\n📉 Max Pain: <b>{mp}</b> | PCR: <b>{pcr_val}</b>\n"
                f"🔴 CE Resistance: <b>{ce_r}</b>\n"
                f"🟢 PE Support: <b>{pe_s}</b>\n"
            )

        type_emoji = '📈' if t.get('type') == 'BUY' else '📉'
        conf_emoji = {'HIGH': '🔥', 'MEDIUM': '⚡', 'LOW': '💡'}.get(t.get('confidence', ''), '💡')

        text = (
            f"🚨 <b>TRADING SIGNAL ALERT</b> 🚨\n\n"
            f"📊 Symbol: <b>{t.get('displaySymbol')}</b>\n"
            f"{type_emoji} Signal: <b>{t.get('type')}</b> | {conf_emoji} Confidence: <b>{t.get('confidence')}</b>\n"
            f"⏰ Time: {time_str}\n"
            f"📅 Date: {date_str}\n"
            f"🕐 Multi-TF: <b>{t.get('multiTimeframeAlignment', 'N/A')}</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💰 ENTRY:      <b>{_fmt_price(t.get('entryPrice'))}</b>\n"
            f"🛑 STOP LOSS:  <b>{_fmt_price(t.get('stopLoss'))}</b> (-{_fmt_pct(t.get('stopLossPercent'))})\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 TARGET 1:   <b>{_fmt_price(t.get('target1'))}</b> (+{_fmt_pct(t.get('target1Pct'))}) [1.5R]\n"
            f"🎯 TARGET 2:   <b>{_fmt_price(t.get('target2'))}</b> (+{_fmt_pct(t.get('target2Pct'))}) [2.5R]\n"
            f"🎯 TARGET 3:   <b>{_fmt_price(t.get('target3'))}</b> (+{_fmt_pct(t.get('target3Pct'))}) [4R]\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📦 Qty:         <b>{t.get('positionSize')} shares</b>\n"
            f"💵 Capital:     <b>{_fmt_price(t.get('capitalRequired'))}</b>\n"
            f"⚠️  Max Loss:    <b>{_fmt_price(t.get('maxLoss'))}</b> (1% rule)\n"
            f"📊 R:R Ratio:   <b>1:{t.get('riskReward')}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔥 STRATEGY VOTES: <b>{t.get('votes')}</b>\n\n"
            + '\n'.join(strategy_lines)
            + options_section
            + f"\n━━━━━━━━━━━━━━━━━━━\n"
            f"📝 Trade ID: <code>{t.get('tradeId')}</code>"
        )

        msg_id = _send_with_retry(text)
        if msg_id and t.get('tradeId'):
            from core.db_storage import update_trade
            update_trade(t['tradeId'], {'telegramMessageId': msg_id})
        return msg_id

    except Exception as e:
        from core.db_storage import save_error
        save_error({"module": "telegram_bot.send_signal", "message": str(e), "symbol": trade.get('symbol', '')})
        return None


def send_target_hit(trade: dict, target_number: int, hit_price: float) -> Optional[int]:
    try:
        text = (
            f"🎯 <b>TARGET {target_number} HIT</b> — {trade.get('displaySymbol')}\n\n"
            f"Hit Price: <b>{_fmt_price(hit_price)}</b>\n"
            f"Trade ID: <code>{trade.get('tradeId')}</code>\n\n"
            f"✅ Action: Book partial profits.\n"
            f"Move SL to previous target."
        )
        return _send_with_retry(text)
    except Exception as e:
        from core.db_storage import save_error
        save_error({"module": "telegram_bot.send_target_hit", "message": str(e), "symbol": trade.get('symbol', '')})
        return None


def send_stop_loss_hit(trade: dict, exit_price: float) -> Optional[int]:
    try:
        pnl = trade.get('profitLoss', 0) or 0
        pnl_pct = trade.get('profitLossPercent', 0) or 0
        account_balance = float(os.getenv('ACCOUNT_BALANCE', 500000))
        protected = account_balance - abs(pnl)

        text = (
            f"🛑 <b>STOP LOSS HIT</b> — {trade.get('displaySymbol')}\n\n"
            f"Exit Price: <b>{_fmt_price(exit_price)}</b>\n"
            f"Loss: <b>{_fmt_price(pnl)}</b> ({_fmt_pct(pnl_pct)})\n"
            f"Trade ID: <code>{trade.get('tradeId')}</code>\n"
            f"Capital Protected: <b>{_fmt_price(protected)}</b>"
        )
        return _send_with_retry(text)
    except Exception as e:
        from core.db_storage import save_error
        save_error({"module": "telegram_bot.send_stop_loss_hit", "message": str(e), "symbol": trade.get('symbol', '')})
        return None


def send_eod_summary(date_string: str, trades: list, account_balance: float) -> Optional[int]:
    try:
        today_closed = [t for t in trades if t.get('date') == date_string and t.get('status') == 'CLOSED']
        wins = [t for t in today_closed if t.get('isProfit') is True]
        losses = [t for t in today_closed if t.get('isProfit') is False]
        total_pnl = sum(t.get('profitLoss', 0) or 0 for t in today_closed)
        win_rate = round(len(wins) / len(today_closed) * 100, 1) if today_closed else 0

        trade_lines = []
        for t in today_closed:
            pnl_icon = '✅' if t.get('isProfit') else '❌'
            trade_lines.append(
                f"{pnl_icon} {t.get('displaySymbol')} {t.get('type')} | "
                f"Entry: {_fmt_price(t.get('entryPrice'))} → Exit: {_fmt_price(t.get('exitPrice'))} | "
                f"P&L: {_fmt_price(t.get('profitLoss'))}"
            )

        trades_text = '\n'.join(trade_lines) if trade_lines else 'No closed trades today.'
        pnl_icon = '📈' if total_pnl >= 0 else '📉'

        text = (
            f"📊 <b>END OF DAY SUMMARY</b> — {date_string}\n\n"
            f"Total Signals: <b>{len(today_closed)}</b>\n"
            f"✅ Winners: <b>{len(wins)}</b> | ❌ Losers: <b>{len(losses)}</b>\n"
            f"Win Rate: <b>{win_rate}%</b>\n"
            f"{pnl_icon} Today's P&L: <b>{_fmt_price(total_pnl)}</b>\n"
            f"💼 Account: <b>{_fmt_price(account_balance)}</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{trades_text}"
        )
        return _send_with_retry(text)
    except Exception as e:
        from core.db_storage import save_error
        save_error({"module": "telegram_bot.send_eod_summary", "message": str(e), "symbol": ""})
        return None


def send_daily_login_alert(success: bool, username: str = '') -> Optional[int]:
    icon = '✅' if success else '❌'
    status = 'successful' if success else 'FAILED'
    text = f"{icon} <b>Fyers login {status}</b> {username}\n⏰ {datetime.now(IST).strftime('%H:%M:%S IST')}"
    return _send_with_retry(text)


def send_error_alert(module: str, message: str, symbol: str = '') -> Optional[int]:
    text = (
        f"⚠️ <b>SYSTEM ERROR</b>\n\n"
        f"Module: <code>{module}</code>\n"
        f"{'Symbol: ' + symbol + chr(10) if symbol else ''}"
        f"Error: {message[:300]}\n"
        f"⏰ {datetime.now(IST).strftime('%H:%M:%S IST')}"
    )
    return _send_with_retry(text)


def send_market_open_alert(symbols: dict, quotes: dict) -> Optional[int]:
    try:
        now_str = datetime.now(IST).strftime('%H:%M:%S IST')
        lines = [f"🔔 <b>MARKET OPEN</b> — {now_str}\n"]

        all_symbols = symbols.get('equity', [])[:5] + symbols.get('indices', [])
        for sym in all_symbols:
            q = quotes.get(sym, {})
            if q:
                chp = q.get('changePct', 0)
                icon = '📈' if chp >= 0 else '📉'
                short = sym.split(':')[1].replace('-EQ', '').replace('-INDEX', '') if ':' in sym else sym
                lines.append(f"{icon} {short}: {_fmt_price(q.get('ltp'))} ({chp:+.2f}%)")

        text = '\n'.join(lines)
        return _send_with_retry(text)
    except Exception as e:
        from core.db_storage import save_error
        save_error({"module": "telegram_bot.send_market_open_alert", "message": str(e), "symbol": ""})
        return None


def _send_email(subject: str, body: str) -> bool:
    """Send alert email via SMTP. Configure EMAIL_* vars in .env to enable."""
    smtp_host = os.getenv('EMAIL_SMTP_HOST', '')
    smtp_port = int(os.getenv('EMAIL_SMTP_PORT', 587))
    smtp_user = os.getenv('EMAIL_SMTP_USER', '')
    smtp_pass = os.getenv('EMAIL_SMTP_PASS', '')
    to_addr   = os.getenv('EMAIL_TO', smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass]):
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[TradeOS] {subject}"
        msg['From']    = smtp_user
        msg['To']      = to_addr
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_addr, msg.as_string())
        return True
    except Exception as e:
        print(f"[Telegram] Email send failed: {e}")
        return False


def send_stop_loss_hit_escalated(trade: dict, exit_price: float) -> None:
    """Send SL hit via Telegram + email escalation."""
    send_stop_loss_hit(trade, exit_price)
    subject = f"SL HIT — {trade.get('displaySymbol')} | Loss: {_fmt_price(trade.get('profitLoss'))}"
    body    = (
        f"Stop Loss Hit Alert\n\n"
        f"Symbol:     {trade.get('displaySymbol')}\n"
        f"Exit Price: {_fmt_price(exit_price)}\n"
        f"Loss:       {_fmt_price(trade.get('profitLoss'))}\n"
        f"Trade ID:   {trade.get('tradeId')}\n"
        f"Time:       {datetime.now(IST).strftime('%H:%M:%S IST')}"
    )
    _send_email(subject, body)


def send_premarket_report(gap_ups: list, gap_downs: list, quotes: dict, symbols: dict) -> Optional[int]:
    """Daily pre-market Telegram report with gap analysis + previous day summary."""
    try:
        now_str  = datetime.now(IST).strftime('%d-%b-%Y %H:%M IST')
        today_str = datetime.now(IST).strftime('%Y-%m-%d')

        # Previous day P&L from DB
        prev_pnl   = 0.0
        prev_wins  = 0
        prev_total = 0
        try:
            from core.db_storage import get_trades_by_date
            from datetime import timedelta
            prev_date  = (datetime.now(IST) - timedelta(days=1)).strftime('%Y-%m-%d')
            prev_trades = get_trades_by_date(prev_date)
            prev_closed = [t for t in prev_trades if t.get('status') == 'CLOSED']
            prev_pnl    = sum(t.get('profitLoss', 0) or 0 for t in prev_closed)
            prev_wins   = sum(1 for t in prev_closed if t.get('isProfit'))
            prev_total  = len(prev_closed)
        except Exception:
            pass

        # Index quotes summary
        index_lines = []
        for sym in symbols.get('indices', []):
            q = quotes.get(sym, {})
            if q:
                chp   = q.get('changePct', 0) or 0
                icon  = '📈' if chp >= 0 else '📉'
                short = sym.split(':')[1].replace('-INDEX', '') if ':' in sym else sym
                index_lines.append(f"{icon} {short}: {_fmt_price(q.get('ltp'))} ({chp:+.2f}%)")

        # Gap analysis
        gap_up_lines   = [f"↑ {sym} +{pct:.2f}%" for sym, pct in sorted(gap_ups,   key=lambda x: -x[1])[:5]]
        gap_down_lines = [f"↓ {sym} -{pct:.2f}%" for sym, pct in sorted(gap_downs, key=lambda x: -x[1])[:5]]

        pnl_icon = '📈' if prev_pnl >= 0 else '📉'

        text = (
            f"🌅 <b>PRE-MARKET REPORT</b> — {now_str}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Yesterday's Performance</b>\n"
            f"Trades: {prev_total} | Wins: {prev_wins} | Losses: {prev_total - prev_wins}\n"
            f"{pnl_icon} P&L: <b>{_fmt_price(prev_pnl)}</b>\n\n"
        )

        if index_lines:
            text += "📉 <b>Index Snapshot</b>\n" + '\n'.join(index_lines) + '\n\n'

        if gap_up_lines:
            text += "🚀 <b>Gap Ups</b>\n" + '\n'.join(gap_up_lines) + '\n\n'

        if gap_down_lines:
            text += "🔻 <b>Gap Downs</b>\n" + '\n'.join(gap_down_lines) + '\n\n'

        text += f"━━━━━━━━━━━━━━━━━━━\n⚡ Scanner active from 09:15 IST"

        return _send_with_retry(text)

    except Exception as e:
        from core.db_storage import save_error
        save_error({"module": "telegram_bot.send_premarket_report", "message": str(e), "symbol": ""})
        return None


def send_weekly_report(start_date: str, end_date: str, trades: list, account_balance: float) -> Optional[int]:
    try:
        week_trades = [t for t in trades if start_date <= t.get('date', '') <= end_date and t.get('status') == 'CLOSED']
        wins = [t for t in week_trades if t.get('isProfit') is True]
        losses = [t for t in week_trades if t.get('isProfit') is False]
        total_pnl = sum(t.get('profitLoss', 0) or 0 for t in week_trades)
        win_rate = round(len(wins) / len(week_trades) * 100, 1) if week_trades else 0

        best = max(week_trades, key=lambda t: t.get('profitLoss', 0) or 0) if week_trades else None
        worst = min(week_trades, key=lambda t: t.get('profitLoss', 0) or 0) if week_trades else None

        pnl_icon = '📈' if total_pnl >= 0 else '📉'

        text = (
            f"📊 <b>WEEKLY PERFORMANCE REPORT</b>\n"
            f"{start_date} → {end_date}\n\n"
            f"Total Trades: <b>{len(week_trades)}</b>\n"
            f"✅ Winners: <b>{len(wins)}</b> | ❌ Losers: <b>{len(losses)}</b>\n"
            f"Win Rate: <b>{win_rate}%</b>\n"
            f"{pnl_icon} Weekly P&L: <b>{_fmt_price(total_pnl)}</b>\n"
            f"💼 Account Balance: <b>{_fmt_price(account_balance)}</b>\n"
        )

        if best:
            text += f"\n🏆 Best Trade: {best.get('displaySymbol')} {_fmt_price(best.get('profitLoss'))}"
        if worst:
            text += f"\n💀 Worst Trade: {worst.get('displaySymbol')} {_fmt_price(worst.get('profitLoss'))}"

        return _send_with_retry(text)
    except Exception as e:
        from core.db_storage import save_error
        save_error({"module": "telegram_bot.send_weekly_report", "message": str(e), "symbol": ""})
        return None
