# StockAnalyst — Resumen Completo del Proyecto
**Fecha:** 09/03/2026
**Propósito de este archivo:** Contexto completo para continuar el desarrollo en un nuevo chat (ChatGPT o Claude)

---

## 1. ¿Qué es esto?

Sistema de análisis multifactor para swing trading en acciones de EEUU. Genera señales de compra y venta al final del día. **No ejecuta trades automáticamente** — el usuario opera manualmente.

- **Stack:** Python 3.12, SQLite, Streamlit, yfinance, Plotly
- **Datos:** Yahoo Finance (gratis, sin API key)
- **Despliegue:** Streamlit Community Cloud (gratis)
- **Repo:** https://github.com/diegoto86/stockanalyst (rama `master`)

---

## 2. Estructura del Proyecto

```
config.py                  Configuración central (universo, riesgo, políticas de refresh)
dashboard.py               Frontend Streamlit (entry point)
requirements.txt           yfinance, pandas, numpy, streamlit, plotly, python-dotenv

providers/
  yahoo_prices.py          Descarga OHLCV diario via yfinance
  yahoo_fundamentals.py    Descarga fundamentales (PE, margen, deuda, FCF, etc.)
  yahoo_news.py            Descarga noticias recientes por ticker
  yahoo_events.py          Descarga calendario de earnings

storage/
  db.py                    Inicialización SQLite con todos los esquemas de tablas
  price_repository.py      CRUD para price_bars_daily
  technical_repository.py  CRUD para technical_snapshot_daily
  fundamentals_repository.py  CRUD para fundamentals_snapshot_quarterly
  news_repository.py       CRUD para news_events_daily
  watchlist_repository.py  CRUD para universe_watchlist_weekly
  portfolio_repository.py  Lee el CSV manual del portfolio

orchestration/
  freshness.py             Verifica si los datos están desactualizados

engines/
  technicals.py            Calcula MA20/50/200, RSI14, ATR14, pullback%, trend state, setup flags
  buy_engine.py            Genera candidatos de compra
  sell_engine.py           Genera acciones sobre posiciones abiertas

jobs/
  build_universe.py        [NUEVO] Construye universo amplio desde NASDAQ screener
  run_quarterly.py         Pipeline trimestral (fundamentales)
  run_weekly.py            Pipeline semanal (watchlist con scoring)
  run_daily.py             Pipeline diario (precios, técnicos, señales)
  run_monthly.py           STUB — no implementado

data/
  stockanalyst.db          Base de datos SQLite
  universe_tickers.csv     [NUEVO] Lista ampliada de tickers (generada por build_universe.py)
  portfolio/portfolio.csv  CSV manual que el usuario edita con sus posiciones
  buy_candidates_daily.csv Salida diaria del BUY engine
  sell_actions_daily.csv   Salida diaria del SELL engine
  market_context.csv       Precios de SPY/QQQ/IWM/VIX para contexto
  earnings_calendar.csv    Próximos earnings
```

---

## 3. Base de Datos SQLite (`data/stockanalyst.db`)

### Tablas:
| Tabla | Descripción |
|-------|-------------|
| `price_bars_daily` | OHLCV diario por ticker |
| `technical_snapshot_daily` | MA20/50/200, RSI14, ATR14, pullback%, trend_state, setup_flags |
| `fundamentals_snapshot_quarterly` | PE, márgenes, deuda/EBITDA, FCF yield, fundamental_score |
| `news_events_daily` | Noticias recientes con sentiment_proxy e impact_level |
| `universe_watchlist_weekly` | Tickers filtrados semanalmente con score |
| `buy_candidates_daily` | Candidatos de compra diarios |
| `sell_actions_daily` | Acciones recomendadas sobre posiciones |
| `refresh_log` | Registro de cuándo se actualizó cada dataset |

---

## 4. Universo de Acciones

### Antes (hardcodeado):
20 tickers: AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSM, AVGO, ASML, AMD, JPM, V, MA, UNH, LLY, XOM, CVX, HD, PG, KO

### Ahora (dinámico):
- **`jobs/build_universe.py`** descarga todos los stocks de NASDAQ, NYSE y AMEX usando el screener gratuito de NASDAQ
- Filtra por: market cap >= $2B y avg volume >= 500,000 acciones
- Resultado: **1,347 tickers** guardados en `data/universe_tickers.csv`
- `config.py` lee este archivo automáticamente si existe; si no, usa los 20 hardcodeados como fallback
- Se ejecuta 1 vez al año (o cuando se quiera refrescar el universo)

---

## 5. Pipelines

### Orden obligatorio (primera vez):
1. **Build Universe** → genera universe_tickers.csv (1 vez al año)
2. **Quarterly** → fundamentales de todos los tickers (~30-60 min para 1,347 tickers)
3. **Weekly** → watchlist con scoring
4. **Daily** → precios, técnicos, noticias, earnings, señales de compra/venta

### Pipeline Trimestral (`run_quarterly.py`)
- Descarga desde Yahoo Finance: revenue growth, EPS growth, gross margin, operating margin, net debt/EBITDA, PE TTM, EV/EBITDA, FCF yield
- Calcula `fundamental_score` (0-1) como score compuesto ponderado:
  - Revenue growth (20%), EPS growth (20%), Gross margin (15%), Op margin (15%), Deuda (15%), FCF yield (15%)
- Guarda en `fundamentals_snapshot_quarterly`

### Pipeline Semanal (`run_weekly.py`)
- Para cada ticker del universo, evalúa:
  - **Filtros duros:** liquidity_ok (avg volume >= 500K) y size_ok (market cap >= $2B) → si falla alguno, queda fuera
  - **Filtros blandos:** quality_ok (margen bruto >= 20%, deuda/EBITDA <= 4) y valuation_ok (PE <= 60)
  - **Score final:** 50% filtros + 50% fundamental_score
- Guarda la watchlist en `universe_watchlist_weekly`

### Pipeline Diario (`run_daily.py`)
1. Descarga barras OHLCV (1 año de historia)
2. Calcula indicadores técnicos
3. Descarga noticias (últimos 5 días)
4. Descarga calendario de earnings
5. Carga portfolio manual (CSV)
6. Ejecuta BUY engine
7. Ejecuta SELL engine
8. Exporta CSVs para el dashboard

---

## 6. Motor de Compra (`buy_engine.py`)

### Filtros secuenciales:
1. Solo tickers en la watchlist semanal (ya pasaron filtros fundamentales)
2. Ticker no está ya en el portfolio
3. Portfolio no está lleno (max 10 posiciones)
4. SPY no está en downtrend (contexto de mercado)
5. Trend state = "uptrend" o "mixed"
6. RSI14 <= 70 (no sobrecomprado)
7. Pullback <= 15% desde máximo reciente
8. Sin noticias de alto impacto negativo
9. Sin earnings en los próximos 7 días

### Sizing de posición:
- Riesgo máximo: 1% del capital ($1,000 sobre $100,000)
- Stop = entry - 1.5 × ATR14
- Target = entry + 2.0 × (entry - stop)  → R:R mínimo 2:1

### Score de setup (0-1):
- pullback_ok: +0.20
- rsi_reset: +0.15
- above_ma50: +0.15
- above_ma200: +0.10
- uptrend: +0.10
- fundamental_score × 0.40

---

## 7. Motor de Venta (`sell_engine.py`)

### Lógica de decisión (en orden de prioridad):
1. **Stop hit** → cerrar 100%
2. **Noticias negativas de alto impacto** → vender 50%
3. **Deterioro fundamental** (score < 0.3) → vender 50%
4. **Tendencia rota** (precio < MA50 o downtrend) → vender 50%
5. **R >= 4x** (2× el target mínimo) → vender 33% (profit parcial)
6. **Uptrend activo** → subir trailing stop (nunca bajar el stop)
7. **Default** → hold

---

## 8. Indicadores Técnicos (`engines/technicals.py`)

Calculados manualmente (sin librerías TA):
- **MA20, MA50, MA200:** medias móviles simples
- **RSI14:** índice de fuerza relativa de 14 períodos
- **ATR14:** Average True Range de 14 períodos
- **Pullback %:** distancia desde el máximo reciente de 52 semanas
- **Trend state:** "uptrend" (precio > MA50 > MA200), "downtrend" (inverso), "mixed"
- **Setup flags:** pullback_ok, rsi_reset, above_ma50, above_ma200

---

## 9. Dashboard Streamlit (`dashboard.py`)

### Secciones:
- **Market Context:** KPIs de SPY, QQQ, IWM, VIX
- **Buy Candidates:** tabla con candidatos, score, sizing, rationale
- **Sell Actions:** acciones recomendadas sobre posiciones abiertas
- **Portfolio:** posiciones actuales del CSV manual
- **Watchlist:** tickers en la watchlist semanal con scores
- **Earnings Calendar:** próximos earnings de tickers en watchlist

### Sidebar:
- Botones para ejecutar cada pipeline (Build Universe, Quarterly, Weekly, Daily)
- Indicadores de frescura de datos (verde/rojo)

---

## 10. Configuración (`config.py`)

```python
ACCOUNT_SIZE = 100_000          # USD
MAX_POSITIONS = 10
MAX_RISK_PER_TRADE = 0.01       # 1%
MAX_SECTOR_EXPOSURE = 0.30      # 30% por sector
ATR_STOP_MULTIPLIER = 1.5
MIN_R_MULTIPLE_TARGET = 2.0

MIN_MARKET_CAP = 2_000_000_000  # $2B
MIN_AVG_DAILY_VOLUME = 500_000
MAX_PE_TTM = 60
MAX_NET_DEBT_TO_EBITDA = 4.0
MIN_GROSS_MARGIN = 0.20

PULLBACK_MAX_PCT = 0.15         # 15%
RSI_OVERSOLD = 40
RSI_OVERBOUGHT = 70
```

---

## 11. Estado Actual

### Funcionando:
- Todos los providers (prices, fundamentals, news, events)
- Todos los repositorios SQLite
- Indicadores técnicos
- BUY engine y SELL engine
- Pipelines daily, weekly, quarterly
- Dashboard con todos los botones y secciones
- **[NUEVO]** build_universe.py — universo de 1,347 tickers generado y guardado
- **[NUEVO]** config.py carga universe_tickers.csv dinámicamente

### En proceso:
- Quarterly pipeline corriendo en background para los 1,347 tickers nuevos (~30-60 min)

### Pendiente de implementar:
- `run_monthly.py` (stub, solo imprime)
- Log histórico de señales (los CSVs se sobreescriben cada día)
- Gráficos de precios por ticker en el dashboard
- Tracking de exposición por sector en el dashboard
- Alertas por email/notificación
- Scheduling automático

---

## 12. Notas Técnicas Importantes

- **yfinance MultiIndex:** `yf.download()` retorna columnas `(Price, Ticker)` — manejado en `providers/yahoo_prices.py`
- **Weekly force=True:** el pipeline semanal tiene un guard que impide re-ejecutar la misma semana; el dashboard siempre pasa `force=True`
- **os.chdir en dashboard.py:** necesario para Streamlit Cloud (el working directory puede diferir del proyecto)
- **Sin Docker:** venv local en `.venv/`, deployed directo en Streamlit Cloud
- **Sin pandas-ta, SQLAlchemy, pyarrow:** removidos porque causaban fallos en Streamlit Cloud
- **Portfolio es CSV manual:** el usuario edita `data/portfolio/portfolio.csv` a mano

---

## 13. Próximos Pasos Sugeridos

1. Esperar que termine el quarterly pipeline para los 1,347 tickers
2. Ejecutar weekly pipeline (watchlist con nuevo universo)
3. Ejecutar daily pipeline (señales del día)
4. Evaluar si los filtros actuales son correctos con el universo ampliado
5. Implementar log histórico de señales (buy/sell no deben sobreescribirse)
6. Agregar gráficos de precios por ticker en el dashboard
