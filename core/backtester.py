import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
from typing import Optional
import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_fetcher import fetch_historical
from core.db_storage import save_backtest_results, save_error
from core.db_storage import load_config
from core.risk_calculator import calculate as calc_risk
from strategies import (
    candlestick_patterns, trend_strategies, momentum_strategies,
    breakout_strategies, support_resistance, volume_strategies,
    reversal_strategies, options_strategies
)

IST = pytz.timezone('Asia/Kolkata')


def _run_strategies_on_slice(df_slice: pd.DataFrame, symbol: str) -> dict:
    results = {
        'candlestick': candlestick_patterns.analyze(df_slice),
        'trend': trend_strategies.analyze(df_slice),
        'momentum': momentum_strategies.analyze(df_slice),
        'breakout': breakout_strategies.analyze(df_slice),
        'support_resistance': support_resistance.analyze(df_slice),
        'volume': volume_strategies.analyze(df_slice),
        'reversal': reversal_strategies.analyze(df_slice),
        'options': {'signal': 'NEUTRAL', 'strength': 0, 'applicable': False}
    }
    return results


def _apply_gates(results: dict, signal: str, vol_ratio: float, rr: float,
                 min_strategies: int = 4, min_rr: float = 1.5) -> tuple[bool, dict]:
    gate_stats = {f'gate{i}': 0 for i in range(1, 9)}

    buy_votes = sum(1 for r in results.values() if r.get('signal') == 'BUY')
    sell_votes = sum(1 for r in results.values() if r.get('signal') == 'SELL')
    votes = buy_votes if signal == 'BUY' else sell_votes

    if votes < min_strategies:
        gate_stats['gate1'] = 1
        return False, gate_stats

    if vol_ratio < 0.7:
        gate_stats['gate2'] = 1
        return False, gate_stats

    if rr < min_rr:
        gate_stats['gate8'] = 1
        return False, gate_stats

    return True, gate_stats


def simulate_trade(df: pd.DataFrame, entry_idx: int, signal_type: str,
                   entry_price: float, stop_loss: float, t1: float, t2: float, t3: float) -> dict:
    t1_hit = t2_hit = t3_hit = False
    exit_price = stop_loss
    exit_reason = 'SL_HIT'
    exit_idx = entry_idx

    for i in range(entry_idx + 1, len(df)):
        candle_high = df['high'].iloc[i]
        candle_low = df['low'].iloc[i]
        candle_close = df['close'].iloc[i]

        if signal_type == 'BUY':
            if candle_low <= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL_HIT'
                exit_idx = i
                break
            if not t1_hit and candle_high >= t1:
                t1_hit = True
                stop_loss = entry_price  # move SL to breakeven after T1
            if not t2_hit and t1_hit and candle_high >= t2:
                t2_hit = True
                stop_loss = t1  # move SL to T1 after T2
            if t1_hit and t2_hit and candle_high >= t3:
                t3_hit = True
                exit_price = t3
                exit_reason = 'T3_HIT'
                exit_idx = i
                break
        else:  # SELL
            if candle_high >= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL_HIT'
                exit_idx = i
                break
            if not t1_hit and candle_low <= t1:
                t1_hit = True
                stop_loss = entry_price
            if not t2_hit and t1_hit and candle_low <= t2:
                t2_hit = True
                stop_loss = t1
            if t1_hit and t2_hit and candle_low <= t3:
                t3_hit = True
                exit_price = t3
                exit_reason = 'T3_HIT'
                exit_idx = i
                break

    if exit_reason not in ['T3_HIT', 'SL_HIT']:
        exit_price = df['close'].iloc[-1]
        exit_reason = 'EOD'
        exit_idx = len(df) - 1

    if signal_type == 'BUY':
        pnl_r = (exit_price - entry_price) / (entry_price - stop_loss) if entry_price != stop_loss else 0
    else:
        pnl_r = (entry_price - exit_price) / (stop_loss - entry_price) if stop_loss != entry_price else 0

    return {
        'exit_price': exit_price,
        'exit_reason': exit_reason,
        'exit_idx': exit_idx,
        't1_hit': t1_hit,
        't2_hit': t2_hit,
        't3_hit': t3_hit,
        'pnl_r': round(pnl_r, 3),
        'is_win': pnl_r > 0
    }


def run_backtest(fyers=None, account_balance: float = 500000) -> dict:
    if fyers is None:
        from auth.fyers_auth import get_fyers_client
        fyers = get_fyers_client()

    cfg = load_config()
    syms_cfg = cfg.get('symbols', {})
    symbols = syms_cfg.get('equity', []) + syms_cfg.get('indices', [])

    all_trades = []
    gate_rejections = {f'filteredByGate{i}': 0 for i in range(1, 9)}
    total_signals = 0
    per_symbol = {}

    equity_curve = [account_balance]
    running_balance = account_balance

    print(f"[Backtester] Starting backtest on {len(symbols)} symbols...")

    for sym_idx, symbol in enumerate(symbols):
        if sym_idx % 10 == 0 and sym_idx > 0:
            print(f"[Backtester] Progress: {sym_idx}/{len(symbols)} symbols processed...")

        df = fetch_historical(symbol, 'D', days_back=365, fyers=fyers)
        if df is None or len(df) < 60:
            print(f"[Backtester] Skipping {symbol}: insufficient data")
            continue

        sym_trades = []
        min_window = 50

        for i in range(min_window, len(df)):
            df_slice = df.iloc[:i].copy()

            if len(df_slice) < 30:
                continue

            try:
                results = _run_strategies_on_slice(df_slice, symbol)
            except Exception:
                continue

            buy_votes = sum(1 for r in results.values() if r.get('signal') == 'BUY')
            sell_votes = sum(1 for r in results.values() if r.get('signal') == 'SELL')

            if buy_votes > sell_votes and buy_votes >= 4:
                signal_type = 'BUY'
                votes = buy_votes
            elif sell_votes > buy_votes and sell_votes >= 4:
                signal_type = 'SELL'
                votes = sell_votes
            else:
                continue

            vol_ratio = results['volume'].get('vol_ratio', 1.0)
            entry_price = float(df.iloc[i]['open']) if i < len(df) else float(df_slice['close'].iloc[-1])

            risk_data = calc_risk(
                df=df_slice,
                signal_type=signal_type,
                entry_price=entry_price,
                account_balance=account_balance
            )
            if not risk_data:
                continue

            rr = risk_data.get('riskReward', 0)
            passed, gate_info = _apply_gates(results, signal_type, vol_ratio, rr)
            total_signals += 1

            for gate_key, rejected in gate_info.items():
                if rejected:
                    gate_num = gate_key.replace('gate', '')
                    rejection_key = f'filteredByGate{gate_num}'
                    gate_rejections[rejection_key] = gate_rejections.get(rejection_key, 0) + 1

            if not passed:
                continue

            trade_result = simulate_trade(
                df=df.iloc[i:].copy() if i < len(df) else df_slice,
                entry_idx=0,
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=risk_data['stopLoss'],
                t1=risk_data['target1'],
                t2=risk_data['target2'],
                t3=risk_data['target3']
            )

            risk_amount = account_balance * 0.01
            pnl = trade_result['pnl_r'] * risk_amount
            running_balance += pnl
            equity_curve.append(round(running_balance, 2))

            trade_entry = {
                'symbol': symbol,
                'type': signal_type,
                'date': str(df_slice.index[-1].date()) if hasattr(df_slice.index[-1], 'date') else str(df_slice.index[-1]),
                'entryPrice': entry_price,
                'stopLoss': risk_data['stopLoss'],
                'target1': risk_data['target1'],
                'target2': risk_data['target2'],
                'target3': risk_data['target3'],
                'exitPrice': trade_result['exit_price'],
                'exitReason': trade_result['exit_reason'],
                'pnlR': trade_result['pnl_r'],
                'pnl': round(pnl, 2),
                'isWin': trade_result['is_win'],
                'votes': votes,
                'volRatio': vol_ratio
            }
            all_trades.append(trade_entry)
            sym_trades.append(trade_entry)

        if sym_trades:
            wins = [t for t in sym_trades if t['isWin']]
            sym_pnl = sum(t['pnl'] for t in sym_trades)
            per_symbol[symbol] = {
                'totalTrades': len(sym_trades),
                'winRate': round(len(wins) / len(sym_trades) * 100, 2),
                'totalPnL': round(sym_pnl, 2),
                'avgR': round(np.mean([t['pnlR'] for t in sym_trades]), 3)
            }

        print(f"[Backtester] {symbol}: {len(sym_trades)} trades")

    # Aggregate statistics
    if not all_trades:
        print("[Backtester] No trades generated.")
        results_dict = {'error': 'No trades generated', 'generatedAt': datetime.now(IST).isoformat()}
        save_backtest_results(results_dict)
        return results_dict

    total_closed = len(all_trades)
    wins = [t for t in all_trades if t['isWin']]
    losses = [t for t in all_trades if not t['isWin']]
    win_rate = len(wins) / total_closed * 100 if total_closed > 0 else 0

    avg_win = np.mean([t['pnlR'] for t in wins]) if wins else 0
    avg_loss = abs(np.mean([t['pnlR'] for t in losses])) if losses else 0
    avg_r = np.mean([t['pnlR'] for t in all_trades])

    loss_rate = 1 - win_rate / 100
    expectancy = (win_rate / 100 * avg_win) - (loss_rate * avg_loss)

    total_pnl = sum(t['pnl'] for t in all_trades)
    risk_amount = account_balance * 0.01

    # Max drawdown
    equity_arr = np.array(equity_curve)
    peak = np.maximum.accumulate(equity_arr)
    drawdown = (equity_arr - peak) / peak * 100
    max_drawdown = abs(float(np.min(drawdown)))

    # Sharpe ratio (simplified)
    pnl_series = [t['pnl'] for t in all_trades]
    if len(pnl_series) > 1 and np.std(pnl_series) > 0:
        sharpe = (np.mean(pnl_series) / np.std(pnl_series)) * np.sqrt(252)
    else:
        sharpe = 0

    # Calmar ratio
    annualized_return = total_pnl / account_balance * 100
    calmar = annualized_return / max_drawdown if max_drawdown > 0 else 0

    # Max consecutive losses
    max_consec_losses = 0
    curr_consec = 0
    for t in all_trades:
        if not t['isWin']:
            curr_consec += 1
            max_consec_losses = max(max_consec_losses, curr_consec)
        else:
            curr_consec = 0

    best_trade = max(all_trades, key=lambda t: t['pnl'])
    worst_trade = min(all_trades, key=lambda t: t['pnl'])

    results_dict = {
        'winRate': round(win_rate, 2),
        'avgR': round(avg_r, 3),
        'totalPnL': round(total_pnl, 2),
        'totalSignals': total_signals,
        'totalTrades': total_closed,
        'maxConsecutiveLosses': max_consec_losses,
        'maxDrawdownPercent': round(max_drawdown, 2),
        'sharpeRatio': round(sharpe, 3),
        'calmarRatio': round(calmar, 3),
        'expectancy': round(expectancy, 3),
        'annualizedReturnPct': round(annualized_return, 2),
        'perSymbol': per_symbol,
        'equityCurve': equity_curve,
        'bestTrade': {
            'symbol': best_trade['symbol'],
            'pnl': best_trade['pnl'],
            'date': best_trade['date']
        },
        'worstTrade': {
            'symbol': worst_trade['symbol'],
            'pnl': worst_trade['pnl'],
            'date': worst_trade['date']
        },
        'gateRejections': gate_rejections,
        'generatedAt': datetime.now(IST).isoformat()
    }

    save_backtest_results(results_dict)
    print(f"\n[Backtester] Complete! {total_closed} trades, Win Rate: {win_rate:.1f}%, Total P&L: ₹{total_pnl:.0f}")
    return results_dict


if __name__ == '__main__':
    print("Running backtester...")
    results = run_backtest()
    print(f"Results saved to data/backtest_results.json")
