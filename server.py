"""
TradeX Price Server — yfinance real-time precision
====================================================
Run:
    pip install flask yfinance flask-cors && python server.py

Then open http://localhost:5000 (serves index.html + /api/prices)

API endpoints:
  GET /api/prices   → { prices: {id: {p, c, hi, lo, mc}}, age: int, ok: bool }
  GET /api/assets   → { stocks: [...], crypto: [...] }  (metadata only, no user data)
  GET /             → serves index.html
  GET /<path>       → serves static files
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import yfinance as yf
import threading
import time
import os

app = Flask(__name__, static_folder='.')
# Allow ALL origins including file:// so the HTML works
# whether opened directly or via the server
CORS(app, resources={r"/api/*": {"origins": "*"}},
     supports_credentials=False)

# ── Stock symbol map: TradeX ID → Yahoo Finance ticker ──────────────────────
SYMBOLS = {
    'aapl':       'AAPL',
    'msft':       'MSFT',
    'nvda':       'NVDA',
    'googl':      'GOOGL',
    'meta':       'META',
    'tsla':       'TSLA',
    'amzn':       'AMZN',
    'nflx':       'NFLX',
    'amd':        'AMD',
    'intc':       'INTC',
    'jpm':        'JPM',
    'bac':        'BAC',
    'gs':         'GS',
    'v':          'V',
    'ma':         'MA',
    'jnj':        'JNJ',
    'pfe':        'PFE',
    'xom':        'XOM',
    'wmt':        'WMT',
    'ko':         'KO',
    'tsm':        'TSM',
    'baba':       'BABA',
    'toyota':     'TM',
    # Indian stocks — priced in INR on NSE, we convert to USD
    'reliance':   'RELIANCE.NS',
    'tcs':        'TCS.NS',
    'infy':       'INFY.NS',
    'hdfcbank':   'HDFCBANK.NS',
    'icicibank':  'ICICIBANK.NS',
    'sbi':        'SBIN.NS',
    'wipro':      'WIPRO.NS',
    'tatamotors': 'TATAMOTORS.BO',  # BSE works when NSE fails
}

# These IDs are priced in INR and need USD conversion
NSE_IDS = {
    'reliance', 'tcs', 'infy', 'hdfcbank',
    'icicibank', 'sbi', 'wipro', 'tatamotors',
}

# ── Shared state (thread-safe) ───────────────────────────────────────────────
_cache: dict = {}          # {app_id: {p, c, hi, lo, mc}}
_last_fetch: float = 0     # unix timestamp of last successful fetch
_lock = threading.Lock()

# ── Helpers ──────────────────────────────────────────────────────────────────
def get_usd_inr() -> float:
    """Fetch live USD/INR rate; falls back to 83.5 if unavailable."""
    try:
        rate = yf.Ticker('USDINR=X').fast_info.last_price
        return float(rate) if rate and float(rate) > 0 else 83.5
    except Exception:
        return 83.5


def safe_float(val, fallback=0.0) -> float:
    try:
        f = float(val)
        return f if f == f else fallback  # NaN check
    except Exception:
        return fallback


def fetch_all() -> None:
    """Fetch all stock prices via yfinance and update _cache."""
    global _last_fetch

    inr_rate = get_usd_inr()
    print(f"[TradeX] USD/INR rate: {inr_rate:.2f}")

    # Fetch all tickers in one batch call (faster than individual requests)
    all_symbols = list(SYMBOLS.values())
    tickers_obj = yf.Tickers(' '.join(all_symbols))

    result = {}
    for app_id, yf_sym in SYMBOLS.items():
        try:
            fi = tickers_obj.tickers[yf_sym].fast_info

            p_raw  = safe_float(getattr(fi, 'last_price',      None) or getattr(fi, 'previous_close', None))
            hi_raw = safe_float(getattr(fi, 'day_high',        None) or p_raw)
            lo_raw = safe_float(getattr(fi, 'day_low',         None) or p_raw)
            pc_raw = safe_float(getattr(fi, 'previous_close',  None) or p_raw)
            mc_raw = safe_float(getattr(fi, 'market_cap',      None))

            if p_raw <= 0:
                print(f"[TradeX] {yf_sym}: price=0, skipping")
                continue

            # NSE stocks are in INR → convert to USD
            conv = inr_rate if app_id in NSE_IDS else 1.0

            chg  = ((p_raw - pc_raw) / pc_raw * 100) if pc_raw > 0 else 0.0

            result[app_id] = {
                'p':  round(p_raw  / conv, 4),
                'c':  round(chg,           3),
                'hi': round(hi_raw / conv, 4),
                'lo': round(lo_raw / conv, 4),
                'mc': round(mc_raw / conv, 0),
            }
        except Exception as e:
            print(f"[TradeX] {yf_sym} error: {e}")

    with _lock:
        _cache.update(result)
        _last_fetch = time.time()

    ok_count = len(result)
    total    = len(SYMBOLS)
    print(f"[TradeX] {ok_count}/{total} stocks fetched @ {time.strftime('%H:%M:%S')}")


def price_loop() -> None:
    """Background thread: refetch every 30 seconds."""
    while True:
        try:
            fetch_all()
        except Exception as e:
            print(f"[TradeX] fetch_all error: {e}")
        time.sleep(30)


# ── Asset metadata (sent to client once; no user data here) ──────────────────
ASSET_META = {
    'stocks': [
        {'id':'aapl',       'name':'Apple Inc.',       'sym':'AAPL',       'col':'#a8b2c1', 'bg':'rgba(168,178,193,.18)', 'sector':'Tech',    'region':'🇺🇸', 'exch':'NASDAQ'},
        {'id':'msft',       'name':'Microsoft',        'sym':'MSFT',       'col':'#00a4ef', 'bg':'rgba(0,164,239,.18)',   'sector':'Tech',    'region':'🇺🇸', 'exch':'NASDAQ'},
        {'id':'nvda',       'name':'NVIDIA',           'sym':'NVDA',       'col':'#76b900', 'bg':'rgba(118,185,0,.18)',   'sector':'Tech',    'region':'🇺🇸', 'exch':'NASDAQ'},
        {'id':'googl',      'name':'Alphabet',         'sym':'GOOGL',      'col':'#4285f4', 'bg':'rgba(66,133,244,.18)',  'sector':'Tech',    'region':'🇺🇸', 'exch':'NASDAQ'},
        {'id':'meta',       'name':'Meta',             'sym':'META',       'col':'#0082fb', 'bg':'rgba(0,130,251,.18)',   'sector':'Tech',    'region':'🇺🇸', 'exch':'NASDAQ'},
        {'id':'tsla',       'name':'Tesla',            'sym':'TSLA',       'col':'#cc0000', 'bg':'rgba(204,0,0,.18)',     'sector':'Auto',    'region':'🇺🇸', 'exch':'NASDAQ'},
        {'id':'amzn',       'name':'Amazon',           'sym':'AMZN',       'col':'#ff9900', 'bg':'rgba(255,153,0,.18)',   'sector':'Tech',    'region':'🇺🇸', 'exch':'NASDAQ'},
        {'id':'nflx',       'name':'Netflix',          'sym':'NFLX',       'col':'#e50914', 'bg':'rgba(229,9,20,.18)',    'sector':'Media',   'region':'🇺🇸', 'exch':'NASDAQ'},
        {'id':'amd',        'name':'AMD',              'sym':'AMD',        'col':'#ed1c24', 'bg':'rgba(237,28,36,.18)',   'sector':'Tech',    'region':'🇺🇸', 'exch':'NASDAQ'},
        {'id':'intc',       'name':'Intel',            'sym':'INTC',       'col':'#0071c5', 'bg':'rgba(0,113,197,.18)',   'sector':'Tech',    'region':'🇺🇸', 'exch':'NASDAQ'},
        {'id':'jpm',        'name':'JPMorgan Chase',   'sym':'JPM',        'col':'#005eb8', 'bg':'rgba(0,94,184,.18)',    'sector':'Finance', 'region':'🇺🇸', 'exch':'NYSE'},
        {'id':'bac',        'name':'Bank of America',  'sym':'BAC',        'col':'#dc1431', 'bg':'rgba(220,20,49,.18)',   'sector':'Finance', 'region':'🇺🇸', 'exch':'NYSE'},
        {'id':'gs',         'name':'Goldman Sachs',    'sym':'GS',         'col':'#6699cc', 'bg':'rgba(102,153,204,.18)','sector':'Finance', 'region':'🇺🇸', 'exch':'NYSE'},
        {'id':'v',          'name':'Visa',             'sym':'V',          'col':'#1a1f71', 'bg':'rgba(26,31,113,.18)',   'sector':'Finance', 'region':'🇺🇸', 'exch':'NYSE'},
        {'id':'ma',         'name':'Mastercard',       'sym':'MA',         'col':'#eb001b', 'bg':'rgba(235,0,27,.18)',    'sector':'Finance', 'region':'🇺🇸', 'exch':'NYSE'},
        {'id':'jnj',        'name':'J&J',              'sym':'JNJ',        'col':'#d51900', 'bg':'rgba(213,25,0,.18)',    'sector':'Health',  'region':'🇺🇸', 'exch':'NYSE'},
        {'id':'pfe',        'name':'Pfizer',           'sym':'PFE',        'col':'#0093d0', 'bg':'rgba(0,147,208,.18)',   'sector':'Health',  'region':'🇺🇸', 'exch':'NYSE'},
        {'id':'xom',        'name':'ExxonMobil',       'sym':'XOM',        'col':'#ff0000', 'bg':'rgba(180,0,0,.18)',     'sector':'Energy',  'region':'🇺🇸', 'exch':'NYSE'},
        {'id':'wmt',        'name':'Walmart',          'sym':'WMT',        'col':'#0071ce', 'bg':'rgba(0,113,206,.18)',   'sector':'Retail',  'region':'🇺🇸', 'exch':'NYSE'},
        {'id':'ko',         'name':'Coca-Cola',        'sym':'KO',         'col':'#f40000', 'bg':'rgba(244,0,0,.18)',     'sector':'FMCG',    'region':'🇺🇸', 'exch':'NYSE'},
        {'id':'reliance',   'name':'Reliance',         'sym':'RELIANCE',   'col':'#1a6bc4', 'bg':'rgba(26,107,196,.18)', 'sector':'Energy',  'region':'🇮🇳', 'exch':'NSE'},
        {'id':'tcs',        'name':'TCS',              'sym':'TCS',        'col':'#c1272d', 'bg':'rgba(193,39,45,.18)',   'sector':'Tech',    'region':'🇮🇳', 'exch':'NSE'},
        {'id':'infy',       'name':'Infosys',          'sym':'INFY',       'col':'#007dc5', 'bg':'rgba(0,125,197,.18)',   'sector':'Tech',    'region':'🇮🇳', 'exch':'NSE'},
        {'id':'hdfcbank',   'name':'HDFC Bank',        'sym':'HDFCBANK',   'col':'#004c8f', 'bg':'rgba(0,76,143,.18)',    'sector':'Finance', 'region':'🇮🇳', 'exch':'NSE'},
        {'id':'icicibank',  'name':'ICICI Bank',       'sym':'ICICIBANK',  'col':'#f7941d', 'bg':'rgba(247,148,29,.18)', 'sector':'Finance', 'region':'🇮🇳', 'exch':'NSE'},
        {'id':'sbi',        'name':'SBI',              'sym':'SBIN',       'col':'#1e4db7', 'bg':'rgba(30,77,183,.18)',   'sector':'Finance', 'region':'🇮🇳', 'exch':'NSE'},
        {'id':'wipro',      'name':'Wipro',            'sym':'WIPRO',      'col':'#0d5eb4', 'bg':'rgba(13,94,180,.18)',   'sector':'Tech',    'region':'🇮🇳', 'exch':'NSE'},
        {'id':'tatamotors', 'name':'Tata Motors',      'sym':'TATAMOTORS', 'col':'#2c6faf', 'bg':'rgba(44,111,175,.18)', 'sector':'Auto',    'region':'🇮🇳', 'exch':'NSE'},
        {'id':'tsm',        'name':'TSMC',             'sym':'TSM',        'col':'#00b4d8', 'bg':'rgba(0,180,216,.18)',   'sector':'Tech',    'region':'🇹🇼', 'exch':'NYSE'},
        {'id':'baba',       'name':'Alibaba',          'sym':'BABA',       'col':'#ff6600', 'bg':'rgba(255,102,0,.18)',   'sector':'Tech',    'region':'🇨🇳', 'exch':'NYSE'},
        {'id':'toyota',     'name':'Toyota',           'sym':'TM',         'col':'#eb0a1e', 'bg':'rgba(235,10,30,.18)',   'sector':'Auto',    'region':'🇯🇵', 'exch':'NYSE'},
    ],
    'crypto': [
        {'id':'bitcoin',     'name':'Bitcoin',      'sym':'BTC',  'col':'#f7931a', 'bg':'rgba(247,147,26,.18)', 'type':'c', 'exch':'Crypto'},
        {'id':'ethereum',    'name':'Ethereum',     'sym':'ETH',  'col':'#627eea', 'bg':'rgba(98,126,234,.18)', 'type':'c', 'exch':'Crypto'},
        {'id':'binancecoin', 'name':'BNB',          'sym':'BNB',  'col':'#f3ba2f', 'bg':'rgba(243,186,47,.18)', 'type':'c', 'exch':'Crypto'},
        {'id':'solana',      'name':'Solana',       'sym':'SOL',  'col':'#9945ff', 'bg':'rgba(153,69,255,.18)', 'type':'c', 'exch':'Crypto'},
        {'id':'ripple',      'name':'XRP',          'sym':'XRP',  'col':'#00aae4', 'bg':'rgba(0,170,228,.18)',  'type':'c', 'exch':'Crypto'},
        {'id':'cardano',     'name':'Cardano',      'sym':'ADA',  'col':'#0d9bd6', 'bg':'rgba(13,155,214,.18)', 'type':'c', 'exch':'Crypto'},
        {'id':'dogecoin',    'name':'Dogecoin',     'sym':'DOGE', 'col':'#c2a633', 'bg':'rgba(194,166,51,.18)', 'type':'c', 'exch':'Crypto'},
        {'id':'avalanche-2', 'name':'Avalanche',    'sym':'AVAX', 'col':'#e84142', 'bg':'rgba(232,65,66,.18)',  'type':'c', 'exch':'Crypto'},
        {'id':'chainlink',   'name':'Chainlink',    'sym':'LINK', 'col':'#2a5ada', 'bg':'rgba(42,90,218,.18)',  'type':'c', 'exch':'Crypto'},
        {'id':'near',        'name':'NEAR Protocol','sym':'NEAR', 'col':'#00c1de', 'bg':'rgba(0,193,222,.18)',  'type':'c', 'exch':'Crypto'},
        {'id':'polkadot',    'name':'Polkadot',     'sym':'DOT',  'col':'#e6007a', 'bg':'rgba(230,0,122,.18)',  'type':'c', 'exch':'Crypto'},
        {'id':'uniswap',     'name':'Uniswap',      'sym':'UNI',  'col':'#ff007a', 'bg':'rgba(255,0,122,.18)',  'type':'c', 'exch':'Crypto'},
        {'id':'litecoin',    'name':'Litecoin',     'sym':'LTC',  'col':'#bfbbbb', 'bg':'rgba(191,187,187,.15)','type':'c', 'exch':'Crypto'},
        {'id':'tron',        'name':'TRON',         'sym':'TRX',  'col':'#ff0013', 'bg':'rgba(255,0,19,.18)',   'type':'c', 'exch':'Crypto'},
        {'id':'stellar',     'name':'Stellar',      'sym':'XLM',  'col':'#08b5e5', 'bg':'rgba(8,181,229,.18)',  'type':'c', 'exch':'Crypto'},
    ]
}


# ── Flask routes ──────────────────────────────────────────────────────────────

@app.route('/api/prices')
def api_prices():
    """
    Returns real-time stock prices from yfinance.
    Response: { prices: {id: {p, c, hi, lo, mc}}, age: seconds_since_fetch, ok: bool }
    """
    with _lock:
        data  = dict(_cache)
        age   = round(time.time() - _last_fetch) if _last_fetch else -1
        ok    = bool(data)
    return jsonify({'prices': data, 'age': age, 'ok': ok})


@app.route('/api/assets')
def api_assets():
    """Returns asset metadata (colours, symbols, sectors) — no prices, no user data."""
    return jsonify(ASSET_META)


@app.route('/')
@app.route('/<path:filename>')
def serve_static(filename='index.html'):
    """Serve the frontend."""
    return send_from_directory('.', filename)


# ── Startup ───────────────────────────────────────────────────────────────────
# ── Auto-start background thread whether run via gunicorn or directly ─────────
# This runs when imported by gunicorn OR when run directly with python server.py
_bg_thread = threading.Thread(target=price_loop, daemon=True)
_bg_thread.start()
print("[TradeX] Background price fetch started.")

if __name__ == '__main__':
    print("=" * 56)
    print("  TradeX Price Server — yfinance real-time edition")
    print("=" * 56)
    print("Waiting for initial price data…")

    timeout = 60
    waited  = 0
    while not _last_fetch and waited < timeout:
        time.sleep(0.5)
        waited += 0.5

    if _last_fetch:
        with _lock:
            count = len(_cache)
        print(f"Ready! {count}/{len(SYMBOLS)} prices loaded.")
    else:
        print("Warning: initial fetch timed out — serving with empty cache.")

    port = int(os.environ.get('PORT', 5000))
    print(f"\nOpen: http://localhost:{port}")
    print("Press Ctrl+C to stop.\n")

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
