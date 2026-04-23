# AI-Powered Stock Analysis Platform

A web platform that combines technical analysis, news, macro signals, and AI-generated commentary across eight investment themes — AI / semiconductors, robotics, SMR (small modular reactors), cybersecurity, aerospace, biotech, quantum computing, and hydrogen.

Built as a personal portfolio project to explore how far LLM agents can go in replacing manual market research, and as a shared dashboard for a small group of peers.

## Tech stack

**Frontend**
- Vite, React 18, TypeScript
- Tailwind CSS v4
- Recharts (charts), Framer Motion (animation)
- React Router, i18next (EN / KO)

**Backend**
- Python 3.11, FastAPI
- `yfinance`, `curl_cffi`, BeautifulSoup for market and news data
- Google Gemini API for AI commentary
- Finnhub API for US news
- Naver Finance crawler for KR news
- Supabase (Postgres) for member data, with JSON fallback

**Infra**
- Backend deployed on Render
- Supabase for the managed Postgres
- Secrets injected via environment variables only

## Features

- **Sector dashboard** — eight sectors tracked in parallel, each with a curated watch list, mind-map view, and narrative summary
- **Technical analysis** — RSI, MACD, and Bollinger Bands computed server-side and rendered as interactive Recharts
- **AI analyst** — Gemini produces per-stock summaries that cite the underlying indicators and recent news
- **News feed** — Finnhub + Naver Finance crawlers with deduplication and auto-refresh on a configurable interval
- **Commodity tracker** — live prices for WTI, gold, copper, etc., for macro context
- **Member gate + admin panel** — private beta: only invited members reach the dashboards; an admin view can add/remove members

## Architecture

```
backend/                 # FastAPI app
  main.py                # entry point
  config.py              # pydantic settings loaded from env
  api/                   # routers: analysis, members, news, sectors
  services/              # stock_data, technical_analysis, fundamentals,
                         # news_crawler, naver_finance, commodity_data,
                         # research, runtime_controls
  models/
frontend/
  src/
    App.tsx, main.tsx
    components/          # AnalysisDashboard, ChartView, SectorList,
                         # SectorMindMap, SectorDetailPage, StockCard,
                         # NewsPanel, CommodityTracker, AdminPanel,
                         # LoginGate, Layout
    api/client.ts        # typed REST client
    i18n/                # en, ko
    types/               # shared TypeScript types
data/                    # sector + stock definitions (JSON)
```

The browser never talks to Supabase directly — all data flows through the FastAPI backend, so the Supabase service key stays server-side.

## Running locally

### Prerequisites
- Python 3.11+
- Node.js 20+
- A Supabase project (optional — backend falls back to JSON files if unset)
- API keys: Google Gemini, Finnhub

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp ../.env.example ../.env      # fill in SUPABASE_URL, SUPABASE_KEY,
                                # GEMINI_API_KEY, FINNHUB_API_KEY
uvicorn main:app --reload       # http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

## Security

- All credentials are loaded from environment variables; nothing is hardcoded
- `.env` is git-ignored — only `.env.example` (placeholders) is tracked
- Supabase is only reached from the backend, so the service key never ships to the browser
- Member gate on the frontend blocks unauthenticated access to dashboards

## Status

In active development. A small group of peers uses the private deployment as a daily read.
