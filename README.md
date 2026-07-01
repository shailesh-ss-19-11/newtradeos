# Stock & Options Trading Prediction System

A professional-grade, fully automated trading signal generation system for Indian markets (NSE/BSE) using Fyers API v3, 8 independent strategy modules, multi-timeframe analysis, and Telegram notifications.

---

## PREREQUISITES

### 1. Fyers Trading Account
- Active Fyers trading account at [fyers.in](https://fyers.in)
- Enable TOTP 2FA at **https://myaccount.fyers.in/ManageAccount**
  - Go to Security → 2-Factor Authentication → Enable TOTP
  - During setup, you will see a QR code and a **secret key string** (e.g., `JBSWY3DPEHPK3PXP`)
  - Copy this secret key — this is your `FYERS_TOTP_KEY`
  - Use any authenticator app (Google Authenticator, Authy) to scan the QR

### 2. Fyers API App
- Go to **https://myapi.fyers.in/dashboard**
- Create a new app
- Set redirect URI to: `https://trade.fyers.in/api-login/redirect-uri/index.html`
- Copy your **App ID** (format: `ABC123-100`) → this is `FYERS_CLIENT_ID`
- Copy the **Secret Key** → this is `FYERS_SECRET_KEY`

### 3. System Requirements
- Python 3.9 or higher
- pip package manager
- Telegram account (for notifications)

---

## SETUP

### Step 1: Get the code
```bash
# Copy the trading-system folder or clone the repository
cd trading-system
```

### Step 2: Create a virtual environment
```bash
python -m venv venv
```

### Step 3: Activate the virtual environment
```bash
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### Step 4: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Configure environment variables
Edit the `.env` file and fill in every value:

```env
FYERS_CLIENT_ID=ABC123-100          # Your App ID from myapi.fyers.in
FYERS_SECRET_KEY=your_secret_key    # Secret key from your API app
FYERS_REDIRECT_URI=https://trade.fyers.in/api-login/redirect-uri/index.html
FYERS_USERNAME=XY12345              # Your Fyers Client ID (login username)
FYERS_PIN=1234                      # Your 4-digit Fyers PIN
FYERS_TOTP_KEY=JBSWY3DPEHPK3PXP    # TOTP secret key from 2FA setup
TELEGRAM_BOT_TOKEN=123456:ABC...    # From @BotFather on Telegram
TELEGRAM_CHAT_ID=987654321          # Your Telegram user/chat ID
ACCOUNT_BALANCE=500000              # Your trading capital in INR
```

### Step 6: Initialize data files
```bash
python -c "from core.file_storage import init_data_files; init_data_files()"
```

### Step 7: Test authentication
```bash
python auth/fyers_auth.py
```
This runs the full auto-login flow. If successful, you'll see your name printed.

---

## RUNNING THE SYSTEM

### Terminal 1 — Scanner (signal generation)
```bash
python scanner.py
```
The scanner starts the scheduler and runs immediately on launch to test authentication.

### Terminal 2 — Flask API (REST endpoints)
```bash
python app.py
```
API is available at: `http://localhost:5000/api`

### Terminal 3 — Backtester (optional, one-time)
```bash
python core/backtester.py
```
Runs full historical backtest over all watchlist symbols. Results saved to `data/backtest_results.json`.

---

## FYERS SYMBOL FORMAT

| Type | Format | Example |
|------|--------|---------|
| NSE Equity | `NSE:SYMBOL-EQ` | `NSE:RELIANCE-EQ` |
| BSE Equity | `BSE:SYMBOL-EQ` | `BSE:RELIANCE-EQ` |
| NSE Index | `NSE:NAME-INDEX` | `NSE:NIFTY50-INDEX` |
| NSE Futures | `NSE:SYMBOL+YYMMM+FUT` | `NSE:NIFTY25JUNFUT` |
| NSE Options | `NSE:SYMBOL+YY+MM+DD+STRIKE+CE/PE` | `NSE:NIFTY2561524750CE` |

### Resolution Codes for Historical API
`1`, `2`, `3`, `5`, `10`, `15`, `20`, `30`, `60`, `120`, `240`, `D`, `W`, `M`

---

## TELEGRAM BOT SETUP

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow prompts to name your bot
4. Copy the **bot token** (format: `1234567890:ABCdef...`) → `TELEGRAM_BOT_TOKEN`
5. Open Telegram and search for **@userinfobot**
6. Send `/start` to get your **chat ID** (a number like `987654321`) → `TELEGRAM_CHAT_ID`
7. Start your bot by sending it any message (search for your bot by its username)

---

## API REFERENCE

Base URL: `http://localhost:5000/api`

### Trades

```bash
# Get all trades (paginated)
curl "http://localhost:5000/api/trades"

# Get active trades only
curl "http://localhost:5000/api/trades?status=ACTIVE"

# Get trades by date
curl "http://localhost:5000/api/trades?date=2024-01-15"

# Get trades in date range
curl "http://localhost:5000/api/trades?from_date=2024-01-01&to_date=2024-01-31"

# Get trades for a symbol
curl "http://localhost:5000/api/trades?symbol=RELIANCE"

# Get single trade
curl "http://localhost:5000/api/trades/TRD-20240115-001"

# Get trades by date (route)
curl "http://localhost:5000/api/trades/date/2024-01-15"

# Get trades by symbol (route)
curl "http://localhost:5000/api/trades/symbol/NSE:RELIANCE-EQ"

# Manually close a trade
curl -X POST "http://localhost:5000/api/trades/TRD-20240115-001/close" \
  -H "Content-Type: application/json" \
  -d '{"exitPrice": 2500.50, "exitReason": "MANUAL_CLOSE"}'

# Update trade (add notes, etc.)
curl -X POST "http://localhost:5000/api/trades/TRD-20240115-001/update" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Exited early due to news"}'
```

### Summary

```bash
# Overall summary
curl "http://localhost:5000/api/summary"

# Daily summary
curl "http://localhost:5000/api/summary/date/2024-01-15"

# Weekly summary (last 7 days)
curl "http://localhost:5000/api/summary/weekly"

# Monthly summary (last 30 days)
curl "http://localhost:5000/api/summary/monthly"
```

### Backtest

```bash
# Get backtest results
curl "http://localhost:5000/api/backtest/results"

# Run backtest (spawns background process)
curl -X POST "http://localhost:5000/api/backtest/run"
```

### Watchlist

```bash
# Get full watchlist
curl "http://localhost:5000/api/watchlist"

# Add equity symbol
curl -X POST "http://localhost:5000/api/watchlist/equity" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "NSE:TATASTEEL-EQ"}'

# Remove equity symbol
curl -X DELETE "http://localhost:5000/api/watchlist/equity/NSE:TATASTEEL-EQ"

# Add index
curl -X POST "http://localhost:5000/api/watchlist/index" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "NSE:NIFTYBANK-INDEX"}'
```

### Options

```bash
# Get live option chain for NIFTY
curl "http://localhost:5000/api/options/NSE:NIFTY50-INDEX"

# Get live option chain for BANKNIFTY
curl "http://localhost:5000/api/options/NSE:NIFTYBANK-INDEX"
```

### Market

```bash
# Market open/close status
curl "http://localhost:5000/api/market/status"

# Live quotes for symbols
curl "http://localhost:5000/api/market/quotes?symbols=NSE:RELIANCE-EQ,NSE:TCS-EQ"
```

### System

```bash
# Health check
curl "http://localhost:5000/api/health"

# Last 50 errors
curl "http://localhost:5000/api/errors"
```

---

## CONFIG REFERENCE (config/config.json)

```json
{
  "trading": {
    "accountBalance": 500000,        // Capital in INR (also set in .env)
    "maxRiskPerTrade": 0.01,         // 1% of account per trade maximum loss
    "minStrategiesConfirmed": 4,     // Minimum strategies to agree (out of 8)
    "minRiskReward": 1.5,            // Minimum R:R ratio (1.5 means 1.5:1)
    "maxActiveTrades": 5,            // Maximum concurrent open positions
    "maxDailyLoss": 0.03             // Stop trading if day loss exceeds 3%
  },
  "market": {
    "timezone": "Asia/Kolkata",      // IST timezone
    "openTime": "09:15",             // NSE market open
    "closeTime": "15:30",            // NSE market close
    "signalCutoffTime": "15:20",     // No new signals after this time
    "preMarketTime": "09:00"         // Pre-market scan time
  },
  "scanning": {
    "intervalMinutes": 5,            // Scan every 5 minutes
    "timeframe": "15",               // Primary timeframe (15-min candles)
    "multiTimeframe": ["5", "15", "60"]  // All timeframes analyzed
  }
}
```

---

## WATCHLIST MANAGEMENT

### Via API (recommended for live system):
```bash
# Add a new equity
curl -X POST http://localhost:5000/api/watchlist/equity \
  -H "Content-Type: application/json" \
  -d '{"symbol": "NSE:LTIM-EQ"}'

# Remove a symbol
curl -X DELETE http://localhost:5000/api/watchlist/equity/NSE:LTIM-EQ
```

### Directly editing data/watchlist.json:
```json
{
  "equity": ["NSE:RELIANCE-EQ", "NSE:TCS-EQ"],
  "indices": ["NSE:NIFTY50-INDEX"],
  "options_underlying": ["NSE:NIFTY50-INDEX"]
}
```
Restart the scanner after direct edits.

---

## UNDERSTANDING SIGNALS

### The 8-Strategy Voting System

Every scan runs all 8 independent strategy modules on the 15-minute timeframe:

| # | Module | What it analyzes |
|---|--------|-----------------|
| 1 | Candlestick Patterns | 30+ price action patterns (Hammer, Engulfing, Stars, etc.) |
| 2 | Trend Strategies | EMA crossovers, ADX, Supertrend, Ichimoku, PSAR, HMA |
| 3 | Momentum Strategies | RSI, MACD, Stochastic, CCI, Williams %R, MFI, TSI + divergences |
| 4 | Breakout Strategies | Bollinger Bands, Keltner, Donchian, ORB, PDH/PDL, 52-wk high |
| 5 | Support & Resistance | Pivot points, Fibonacci, Camarilla, Horizontal S/R, Options OI |
| 6 | Volume Strategies | VWAP, Volume spike, OBV, CMF, A/D line, Volume profile |
| 7 | Reversal Patterns | Double/Triple top-bottom, H&S, Wedges, Triangles, Cup & Handle |
| 8 | Options Strategies | Max pain, PCR, OI walls, IV skew (indices only) |

Each module returns BUY, SELL, or NEUTRAL. The vote count determines if a signal is generated.

### The 8 Gates (all must pass)

1. **Gate 1 — Strategy Votes**: ≥4 out of 8 modules must agree on same direction
2. **Gate 2 — Volume**: Volume ratio must be ≥0.7x average (no low-volume signals)
3. **Gate 3 — HTF Trend**: 60-min trend must not oppose the signal direction
4. **Gate 4 — Market Hours**: IST time must be between 09:15 and 15:20 on weekdays
5. **Gate 5 — No Duplicate**: No existing ACTIVE trade for the same symbol
6. **Gate 6 — Daily Loss**: Today's losses must not exceed 3% of account
7. **Gate 7 — Max Trades**: Active trade count must be below maximum (5)
8. **Gate 8 — Risk/Reward**: Signal's R:R ratio must be ≥1.5

### Confidence Levels
- **HIGH**: 7-8 strategies agree
- **MEDIUM**: 5-6 strategies agree
- **LOW**: 4 strategies agree (minimum threshold)

---

## RISK MANAGEMENT

### The 1% Rule
- Maximum risk per trade = 1% of account balance
- Example: ₹5,00,000 account → max loss per trade = ₹5,000

### ATR-Based Stops
- Stop loss = Entry ± (ATR14 × 1.5)
- Also checks nearest support/resistance level
- Tighter of the two is used

### R Multiples (Reward targets)
- **Target 1**: 1.5R (1.5× the risk amount)
- **Target 2**: 2.5R
- **Target 3**: 4.0R
- **Target 4-5**: Fibonacci extensions (127.2% and 161.8%)

### Position Sizing
```
Position Size = Floor(Account × 1% / Risk Per Share)
```
Example: ₹5,000 max loss ÷ ₹50 risk/share = 100 shares

### Trade Monitoring
- System checks active trades every scan cycle (5 min)
- On SL hit: trade closed automatically, Telegram alert sent
- On target hit: partial profit alert sent, SL moved up
- At 15:35: all remaining trades closed at market price (EOD rule)

---

## TROUBLESHOOTING

### Fyers Login Fails
```
❌ Login failed: verify_otp error
```
- Check `FYERS_TOTP_KEY` — must be the secret string from 2FA setup, not the 6-digit code
- Check `FYERS_USERNAME` — this is your Fyers Client ID (e.g., XY12345), not email
- Check `FYERS_PIN` — your 4-digit PIN used to login to Fyers app
- TOTP codes are time-sensitive — ensure your system clock is synchronized (NTP)
- Run `python -c "import pyotp; print(pyotp.TOTP('YOUR_KEY').now())"` to verify TOTP works

### No Signals Generated
```
[Scanner] Main scan complete. No signals.
```
- Verify market is open (weekdays 09:15-15:20 IST)
- Check `data/errors.json` for any API errors
- Volume gate is common: low-volume symbols below 0.7× average are blocked
- Increase minimum strategies to check: look at individual strategy outputs
- Try reducing `minStrategiesConfirmed` in config from 4 to 3 (not recommended for production)

### Telegram Not Sending
```
[Telegram] Token/ChatID not configured
```
- Verify `TELEGRAM_BOT_TOKEN` format: `1234567890:ABCdefGHI...`
- Verify `TELEGRAM_CHAT_ID` is your numeric ID (not @username)
- Send a message to your bot first to initiate the chat
- Check if bot is blocked — send `/start` to the bot

### API Errors 500
- Check `data/errors.json` via `curl http://localhost:5000/api/errors`
- Common: Fyers token expired mid-session → restart scanner to refresh

### High Memory Usage
- The system caches historical data for 4 minutes in memory
- Call `GET /api/backtest/run` only when needed as it loads 365 days of data
- Each symbol uses ~1MB of OHLCV data in memory

---

## PROJECT STRUCTURE

```
trading-system/
├── auth/                   # Fyers authentication modules
│   ├── fyers_auth.py       # Auto-login via TOTP (no selenium)
│   └── token_manager.py    # Token storage and validation
├── strategies/             # 8 independent strategy modules
│   ├── candlestick_patterns.py
│   ├── trend_strategies.py
│   ├── momentum_strategies.py
│   ├── breakout_strategies.py
│   ├── support_resistance.py
│   ├── volume_strategies.py
│   ├── reversal_strategies.py
│   └── options_strategies.py
├── core/                   # Engine modules
│   ├── data_fetcher.py     # Fyers API data layer with caching
│   ├── realtime_feed.py    # WebSocket live price feed
│   ├── risk_calculator.py  # ATR stops, position sizing, R targets
│   ├── combined_engine.py  # Multi-timeframe signal orchestrator
│   ├── backtester.py       # Historical simulation engine
│   └── file_storage.py     # Thread-safe JSON storage layer
├── api/
│   └── routes.py           # Flask REST API endpoints
├── bot/
│   └── telegram_bot.py     # Telegram notification messages
├── data/                   # JSON data storage
│   ├── trades.json         # All signals and trade records
│   ├── watchlist.json      # Symbol watchlist
│   ├── backtest_results.json
│   ├── errors.json
│   └── token.json          # Fyers access token (auto-managed)
├── config/
│   └── config.json         # System configuration
├── scanner.py              # APScheduler orchestrator
├── app.py                  # Flask application entry point
└── requirements.txt
```

---

## DISCLAIMER

This system generates trading signals based on technical analysis. Past performance does not guarantee future results. Trading in stocks and derivatives involves significant risk. This software is for educational and informational purposes only. Always do your own research and consult a qualified financial advisor before trading.
