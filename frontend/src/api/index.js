import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const apiSetToken = token => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common['Authorization']
  }
}

// ─── Existing trading endpoints ───────────────────────────────────────────────
export const getSummary        = ()           => api.get('/summary')
export const getTrades         = (params)     => api.get('/trades', { params })
export const getTrade          = (id)         => api.get(`/trades/${id}`)
export const closeTrade        = (id, body)   => api.post(`/trades/${id}/close`, body)
export const getMarketStatus   = ()           => api.get('/market/status')
export const getHealth         = ()           => api.get('/health')
export const getErrors         = ()           => api.get('/errors')
export const getPnlChart       = (days = 30)  => api.get('/analytics/pnl-chart', { params: { days } })
export const getStrategyStats  = ()           => api.get('/analytics/strategy-stats')
export const getTopSymbols     = ()           => api.get('/analytics/top-symbols')
export const getWeeklySummary  = ()           => api.get('/summary/weekly')
export const getMonthlySummary = ()           => api.get('/summary/monthly')
export const getChart          = (symbol, resolution, days) => api.get('/chart', { params: { symbol, resolution, days } })
export const getRiskReport     = (days = 30)  => api.get('/analytics/risk-report', { params: { days } })
export const getScreener       = ()           => api.get('/screener')
export const getHeatmap        = (days = 30)  => api.get('/heatmap', { params: { days } })
export const getTradingMode    = ()           => api.get('/trading-mode')
export const setTradingMode    = (mode)       => api.post('/trading-mode', { mode })

export const exportTradesCsv = (params = {}) => {
  const qs = new URLSearchParams(params).toString()
  window.open(`/api/trades/export${qs ? '?' + qs : ''}`, '_blank')
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authLogin    = (email, password) => api.post('/auth/login',    { email, password })
export const authRegister = (name, email, password) => api.post('/auth/register', { name, email, password })
export const authMe       = ()                => api.get('/auth/me')

// ─── Strategies ──────────────────────────────────────────────────────────────
export const getStrategies    = ()       => api.get('/strategies')
export const getStrategyTypes = ()       => api.get('/strategies/types')
export const createStrategy   = (data)  => api.post('/strategies', data)
export const updateStrategy   = (id, data) => api.put(`/strategies/${id}`, data)
export const deleteStrategy   = (id)    => api.delete(`/strategies/${id}`)

// ─── Backtest v2 ─────────────────────────────────────────────────────────────
export const searchStocks       = (q)          => api.get('/v2/stocks/search', { params: { q } })
export const runBacktest        = (strategyId, config) => api.post('/v2/run', { strategyId, config })
export const getBacktestStatus  = (runId)      => api.get(`/v2/status/${runId}`)
export const getBacktestResults = (runId)      => api.get(`/v2/results/${runId}`)
export const getBacktestHistory = ()           => api.get('/v2/history')

// ─── Subscriptions ───────────────────────────────────────────────────────────
export const getSubscriptionPlans   = ()       => api.get('/subscriptions/plans')
export const getCurrentSubscription = ()       => api.get('/subscriptions/current')
export const upgradeSubscription    = (tier)   => api.post('/subscriptions/upgrade', { tier })

// ─── Strategy performance ────────────────────────────────────────────────────
export const getStrategiesPerformance = () => api.get('/strategies/performance')

// ─── Paper Trading ────────────────────────────────────────────────────────────
export const getPaperPortfolio  = ()           => api.get('/paper/portfolio')
export const openPaperTrade     = (data)       => api.post('/paper/trade', data)
export const closePaperTrade    = (id, data)   => api.post(`/paper/trade/${id}/close`, data)
export const updatePaperPrice   = (id, price)  => api.patch(`/paper/trade/${id}/price`, { lastPrice: price })
export const resetPaperPortfolio= ()           => api.post('/paper/portfolio/reset')

// ─── Trade Journal ────────────────────────────────────────────────────────────
export const getJournalEntries  = (params)     => api.get('/journal', { params })
export const createJournalEntry = (data)       => api.post('/journal', data)
export const updateJournalEntry = (id, data)   => api.put(`/journal/${id}`, data)
export const deleteJournalEntry = (id)         => api.delete(`/journal/${id}`)

// ─── Notifications ────────────────────────────────────────────────────────────
export const getNotifications   = ()           => api.get('/notifications')
export const markAllRead        = ()           => api.post('/notifications/read-all')
export const markRead           = (id)         => api.post(`/notifications/${id}/read`)
export const deleteNotification = (id)         => api.delete(`/notifications/${id}`)

// ─── Price Alerts ─────────────────────────────────────────────────────────────
export const getAlerts          = ()           => api.get('/alerts')
export const createAlert        = (data)       => api.post('/alerts', data)
export const deleteAlert        = (id)         => api.delete(`/alerts/${id}`)
export const toggleAlert        = (id)         => api.post(`/alerts/${id}/toggle`)

// ─── Marketplace ──────────────────────────────────────────────────────────────
export const browseMarketplace  = (params)     => api.get('/marketplace', { params })
export const publishStrategy    = (data)       => api.post('/marketplace/publish', data)
export const subscribeStrategy  = (id)         => api.post(`/marketplace/${id}/subscribe`)
export const unpublishStrategy  = (id)         => api.post(`/marketplace/${id}/unpublish`)
export const getMyPublished     = ()           => api.get('/marketplace/mine')

// ─── Optimizer ────────────────────────────────────────────────────────────────
export const runOptimizer       = (data)       => api.post('/optimizer/run', data)
export const getOptimizerStatus = (id)         => api.get(`/optimizer/status/${id}`)
export const getOptimizerResults= (id)         => api.get(`/optimizer/results/${id}`)
export const getOptimizerHistory= ()           => api.get('/optimizer/history')

// ─── Forward Testing ──────────────────────────────────────────────────────────
export const runForwardTest     = (data)       => api.post('/forward/run', data)
export const getForwardStatus   = (id)         => api.get(`/forward/status/${id}`)

// ─── Walk-Forward / CSV export ────────────────────────────────────────────────
export const runWalkForward     = (data)       => api.post('/v2/walk-forward', data)
export const exportBacktestCsv  = (runId)      => { window.open(`/api/v2/results/${runId}/export`, '_blank') }
