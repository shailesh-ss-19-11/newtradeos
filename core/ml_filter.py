"""
ML Signal Filter — trains a lightweight model on historical trade data
to predict whether a new signal is likely to be profitable.

Uses scikit-learn (LogisticRegression) on features extracted from the
strategy votes already stored in the DB. Falls back to PASS when there
is insufficient training data (<30 closed trades).

Install: pip install scikit-learn (added to requirements.txt)
"""

import os
import json
import pickle
import numpy as np
from typing import Optional

_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           'data', 'ml_model.pkl')
_MIN_SAMPLES = 30       # Need at least this many closed trades before training
_model       = None
_trained_at  = None


_STRATEGY_NAMES = [
    'candlestick', 'trend', 'momentum', 'breakout',
    'support_resistance', 'volume', 'reversal', 'options'
]

_SIGNAL_MAP = {'BUY': 1, 'SELL': -1, 'NEUTRAL': 0}


def _extract_features(signal: dict) -> Optional[np.ndarray]:
    """
    Convert a signal dict into a numeric feature vector.
    Features: 8 strategy signals + votes_count + confidence + rr_ratio + vol_ratio
    """
    strategies = signal.get('strategies', {})
    features = []

    for name in _STRATEGY_NAMES:
        s = strategies.get(name, {})
        sig_val = _SIGNAL_MAP.get(s.get('signal', 'NEUTRAL'), 0)
        strength = float(s.get('strength', 0)) / 10.0   # normalise 0-1
        features.extend([sig_val, strength])

    votes_raw = signal.get('votes', '0/8')
    try:
        votes_num = int(str(votes_raw).split('/')[0])
    except Exception:
        votes_num = signal.get('votesCount', 0) or 0
    features.append(votes_num / 8.0)

    conf_map = {'HIGH': 1.0, 'MEDIUM': 0.6, 'LOW': 0.3}
    features.append(conf_map.get(signal.get('confidence', 'LOW'), 0.3))

    rr = min(float(signal.get('riskReward', 1.5)), 5.0) / 5.0
    features.append(rr)

    vol_ratio = min(float(signal.get('volRatio', 1.0)), 3.0) / 3.0
    features.append(vol_ratio)

    return np.array(features, dtype=np.float32)


def _load_training_data():
    """Pull closed trades from DB and convert to (X, y) arrays."""
    try:
        from core.db_storage import load_trades
        data = load_trades()
        closed = [t for t in data['trades']
                  if t.get('status') == 'CLOSED' and t.get('isProfit') is not None
                  and t.get('strategies')]

        if len(closed) < _MIN_SAMPLES:
            return None, None

        X, y = [], []
        for t in closed:
            feat = _extract_features(t)
            if feat is not None:
                X.append(feat)
                y.append(1 if t.get('isProfit') else 0)

        return np.array(X), np.array(y)
    except Exception:
        return None, None


def train() -> bool:
    """Train or retrain the model. Returns True on success."""
    global _model, _trained_at
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
        from sklearn.model_selection import cross_val_score

        X, y = _load_training_data()
        if X is None or len(X) < _MIN_SAMPLES:
            print(f"[MLFilter] Not enough data ({0 if X is None else len(X)} trades, need {_MIN_SAMPLES})")
            return False

        pipe = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(C=1.0, max_iter=500, random_state=42))
        ])
        pipe.fit(X, y)

        # Cross-val score
        try:
            cv_scores = cross_val_score(pipe, X, y, cv=min(5, len(X)//6 + 1), scoring='accuracy')
            accuracy  = round(float(cv_scores.mean()), 3)
        except Exception:
            accuracy = 0.0

        os.makedirs(os.path.dirname(_MODEL_PATH), exist_ok=True)
        with open(_MODEL_PATH, 'wb') as f:
            pickle.dump({'model': pipe, 'accuracy': accuracy, 'n_samples': len(X)}, f)

        _model      = pipe
        _trained_at = accuracy
        print(f"[MLFilter] Model trained on {len(X)} trades | CV accuracy: {accuracy:.1%}")
        return True

    except ImportError:
        print("[MLFilter] scikit-learn not installed — run: pip install scikit-learn")
        return False
    except Exception as e:
        print(f"[MLFilter] Training failed: {e}")
        return False


def _load_model():
    global _model
    if _model is not None:
        return _model
    if os.path.exists(_MODEL_PATH):
        try:
            with open(_MODEL_PATH, 'rb') as f:
                data = pickle.load(f)
            _model = data['model']
            return _model
        except Exception:
            pass
    return None


def predict(signal: dict) -> dict:
    """
    Returns:
        allowed: bool
        probability: float (0-1, probability of profit)
        reason: str
    """
    model = _load_model()
    if model is None:
        return {'allowed': True, 'probability': 0.5, 'reason': 'ML model not trained yet — PASS'}

    try:
        feat = _extract_features(signal)
        if feat is None:
            return {'allowed': True, 'probability': 0.5, 'reason': 'Feature extraction failed — PASS'}

        prob = float(model.predict_proba(feat.reshape(1, -1))[0][1])

        # Block signals with < 55% predicted probability of profit
        allowed = prob >= 0.55
        reason  = (
            f"ML score: {prob:.1%} — {'PASS' if allowed else 'BLOCKED (below 55% threshold)'}"
        )
        return {'allowed': allowed, 'probability': round(prob, 3), 'reason': reason}

    except Exception as e:
        return {'allowed': True, 'probability': 0.5, 'reason': f'ML predict error: {e} — PASS'}
