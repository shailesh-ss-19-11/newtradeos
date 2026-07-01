"""
Order Executor — paper trading and live order placement via Fyers API.

Set TRADING_MODE=paper in .env for safe simulation.
Set TRADING_MODE=live to actually place orders (requires confirmed Fyers session).

Paper trades are stored in the same DB with source='PAPER'.
Live orders call fyers.place_order() and track order IDs.
"""

import os
import json
from datetime import datetime
from typing import Optional
import pytz
from dotenv import load_dotenv

load_dotenv()

IST = pytz.timezone('Asia/Kolkata')
TRADING_MODE = os.getenv('TRADING_MODE', 'paper').lower()  # 'paper' | 'live'


def _fmt(v):
    return f"₹{float(v):,.2f}" if v is not None else 'N/A'


class PaperOrder:
    """Simulates a filled order instantly at signal price."""

    def place(self, signal: dict) -> dict:
        now = datetime.now(IST)
        order_id = f"PAPER-{now.strftime('%Y%m%d%H%M%S')}-{signal.get('displaySymbol', 'SYM')}"
        filled_price = signal.get('entryPrice', 0)

        result = {
            'orderId':     order_id,
            'status':      'FILLED',
            'mode':        'paper',
            'symbol':      signal.get('symbol'),
            'type':        signal.get('type'),
            'qty':         signal.get('positionSize', 0),
            'filledPrice': filled_price,
            'filledAt':    now.isoformat(),
        }
        print(
            f"[PaperOrder] {signal.get('type')} {signal.get('displaySymbol')} "
            f"× {signal.get('positionSize')} @ {_fmt(filled_price)} — SIMULATED"
        )
        return result

    def cancel(self, order_id: str) -> dict:
        return {'orderId': order_id, 'status': 'CANCELLED', 'mode': 'paper'}


class LiveOrder:
    """Places real bracket orders via Fyers API."""

    def __init__(self, fyers_client):
        self.fyers = fyers_client

    def place(self, signal: dict) -> dict:
        if self.fyers is None:
            raise RuntimeError("Fyers client not available for live order")

        symbol    = signal.get('symbol', '')
        qty       = int(signal.get('positionSize', 0))
        side      = 1 if signal.get('type') == 'BUY' else -1
        ltp       = signal.get('entryPrice', 0)
        sl_price  = signal.get('stopLoss', 0)
        tgt_price = signal.get('target1', 0)

        if qty <= 0:
            raise ValueError(f"Invalid quantity {qty} for {symbol}")

        # Fyers bracket order format
        order_data = {
            "symbol":         symbol,
            "qty":            qty,
            "type":           2,          # Market order
            "side":           side,
            "productType":    "BO",       # Bracket Order
            "limitPrice":     0,
            "stopPrice":      0,
            "validity":       "DAY",
            "disclosedQty":   0,
            "offlineOrder":   False,
            "stopLoss":       round(abs(ltp - sl_price), 2),
            "takeProfit":     round(abs(tgt_price - ltp), 2),
        }

        try:
            response = self.fyers.place_order(data=order_data)
            order_id = response.get('id', '')
            status   = 'PLACED' if response.get('s') == 'ok' else 'FAILED'
            print(
                f"[LiveOrder] {signal.get('type')} {symbol} × {qty} "
                f"@ market | Status: {status} | ID: {order_id}"
            )
            return {
                'orderId':      order_id,
                'status':       status,
                'mode':         'live',
                'symbol':       symbol,
                'type':         signal.get('type'),
                'qty':          qty,
                'filledPrice':  ltp,
                'filledAt':     datetime.now(IST).isoformat(),
                'rawResponse':  response,
            }
        except Exception as e:
            print(f"[LiveOrder] Order failed for {symbol}: {e}")
            return {
                'orderId': None, 'status': 'ERROR',
                'mode': 'live', 'error': str(e)
            }

    def cancel(self, order_id: str) -> dict:
        try:
            response = self.fyers.cancel_order(data={"id": order_id})
            return {'orderId': order_id, 'status': 'CANCELLED', 'rawResponse': response}
        except Exception as e:
            return {'orderId': order_id, 'status': 'ERROR', 'error': str(e)}


def get_executor(fyers_client=None):
    """Factory — returns the right executor based on TRADING_MODE env var."""
    mode = os.getenv('TRADING_MODE', 'paper').lower()
    if mode == 'live':
        if fyers_client is None:
            print("[OrderExecutor] WARNING: live mode requested but no Fyers client — falling back to paper")
            return PaperOrder(), 'paper'
        return LiveOrder(fyers_client), 'live'
    return PaperOrder(), 'paper'


def execute_signal(signal: dict, fyers_client=None) -> Optional[dict]:
    """
    Place an order for a signal. Returns order result dict or None on failure.
    """
    try:
        executor, mode = get_executor(fyers_client)
        result = executor.place(signal)
        result['mode'] = mode
        return result
    except Exception as e:
        print(f"[OrderExecutor] execute_signal failed: {e}")
        return None


def cancel_order(order_id: str, fyers_client=None) -> dict:
    executor, _ = get_executor(fyers_client)
    return executor.cancel(order_id)
