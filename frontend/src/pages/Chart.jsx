import { useEffect, useRef, useState, useCallback } from 'react'
import { createChart, CandlestickSeries, HistogramSeries, LineSeries } from 'lightweight-charts'
import { getChart } from '../api'

const TIMEFRAMES = [
  { label: '5m',  resolution: '5',  days: 5  },
  { label: '15m', resolution: '15', days: 10 },
  { label: '1h',  resolution: '60', days: 30 },
  { label: 'D',   resolution: 'D',  days: 180},
  { label: 'W',   resolution: 'W',  days: 730},
]

const POPULAR = [
  { label: 'NIFTY 50',   symbol: 'NSE:NIFTY50-INDEX'   },
  { label: 'BANK NIFTY', symbol: 'NSE:NIFTYBANK-INDEX'  },
  { label: 'RELIANCE',   symbol: 'NSE:RELIANCE-EQ'      },
  { label: 'TCS',        symbol: 'NSE:TCS-EQ'           },
  { label: 'HDFC BANK',  symbol: 'NSE:HDFCBANK-EQ'      },
  { label: 'INFOSYS',    symbol: 'NSE:INFY-EQ'          },
  { label: 'TATAMOTORS', symbol: 'NSE:TATAMOTORS-EQ'    },
  { label: 'GOLD',       symbol: 'MCX:GOLD-I'           },
  { label: 'SILVER',     symbol: 'MCX:SILVER-I'         },
]

function fmt(v)    { return v == null || v === 0 ? '—' : `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2 })}` }
function fmtVol(v) { return v == null ? '—' : v >= 1e7 ? `${(v/1e7).toFixed(2)}Cr` : v >= 1e5 ? `${(v/1e5).toFixed(2)}L` : v.toLocaleString() }

export default function ChartPage() {
  const chartContainer = useRef(null)
  const chartRef        = useRef(null)
  const candleRef       = useRef(null)
  const volumeRef       = useRef(null)
  const ema9Ref         = useRef(null)
  const ema21Ref        = useRef(null)
  const sseRef          = useRef(null)
  const liveCandleRef   = useRef(null)   // { time, open, high, low, close }
  const prevCloseRef    = useRef(null)   // prev-day close for change% calc

  const [tf, setTf]         = useState(TIMEFRAMES[1])  // default 15m
  const [symbol, setSymbol] = useState('NSE:NIFTY50-INDEX')
  const [input, setInput]   = useState('')
  const [quote, setQuote]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState('')
  const [showEma9, setShowEma9]   = useState(true)
  const [showEma21, setShowEma21] = useState(true)
  const [live, setLive]     = useState(false)

  // init chart once
  useEffect(() => {
    if (!chartContainer.current) return

    const chart = createChart(chartContainer.current, {
      layout:     { background: { color: '#0F1629' }, textColor: '#6B82A8' },
      grid:       { vertLines: { color: '#1E2D4A' }, horzLines: { color: '#1E2D4A' } },
      crosshair:  { mode: 1 },
      rightPriceScale: { borderColor: '#1E2D4A' },
      timeScale:  { borderColor: '#1E2D4A', timeVisible: true, secondsVisible: false },
      width:  chartContainer.current.clientWidth,
      height: 460,
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor:        '#00FF88', downColor: '#FF3B6B',
      borderUpColor:  '#00FF88', borderDownColor: '#FF3B6B',
      wickUpColor:    '#00FF88', wickDownColor:   '#FF3B6B',
    })

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat:     { type: 'volume' },
      priceScaleId:    'volume',
    })
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })

    const ema9Series  = chart.addSeries(LineSeries, { color: '#FFB800', lineWidth: 1, priceLineVisible: false })
    const ema21Series = chart.addSeries(LineSeries, { color: '#00D4FF', lineWidth: 1, priceLineVisible: false })

    chartRef.current  = chart
    candleRef.current = candleSeries
    volumeRef.current = volumeSeries
    ema9Ref.current   = ema9Series
    ema21Ref.current  = ema21Series

    const ro = new ResizeObserver(() => {
      if (chartContainer.current)
        chart.applyOptions({ width: chartContainer.current.clientWidth })
    })
    ro.observe(chartContainer.current)

    return () => { ro.disconnect(); chart.remove() }
  }, [])

  // load chart data
  const loadChart = useCallback(async (sym, timeframe) => {
    setLoading(true); setError('')
    try {
      const res = await getChart(sym, timeframe.resolution, timeframe.days)
      const { candles, volumes, ema9, ema21, quote: q } = res.data

      candleRef.current?.setData(candles)
      volumeRef.current?.setData(volumes)
      ema9Ref.current?.setData(ema9)
      ema21Ref.current?.setData(ema21)
      chartRef.current?.timeScale().fitContent()
      setQuote(q)
      // seed live candle from last historical bar
      if (candles.length > 0) liveCandleRef.current = { ...candles[candles.length - 1] }
      if (q?.close) prevCloseRef.current = q.close
    } catch (e) {
      setError(e.response?.data?.error || 'Failed to load chart data')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { loadChart(symbol, tf) }, [symbol, tf])

  // EMA visibility toggles (don't reload, just show/hide)
  useEffect(() => { ema9Ref.current?.applyOptions({ visible: showEma9 }) },  [showEma9])
  useEffect(() => { ema21Ref.current?.applyOptions({ visible: showEma21 }) }, [showEma21])

  // SSE tick stream — only for intraday resolutions (5, 15, 60 min)
  useEffect(() => {
    sseRef.current?.close()
    setLive(false)

    const resNum = parseInt(tf.resolution)
    if (isNaN(resNum)) return  // skip D / W timeframes

    let retryTimer = null
    let retryDelay = 2000
    let cancelled  = false

    const connect = () => {
      if (cancelled) return
      const es = new EventSource(`/api/stream?symbol=${encodeURIComponent(symbol)}`)
      sseRef.current = es

      es.onmessage = (e) => {
        try {
          const tick = JSON.parse(e.data)
          const ltp = tick?.ltp
          if (typeof ltp !== 'number' || ltp <= 0) return  // ignore heartbeats / bad ticks

          setLive(true)
          retryDelay = 2000  // reset backoff on successful data

          const nowSec    = Math.floor(Date.now() / 1000)
          const periodSec = resNum * 60
          const bucket    = Math.floor(nowSec / periodSec) * periodSec
          if (!Number.isFinite(bucket)) return

          const prev = liveCandleRef.current
          if (!prev || prev.time !== bucket) {
            liveCandleRef.current = { time: bucket, open: ltp, high: ltp, low: ltp, close: ltp }
          } else {
            liveCandleRef.current = {
              ...prev,
              high:  Math.max(prev.high, ltp),
              low:   Math.min(prev.low,  ltp),
              close: ltp,
            }
          }
          try { candleRef.current?.update(liveCandleRef.current) } catch (_) {}

          const prevClose = prevCloseRef.current
          if (prevClose && prevClose > 0) {
            const change    = parseFloat((ltp - prevClose).toFixed(2))
            const changePct = parseFloat(((ltp - prevClose) / prevClose * 100).toFixed(2))
            setQuote(q => q ? { ...q, ltp, change, changePct,
              high: Math.max(q.high ?? ltp, ltp),
              low:  Math.min(q.low  ?? ltp, ltp),
            } : q)
          }
        } catch (_) {}
      }

      es.onerror = () => {
        setLive(false)
        es.close()
        if (!cancelled) {
          retryTimer = setTimeout(connect, retryDelay)
          retryDelay = Math.min(retryDelay * 2, 30000)  // cap at 30 s
        }
      }
    }

    connect()

    return () => {
      cancelled = true
      clearTimeout(retryTimer)
      sseRef.current?.close()
      setLive(false)
    }
  }, [symbol, tf])

  const handleSearch = (e) => {
    e.preventDefault()
    const raw = input.trim().toUpperCase()
    if (!raw) return
    // auto-format if user types plain name like "RELIANCE"
    const formatted = raw.includes(':') ? raw : `NSE:${raw}-EQ`
    setSymbol(formatted)
    setInput('')
  }

  const isUp = quote && quote.changePct >= 0
  const displayName = symbol.split(':')[1]?.replace(/-EQ|-INDEX|-I/, '') || symbol

  const chipStyle = isActive => ({
    fontSize: 11,
    padding: '5px 12px',
    borderRadius: 4,
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    border: isActive ? '1px solid rgba(0,212,255,0.35)' : '1px solid var(--border)',
    background: isActive ? 'rgba(0,212,255,0.12)' : 'transparent',
    color: isActive ? 'var(--cyan)' : 'var(--text-2)',
    transition: 'border-color 0.15s ease, color 0.15s ease, background 0.15s ease',
  })
  const hoverOn = e => {
    e.currentTarget.style.borderColor = 'var(--border-hi)'
    e.currentTarget.style.color = 'var(--text-1)'
  }
  const hoverOff = (e, active) => {
    e.currentTarget.style.borderColor = active ? 'rgba(0,212,255,0.35)' : 'var(--border)'
    e.currentTarget.style.color = active ? 'var(--cyan)' : 'var(--text-2)'
  }
  const controlButton = active => ({
    fontSize: 11,
    fontWeight: 600,
    padding: '5px 10px',
    borderRadius: 4,
    cursor: 'pointer',
    border: active ? '1px solid rgba(0,212,255,0.3)' : '1px solid transparent',
    background: active ? 'rgba(0,212,255,0.12)' : 'transparent',
    color: active ? 'var(--cyan)' : 'var(--text-2)',
    transition: 'all 0.15s ease',
  })
  const emaButton = (active, color, bg, border) => ({
    fontSize: 11,
    fontWeight: 600,
    padding: '5px 10px',
    borderRadius: 4,
    cursor: 'pointer',
    border: active ? border : '1px solid var(--border)',
    background: active ? bg : 'transparent',
    color: active ? color : 'var(--text-2)',
    transition: 'all 0.15s ease',
  })
  const legendLine = color => ({
    display: 'inline-block',
    width: 6,
    height: 2,
    background: color,
    borderRadius: 99,
  })
  const formatItems = [
    { type: 'NSE Equity', fmt: 'NSE:SYMBOL-EQ', ex: 'NSE:RELIANCE-EQ' },
    { type: 'NSE Index', fmt: 'NSE:NAME-INDEX', ex: 'NSE:NIFTY50-INDEX' },
    { type: 'MCX Gold/Silver', fmt: 'MCX:SYMBOL-I', ex: 'MCX:GOLD-I' },
    { type: 'Futures', fmt: 'NSE:SYMBOLDMMYFUT', ex: 'NSE:NIFTY25JUNFUT' },
  ]

  return (
    <div className="fade-up" style={{ background: 'var(--bg)', display: 'flex', flexDirection: 'column', gap: 18, overflowX: 'hidden' }}>
      <div>
        <p style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Charts</p>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-1)' }}>Stock Charts</h1>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <form onSubmit={handleSearch} style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="e.g. TATAMOTORS or NSE:TCS-EQ"
            className="form-input"
            style={{ width: 240, maxWidth: '100%' }}
          />
          <button type="submit" className="btn-primary" style={{ whiteSpace: 'nowrap' }}>
            Search
          </button>
        </form>

        <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 2, maxWidth: '100%' }}>
          {POPULAR.map(p => {
            const active = symbol === p.symbol
            return (
              <button
                key={p.symbol}
                type="button"
                onClick={() => setSymbol(p.symbol)}
                onMouseEnter={active ? undefined : hoverOn}
                onMouseLeave={e => hoverOff(e, active)}
                style={chipStyle(active)}
              >
                {p.label}
              </button>
            )
          })}
        </div>
      </div>

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap', padding: '14px 16px', borderBottom: '1px solid var(--border)' }}>
          <div>
            <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-1)' }}>{displayName}</p>
            <p style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>{symbol}</p>
          </div>

          {quote ? (
            <>
              <span style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', fontFamily: 'var(--font-mono)' }}>{fmt(quote.ltp)}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: isUp ? 'var(--emerald)' : 'var(--rose)', fontFamily: 'var(--font-mono)' }}>
                {isUp ? '↑ ' : '↓ '}{isUp ? '+' : ''}{fmt(quote.change)} ({isUp ? '+' : ''}{Number(quote.changePct).toFixed(2)}%)
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>H {fmt(quote.high)}</span>
              <span style={{ fontSize: 12, color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>L {fmt(quote.low)}</span>
              <span style={{ fontSize: 12, color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>Vol {fmtVol(quote.volume)}</span>
            </>
          ) : loading ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className="shimmer" style={{ display: 'inline-block', width: 86, height: 24, borderRadius: 4 }} />
              <span className="shimmer" style={{ display: 'inline-block', width: 112, height: 14, borderRadius: 4 }} />
              <span className="shimmer" style={{ display: 'inline-block', width: 54, height: 14, borderRadius: 4 }} />
            </div>
          ) : null}

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginLeft: 'auto' }}>
            {live && (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 10, color: 'var(--emerald)', fontWeight: 600, letterSpacing: '0.05em' }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--emerald)', boxShadow: '0 0 5px var(--emerald)', display: 'inline-block' }} />
                LIVE
              </span>
            )}
            <button
              type="button"
              onClick={() => setShowEma9(v => !v)}
              style={emaButton(showEma9, 'var(--amber)', 'rgba(255,184,0,0.08)', '1px solid rgba(255,184,0,0.4)')}
            >
              EMA 9
            </button>
            <button
              type="button"
              onClick={() => setShowEma21(v => !v)}
              style={emaButton(showEma21, 'var(--cyan)', 'rgba(0,212,255,0.08)', '1px solid rgba(0,212,255,0.4)')}
            >
              EMA 21
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {TIMEFRAMES.map(t => (
                <button key={t.label} type="button" onClick={() => setTf(t)} style={controlButton(tf.label === t.label)}>
                  {t.label}
                </button>
              ))}
            </div>

            <button type="button" onClick={() => loadChart(symbol, tf)} disabled={loading} className="btn-ghost" style={{ padding: '5px 10px', opacity: loading ? 0.45 : 1 }}>
              ↻
            </button>
          </div>
        </div>

        <div style={{ position: 'relative' }}>
          {loading && (
            <div style={{
              position: 'absolute',
              inset: 0,
              zIndex: 10,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(9,14,26,0.7)',
              backdropFilter: 'blur(2px)',
            }}>
              <div className="spin" style={{ width: 24, height: 24, border: '2px solid var(--border)', borderTopColor: 'var(--cyan)', borderRadius: '50%' }} />
            </div>
          )}
          {error && (
            <div style={{
              position: 'absolute',
              inset: 0,
              zIndex: 11,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              padding: 20,
            }}>
              <div>
                <p style={{ fontSize: 14, color: 'var(--rose)', marginBottom: 6 }}>{error}</p>
                <p style={{ fontSize: 12, color: 'var(--text-3)' }}>Try: NSE:RELIANCE-EQ · NSE:NIFTY50-INDEX · MCX:GOLD-I</p>
              </div>
            </div>
          )}
          <div ref={chartContainer} style={{ width: '100%' }} />
        </div>

        <div style={{ borderTop: '1px solid var(--border)', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-3)' }}>
            <span style={legendLine('var(--emerald)')} /> Candle Up
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-3)' }}>
            <span style={legendLine('var(--rose)')} /> Candle Down
          </span>
          {showEma9 && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-3)' }}>
              <span style={legendLine('var(--amber)')} /> EMA 9
            </span>
          )}
          {showEma21 && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-3)' }}>
              <span style={legendLine('var(--cyan)')} /> EMA 21
            </span>
          )}
        </div>
      </div>

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '18px 20px' }}>
        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)', marginBottom: 14 }}>Symbol Format Guide</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 10 }}>
          {formatItems.map(r => (
            <div key={r.type} style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', borderRadius: 7, padding: '12px 14px', minWidth: 0 }}>
              <p style={{ fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>{r.type}</p>
              <p style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-2)', marginBottom: 4, overflowWrap: 'anywhere' }}>{r.fmt}</p>
              <p style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--cyan)', overflowWrap: 'anywhere' }}>{r.ex}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
