"""
Enhanced backtesting engine v2.
Features:
- No look-ahead bias (signal on day T → entry at open of day T+1)
- Partial exits at T1/T2/T3
- Trailing stop-loss
- Move SL to breakeven after T1
- Transaction costs (0.1% per side)
- Multiple open positions with capital allocation
- Daily mark-to-market
- Benchmark comparison (Nifty 50)
- Sharpe, Sortino, Max Drawdown
"""

import sys
import os
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, date as date_type
from typing import Optional
import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_fetcher import fetch_historical
from core.stock_universe import get_universe, get_display_name, STOCK_CATALOG
from core.strategy_engine import generate_signal

IST = pytz.timezone('Asia/Kolkata')
TRANSACTION_COST_PCT = 0.1  # 0.1% per side (brokerage + taxes simplified)
RISK_FREE_RATE_ANNUAL = 0.065  # 6.5% per annum


# ─── Position ────────────────────────────────────────────────────────────────

class Position:
    def __init__(self, symbol: str, display_symbol: str, strategy_name: str,
                 direction: str, entry_date, entry_price: float,
                 quantity: int, sl: float, t1: float, t2: float, t3: float,
                 config: dict):
        self.symbol         = symbol
        self.display_symbol = display_symbol
        self.strategy_name  = strategy_name
        self.direction      = direction   # 'BUY' or 'SELL'
        self.entry_date     = entry_date
        self.entry_price    = float(entry_price)
        self.initial_qty    = quantity
        self.remaining_qty  = quantity
        self.current_sl     = float(sl)
        self.original_sl    = float(sl)
        self.t1             = float(t1)
        self.t2             = float(t2)
        self.t3             = float(t3)

        self.t1_enabled        = config.get('t1_enabled', True)
        self.t2_enabled        = config.get('t2_enabled', True)
        self.t3_enabled        = config.get('t3_enabled', True)
        self.t1_qty_pct        = config.get('t1_qty_pct', 30)
        self.t2_qty_pct        = config.get('t2_qty_pct', 30)
        self.t3_qty_pct        = config.get('t3_qty_pct', 40)
        self.breakeven_t1      = config.get('breakeven_after_t1', False)
        self.trailing_sl       = config.get('trailing_sl', False)
        self.trailing_sl_pct   = config.get('sl_pct', 2.0)

        self.t1_hit   = False
        self.t2_hit   = False
        self.t3_hit   = False

        self.exits: list[dict] = []  # list of {date, price, qty, type}
        self.is_closed  = False
        self.exit_date  = None
        self.exit_type  = None
        self.capital_returned = 0.0

    def process_day(self, day_open: float, day_high: float, day_low: float,
                    day_close: float, trade_date) -> float:
        """
        Process a single trading day. Returns capital released (from partial/full exits).
        """
        if self.is_closed or self.remaining_qty == 0:
            return 0.0

        released = 0.0

        if self.direction == 'BUY':
            # Gap-down through SL: exit at open
            if day_open <= self.current_sl:
                released = self._full_exit(day_open, trade_date, 'SL')
                return released

            # Check T1
            if self.t1_enabled and not self.t1_hit and day_high >= self.t1:
                self.t1_hit = True
                qty = max(1, int(self.initial_qty * self.t1_qty_pct / 100))
                qty = min(qty, self.remaining_qty)
                released += self._partial_exit(self.t1, trade_date, 'T1', qty)
                if self.breakeven_t1:
                    self.current_sl = self.entry_price

            # Check T2 (only after T1)
            if self.t2_enabled and self.t1_hit and not self.t2_hit and day_high >= self.t2:
                self.t2_hit = True
                qty = max(1, int(self.initial_qty * self.t2_qty_pct / 100))
                qty = min(qty, self.remaining_qty)
                released += self._partial_exit(self.t2, trade_date, 'T2', qty)

            # Check T3 (only after T2, or T1 if T2 disabled)
            t3_prereq = (self.t2_hit if self.t2_enabled else self.t1_hit) if self.t1_enabled else True
            if self.t3_enabled and t3_prereq and not self.t3_hit and day_high >= self.t3:
                self.t3_hit = True
                released += self._full_exit(self.t3, trade_date, 'T3')
                return released

            # Check SL after target checks
            if self.remaining_qty > 0 and day_low <= self.current_sl:
                released += self._full_exit(self.current_sl, trade_date, 'SL')
                return released

            # Trailing SL update (only after T1)
            if self.trailing_sl and self.t1_hit and self.remaining_qty > 0:
                new_sl = day_close * (1 - self.trailing_sl_pct / 100)
                if new_sl > self.current_sl:
                    self.current_sl = new_sl

        else:  # SELL / SHORT
            if day_open >= self.current_sl:
                released = self._full_exit(day_open, trade_date, 'SL')
                return released

            if self.t1_enabled and not self.t1_hit and day_low <= self.t1:
                self.t1_hit = True
                qty = max(1, int(self.initial_qty * self.t1_qty_pct / 100))
                qty = min(qty, self.remaining_qty)
                released += self._partial_exit(self.t1, trade_date, 'T1', qty)
                if self.breakeven_t1:
                    self.current_sl = self.entry_price

            if self.t2_enabled and self.t1_hit and not self.t2_hit and day_low <= self.t2:
                self.t2_hit = True
                qty = max(1, int(self.initial_qty * self.t2_qty_pct / 100))
                qty = min(qty, self.remaining_qty)
                released += self._partial_exit(self.t2, trade_date, 'T2', qty)

            t3_prereq = (self.t2_hit if self.t2_enabled else self.t1_hit) if self.t1_enabled else True
            if self.t3_enabled and t3_prereq and not self.t3_hit and day_low <= self.t3:
                self.t3_hit = True
                released += self._full_exit(self.t3, trade_date, 'T3')
                return released

            if self.remaining_qty > 0 and day_high >= self.current_sl:
                released += self._full_exit(self.current_sl, trade_date, 'SL')
                return released

            if self.trailing_sl and self.t1_hit and self.remaining_qty > 0:
                new_sl = day_close * (1 + self.trailing_sl_pct / 100)
                if new_sl < self.current_sl:
                    self.current_sl = new_sl

        return released

    def force_close(self, price: float, trade_date) -> float:
        if self.is_closed or self.remaining_qty == 0:
            return 0.0
        return self._full_exit(price, trade_date, 'Strategy Exit')

    def mark_to_market_value(self, current_price: float) -> float:
        if self.direction == 'BUY':
            return self.remaining_qty * current_price
        else:
            # For short: initial invested - (current_price - entry_price) * qty
            return self.remaining_qty * (2 * self.entry_price - current_price)

    def _partial_exit(self, price: float, trade_date, exit_type: str, qty: int) -> float:
        if qty <= 0 or self.remaining_qty <= 0:
            return 0.0
        qty = min(qty, self.remaining_qty)
        cost = price * qty * TRANSACTION_COST_PCT / 100
        self.remaining_qty -= qty
        self.exits.append({
            'date': str(trade_date), 'price': price,
            'qty': qty, 'type': exit_type
        })
        if self.remaining_qty == 0:
            self.is_closed = True
            self.exit_date = trade_date
            self.exit_type = exit_type
        # Return capital: for BUY, return exit proceeds; for SELL, return margin
        proceeds = price * qty - cost
        return proceeds

    def _full_exit(self, price: float, trade_date, exit_type: str) -> float:
        proceeds = self._partial_exit(price, trade_date, exit_type, self.remaining_qty)
        self.is_closed = True
        self.exit_date = trade_date
        self.exit_type = exit_type
        return proceeds

    def compute_pnl(self) -> tuple[float, float]:
        """Returns (total_pnl, pnl_pct)"""
        if not self.exits:
            return 0.0, 0.0

        entry_cost = self.entry_price * self.initial_qty * (1 + TRANSACTION_COST_PCT / 100)
        total_proceeds = sum(e['price'] * e['qty'] for e in self.exits)
        exit_cost      = sum(e['price'] * e['qty'] * TRANSACTION_COST_PCT / 100 for e in self.exits)

        if self.direction == 'BUY':
            pnl = total_proceeds - exit_cost - entry_cost + (self.remaining_qty * self.entry_price if not self.is_closed else 0)
            # Simplified: P&L = proceeds - entry
            gross_entry = self.entry_price * self.initial_qty
            gross_exit  = total_proceeds - exit_cost
            pnl = gross_exit - gross_entry - (self.entry_price * self.initial_qty * TRANSACTION_COST_PCT / 100)
        else:
            gross_entry = self.entry_price * self.initial_qty
            gross_exit  = sum(e['price'] * e['qty'] for e in self.exits)
            pnl = gross_entry - gross_exit

        pnl_pct = (pnl / (self.entry_price * self.initial_qty)) * 100
        return round(pnl, 2), round(pnl_pct, 4)

    def weighted_exit_price(self) -> float:
        if not self.exits:
            return self.entry_price
        total_qty      = sum(e['qty'] for e in self.exits)
        weighted_total = sum(e['price'] * e['qty'] for e in self.exits)
        return round(weighted_total / total_qty, 4) if total_qty > 0 else self.entry_price

    def to_trade_record(self) -> dict:
        pnl, pnl_pct = self.compute_pnl()
        entry_date = str(self.entry_date)
        exit_date  = str(self.exit_date) if self.exit_date else None
        holding_days = 0
        try:
            if self.entry_date and self.exit_date:
                d1 = pd.to_datetime(entry_date).date() if not isinstance(self.entry_date, date_type) else self.entry_date
                d2 = pd.to_datetime(exit_date).date()  if not isinstance(self.exit_date,  date_type) else self.exit_date
                holding_days = (d2 - d1).days
        except Exception:
            pass

        return {
            'strategyName':      self.strategy_name,
            'symbol':            self.display_symbol,
            'direction':         self.direction,
            'entryDate':         entry_date,
            'entryPrice':        self.entry_price,
            'quantity':          self.initial_qty,
            'sl':                round(self.original_sl, 4),
            't1':                round(self.t1, 4),
            't2':                round(self.t2, 4),
            't3':                round(self.t3, 4),
            'exitDate':          exit_date,
            'exitPrice':         self.weighted_exit_price(),
            'remainingQty':      self.remaining_qty,
            'exitType':          self.exit_type or 'Open',
            'pnl':               pnl,
            'pnlPct':            pnl_pct,
            'holdingDays':       holding_days,
            'exits':             self.exits,
            'isClosed':          self.is_closed,
        }


# ─── Portfolio ────────────────────────────────────────────────────────────────

class Portfolio:
    def __init__(self, initial_capital: float, max_capital_per_trade_pct: float,
                 max_open_positions: int):
        self.initial_capital         = float(initial_capital)
        self.available_capital       = float(initial_capital)
        self.max_capital_per_trade_pct = float(max_capital_per_trade_pct)
        self.max_open_positions      = int(max_open_positions)

        self.open_positions: list[Position] = []
        self.closed_trades: list[dict]      = []
        self.daily_values: list[tuple]      = []   # (date, portfolio_value)
        self.invested_capital               = 0.0

    @property
    def open_symbols(self) -> set:
        return {p.symbol for p in self.open_positions}

    @property
    def can_open(self) -> bool:
        return (len(self.open_positions) < self.max_open_positions
                and self.available_capital > 0)

    def process_exits(self, data_cache: dict, trade_date) -> None:
        for pos in list(self.open_positions):
            df = data_cache.get(pos.symbol)
            if df is None:
                continue
            day_data = df[df.index == trade_date]
            if day_data.empty:
                continue
            row       = day_data.iloc[0]
            day_open  = float(row['open'])
            day_high  = float(row['high'])
            day_low   = float(row['low'])
            day_close = float(row['close'])

            released = pos.process_day(day_open, day_high, day_low, day_close, trade_date)
            self.available_capital += released

            if pos.is_closed:
                self.closed_trades.append(pos.to_trade_record())
                self.open_positions.remove(pos)

    def open_position(self, symbol: str, display_symbol: str, strategy_name: str,
                      direction: str, entry_date, entry_price: float,
                      sl: float, t1: float, t2: float, t3: float,
                      config: dict) -> bool:
        if not self.can_open:
            return False

        capital_per_trade = self.initial_capital * (self.max_capital_per_trade_pct / 100)
        capital_per_trade = min(capital_per_trade, self.available_capital)

        quantity = int(capital_per_trade / entry_price)
        if quantity <= 0:
            return False

        actual_capital = quantity * entry_price
        entry_cost     = actual_capital * TRANSACTION_COST_PCT / 100
        total_deducted = actual_capital + entry_cost

        if total_deducted > self.available_capital:
            quantity = int((self.available_capital * 0.99) / entry_price)
            if quantity <= 0:
                return False
            actual_capital = quantity * entry_price
            entry_cost     = actual_capital * TRANSACTION_COST_PCT / 100
            total_deducted = actual_capital + entry_cost

        self.available_capital -= total_deducted

        pos = Position(
            symbol=symbol, display_symbol=display_symbol,
            strategy_name=strategy_name, direction=direction,
            entry_date=entry_date, entry_price=entry_price,
            quantity=quantity, sl=sl, t1=t1, t2=t2, t3=t3,
            config=config
        )
        self.open_positions.append(pos)
        return True

    def close_all_remaining(self, data_cache: dict, last_date) -> None:
        for pos in list(self.open_positions):
            df = data_cache.get(pos.symbol)
            price = pos.entry_price
            if df is not None:
                available = df[df.index <= last_date]
                if not available.empty:
                    price = float(available['close'].iloc[-1])
            released = pos.force_close(price, last_date)
            self.available_capital += released
            self.closed_trades.append(pos.to_trade_record())
        self.open_positions.clear()

    def record_daily_value(self, data_cache: dict, trade_date) -> None:
        mtm = self.available_capital
        for pos in self.open_positions:
            df = data_cache.get(pos.symbol)
            if df is None:
                mtm += pos.remaining_qty * pos.entry_price
                continue
            day_data = df[df.index == trade_date]
            price = float(day_data['close'].iloc[0]) if not day_data.empty else pos.entry_price
            mtm += pos.mark_to_market_value(price)
        self.daily_values.append((trade_date, round(mtm, 2)))

    def get_current_mtm(self, data_cache: dict, trade_date) -> float:
        mtm = self.available_capital
        for pos in self.open_positions:
            df = data_cache.get(pos.symbol)
            if df is None:
                continue
            day_data = df[df.index == trade_date]
            if not day_data.empty:
                price = float(day_data['close'].iloc[0])
                mtm += pos.mark_to_market_value(price)
        return mtm


# ─── Backtester ───────────────────────────────────────────────────────────────

def run_backtest_v2(config: dict, user_strategy: dict, fyers=None) -> dict:
    """
    Main backtest runner.
    config keys: universe, symbol, strategy_id, period, from_date, to_date,
                 initial_capital, max_capital_per_trade_pct, max_open_positions,
                 sl_pct, t1_pct, t1_qty_pct, t1_enabled,
                 t2_pct, t2_qty_pct, t2_enabled,
                 t3_pct, t3_qty_pct, t3_enabled,
                 trailing_sl, breakeven_after_t1
    user_strategy keys: name, strategy_type, parameters, timeframe
    """
    start_dt, end_dt = _resolve_date_range(config)
    days_back = (end_dt - start_dt).days + 60  # extra buffer for indicator warmup

    # Determine universe
    universe_key = config.get('universe', 'NIFTY50')
    if universe_key == 'INDIVIDUAL':
        symbols = [config.get('symbol', '')]
    else:
        symbols = get_universe(universe_key)

    if not symbols or not symbols[0]:
        return {'error': 'No symbols in selected universe'}

    strategy_type   = user_strategy.get('strategy_type', 'ema_crossover')
    strategy_params = user_strategy.get('parameters', {})
    strategy_name   = user_strategy.get('name', 'Strategy')
    timeframe       = user_strategy.get('timeframe', 'D')

    # Normalise timeframe for Fyers: use 'D' for daily (safest for multi-stock backtest)
    fyers_resolution = timeframe if timeframe in ['5', '15', '60', 'D', 'W'] else 'D'

    print(f"[BacktesterV2] Universe: {universe_key} ({len(symbols)} symbols), "
          f"Period: {start_dt} → {end_dt}, Strategy: {strategy_name}")

    # ── Fetch historical data ──
    data_cache: dict[str, pd.DataFrame] = {}
    benchmark_df = None

    for sym in symbols:
        if not sym:
            continue
        try:
            df = fetch_historical(sym, fyers_resolution, days_back=days_back, fyers=fyers)
            if df is not None and len(df) >= 30:
                # Filter to backtest window (keep buffer for indicators)
                df = df[df.index >= pd.Timestamp(start_dt - timedelta(days=60))]
                data_cache[sym] = df
        except Exception as e:
            print(f"[BacktesterV2] Skip {sym}: {e}")

    # Fetch Nifty 50 benchmark
    try:
        benchmark_df = fetch_historical('NSE:NIFTY50-INDEX', 'D', days_back=days_back, fyers=fyers)
        if benchmark_df is not None:
            benchmark_df = benchmark_df[benchmark_df.index >= pd.Timestamp(start_dt)]
    except Exception:
        benchmark_df = None

    if not data_cache:
        return {'error': 'No data available for selected universe'}

    # ── Build sorted trading-day calendar ──
    all_dates = set()
    for df in data_cache.values():
        for d in df.index:
            dt = pd.Timestamp(d).date() if hasattr(d, 'date') else d
            if start_dt <= dt <= end_dt:
                all_dates.add(d)
    trading_days = sorted(all_dates)

    if not trading_days:
        return {'error': 'No trading days in selected period'}

    print(f"[BacktesterV2] {len(trading_days)} trading days, {len(data_cache)} symbols with data")

    # ── Initialise portfolio ──
    portfolio = Portfolio(
        initial_capital=float(config.get('initial_capital', 100000)),
        max_capital_per_trade_pct=float(config.get('max_capital_per_trade_pct', 20)),
        max_open_positions=int(config.get('max_open_positions', 5)),
    )
    position_config = {
        'sl_pct':            float(config.get('sl_pct', 2)),
        't1_enabled':        config.get('t1_enabled', True),
        't2_enabled':        config.get('t2_enabled', True),
        't3_enabled':        config.get('t3_enabled', True),
        't1_qty_pct':        float(config.get('t1_qty_pct', 30)),
        't2_qty_pct':        float(config.get('t2_qty_pct', 30)),
        't3_qty_pct':        float(config.get('t3_qty_pct', 40)),
        'breakeven_after_t1': config.get('breakeven_after_t1', False),
        'trailing_sl':       config.get('trailing_sl', False),
    }

    min_warmup_bars = 30  # minimum bars needed for indicator calculation

    # ── Main simulation loop ──
    for day_idx, trading_day in enumerate(trading_days):
        # Step 1: Process exits for existing positions
        portfolio.process_exits(data_cache, trading_day)

        # Step 2: Generate new signals
        if portfolio.can_open:
            for sym in symbols:
                if sym in portfolio.open_symbols:
                    continue
                df = data_cache.get(sym)
                if df is None:
                    continue

                # Data strictly BEFORE this trading day (no look-ahead)
                df_before = df[df.index < trading_day]
                if len(df_before) < min_warmup_bars:
                    continue

                signal = generate_signal(strategy_type, strategy_params, df_before)
                if signal == 'NEUTRAL':
                    continue

                # Entry is at the OPEN of the current trading day
                day_data = df[df.index == trading_day]
                if day_data.empty:
                    continue

                entry_price = float(day_data['open'].iloc[0])
                if entry_price <= 0:
                    continue

                sl_pct = float(config.get('sl_pct', 2))
                t1_pct = float(config.get('t1_pct', 3))
                t2_pct = float(config.get('t2_pct', 5))
                t3_pct = float(config.get('t3_pct', 7))

                if signal == 'BUY':
                    sl = entry_price * (1 - sl_pct / 100)
                    t1 = entry_price * (1 + t1_pct / 100)
                    t2 = entry_price * (1 + t2_pct / 100)
                    t3 = entry_price * (1 + t3_pct / 100)
                else:  # SELL
                    sl = entry_price * (1 + sl_pct / 100)
                    t1 = entry_price * (1 - t1_pct / 100)
                    t2 = entry_price * (1 - t2_pct / 100)
                    t3 = entry_price * (1 - t3_pct / 100)

                display = get_display_name(sym)
                opened = portfolio.open_position(
                    symbol=sym, display_symbol=display,
                    strategy_name=strategy_name, direction=signal,
                    entry_date=trading_day, entry_price=entry_price,
                    sl=sl, t1=t1, t2=t2, t3=t3,
                    config=position_config
                )
                if not portfolio.can_open:
                    break

        # Step 3: Record daily portfolio value (MTM)
        portfolio.record_daily_value(data_cache, trading_day)

    # Step 4: Close all remaining open positions at end of period
    if trading_days:
        portfolio.close_all_remaining(data_cache, trading_days[-1])

    # ── Compute results ──
    trades = portfolio.closed_trades
    if not trades:
        return {
            'error': 'No trades generated. Try adjusting your strategy parameters or extending the backtest period.',
            'summary': _empty_summary(portfolio.initial_capital),
            'trades': [],
            'equityCurve': [(str(d), v) for d, v in portfolio.daily_values],
            'benchmarkCurve': [],
        }

    summary = _compute_summary(trades, portfolio, config)
    benchmark_curve = _compute_benchmark_curve(benchmark_df, start_dt, end_dt)

    return {
        'summary':        summary,
        'trades':         trades,
        'equityCurve':    [(str(d), v) for d, v in portfolio.daily_values],
        'benchmarkCurve': benchmark_curve,
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _resolve_date_range(config: dict) -> tuple:
    period = config.get('period', '1Y')
    today  = datetime.now(IST).date()

    if period == 'CUSTOM':
        from_date = config.get('from_date', str(today - timedelta(days=365)))
        to_date   = config.get('to_date',   str(today))
        start_dt  = datetime.strptime(from_date, '%Y-%m-%d').date()
        end_dt    = datetime.strptime(to_date,   '%Y-%m-%d').date()
    elif period == '6M':
        start_dt = today - timedelta(days=183)
        end_dt   = today
    elif period == '2Y':
        start_dt = today - timedelta(days=730)
        end_dt   = today
    elif period == '3Y':
        start_dt = today - timedelta(days=1095)
        end_dt   = today
    else:  # 1Y default
        start_dt = today - timedelta(days=365)
        end_dt   = today

    return start_dt, end_dt


def _compute_summary(trades: list[dict], portfolio: Portfolio, config: dict) -> dict:
    closed   = [t for t in trades if t.get('isClosed')]
    open_pos = [t for t in trades if not t.get('isClosed')]

    total_pnl   = sum(t['pnl'] for t in closed)
    wins        = [t for t in closed if t['pnl'] > 0]
    losses      = [t for t in closed if t['pnl'] <= 0]
    win_rate    = (len(wins) / len(closed) * 100) if closed else 0
    total_return = (total_pnl / portfolio.initial_capital) * 100

    avg_win_pnl  = sum(t['pnl'] for t in wins)  / len(wins)  if wins  else 0
    avg_loss_pnl = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
    profit_factor = abs(avg_win_pnl * len(wins) / (avg_loss_pnl * len(losses))) if losses and avg_loss_pnl != 0 else float('inf')

    avg_holding = sum(t.get('holdingDays', 0) for t in closed) / len(closed) if closed else 0

    # Equity curve metrics
    values   = [v for _, v in portfolio.daily_values]
    max_dd   = _max_drawdown(values)
    sharpe   = _sharpe_ratio(values)
    sortino  = _sortino_ratio(values)

    final_capital     = values[-1] if values else portfolio.initial_capital
    invested_capital  = sum(p.remaining_qty * p.entry_price for p in portfolio.open_positions)

    return {
        'initialCapital':    round(portfolio.initial_capital, 2),
        'finalCapital':      round(final_capital, 2),
        'availableCapital':  round(portfolio.available_capital, 2),
        'investedCapital':   round(invested_capital, 2),
        'currentCapital':    round(portfolio.available_capital + invested_capital, 2),
        'totalPnL':          round(total_pnl, 2),
        'totalReturnPct':    round(total_return, 4),
        'winRate':           round(win_rate, 2),
        'totalTrades':       len(closed),
        'totalWins':         len(wins),
        'totalLosses':       len(losses),
        'openPositions':     len(open_pos),
        'maxDrawdownPct':    round(max_dd, 4),
        'sharpeRatio':       round(sharpe, 4),
        'sortinRatio':       round(sortino, 4),
        'profitFactor':      round(profit_factor, 4) if profit_factor != float('inf') else None,
        'avgHoldingDays':    round(avg_holding, 1),
        'avgWinPnL':         round(avg_win_pnl, 2),
        'avgLossPnL':        round(avg_loss_pnl, 2),
    }


def _empty_summary(initial_capital: float) -> dict:
    return {
        'initialCapital': round(initial_capital, 2),
        'finalCapital': round(initial_capital, 2),
        'availableCapital': round(initial_capital, 2),
        'investedCapital': 0.0,
        'currentCapital': round(initial_capital, 2),
        'totalPnL': 0.0, 'totalReturnPct': 0.0, 'winRate': 0.0,
        'totalTrades': 0, 'totalWins': 0, 'totalLosses': 0, 'openPositions': 0,
        'maxDrawdownPct': 0.0, 'sharpeRatio': 0.0, 'sortinRatio': 0.0,
        'profitFactor': None, 'avgHoldingDays': 0.0, 'avgWinPnL': 0.0, 'avgLossPnL': 0.0,
    }


def _max_drawdown(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    arr  = np.array(values)
    peak = np.maximum.accumulate(arr)
    dd   = (arr - peak) / peak * 100
    return abs(float(np.min(dd)))


def _sharpe_ratio(values: list[float]) -> float:
    if len(values) < 10:
        return 0.0
    arr     = np.array(values)
    returns = np.diff(arr) / arr[:-1]
    rf_daily = RISK_FREE_RATE_ANNUAL / 252
    excess   = returns - rf_daily
    if np.std(excess) == 0:
        return 0.0
    return float(np.mean(excess) / np.std(excess) * np.sqrt(252))


def _sortino_ratio(values: list[float]) -> float:
    if len(values) < 10:
        return 0.0
    arr      = np.array(values)
    returns  = np.diff(arr) / arr[:-1]
    rf_daily = RISK_FREE_RATE_ANNUAL / 252
    excess   = returns - rf_daily
    downside = excess[excess < 0]
    if len(downside) == 0 or np.std(downside) == 0:
        return 0.0
    return float(np.mean(excess) / np.std(downside) * np.sqrt(252))


def _compute_benchmark_curve(benchmark_df: Optional[pd.DataFrame],
                              start_dt, end_dt) -> list[list]:
    if benchmark_df is None or benchmark_df.empty:
        return []
    try:
        filtered = benchmark_df[
            (benchmark_df.index >= pd.Timestamp(start_dt)) &
            (benchmark_df.index <= pd.Timestamp(end_dt))
        ]
        if filtered.empty:
            return []
        base  = float(filtered['close'].iloc[0])
        result = []
        for idx, row in filtered.iterrows():
            pct = (float(row['close']) - base) / base * 100
            result.append([str(idx), round(pct, 4)])
        return result
    except Exception:
        return []
