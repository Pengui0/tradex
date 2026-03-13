"""
TradeX Price Server — yfinance real-time precision
Run: pip install flask yfinance flask-cors && python server.py
Open: http://localhost:5000
"""
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import yfinance as yf, threading, time

app = Flask(__name__, static_folder='.')
CORS(app)

SYMBOLS = {
    'aapl':'AAPL','msft':'MSFT','nvda':'NVDA','googl':'GOOGL','meta':'META',
    'tsla':'TSLA','amzn':'AMZN','nflx':'NFLX','amd':'AMD','intc':'INTC',
    'jpm':'JPM','bac':'BAC','gs':'GS','v':'V','ma':'MA',
    'jnj':'JNJ','pfe':'PFE','xom':'XOM','wmt':'WMT','ko':'KO',
    'tsm':'TSM','baba':'BABA','toyota':'TM',
    'reliance':'RELIANCE.NS','tcs':'TCS.NS','infy':'INFY.NS',
    'hdfcbank':'HDFCBANK.NS','icicibank':'ICICIBANK.NS','sbi':'SBIN.NS',
    'wipro':'WIPRO.NS','tatamotors':'TATAMOTORS.NS',
}
NSE = {'reliance','tcs','infy','hdfcbank','icicibank','sbi','wipro','tatamotors'}

_cache, _last_fetch, _lock = {}, 0, threading.Lock()

def get_inr():
    try: return float(yf.Ticker('USDINR=X').fast_info.last_price) or 83.5
    except: return 83.5

def fetch_all():
    global _last_fetch
    inr = get_inr()
    tickers = yf.Tickers(' '.join(SYMBOLS.values()))
    result = {}
    for app_id, sym in SYMBOLS.items():
        try:
            fi     = tickers.tickers[sym].fast_info
            p_raw  = float(fi.last_price or fi.previous_close)
            hi_raw = float(fi.day_high   or p_raw)
            lo_raw = float(fi.day_low    or p_raw)
            pc_raw = float(fi.previous_close or p_raw)
            mc_raw = float(getattr(fi, 'market_cap', 0) or 0)
            conv   = inr if app_id in NSE else 1.0
            chg    = ((p_raw - pc_raw) / pc_raw * 100) if pc_raw else 0
            result[app_id] = {
                'p':  round(p_raw  / conv, 4),
                'c':  round(chg, 3),
                'hi': round(hi_raw / conv, 4),
                'lo': round(lo_raw / conv, 4),
                'mc': round(mc_raw / conv, 0),
            }
        except: pass
    with _lock:
        _cache.update(result)
        _last_fetch = time.time()
    print(f"[TradeX] {len(result)}/{len(SYMBOLS)} stocks @ {time.strftime('%H:%M:%S')}")

def loop():
    while True:
        try: fetch_all()
        except Exception as e: print(f"[TradeX] error: {e}")
        time.sleep(30)

ASSETS = {
  'stocks': [
    {'id':'aapl','name':'Apple','sym':'AAPL','col':'#a8b2c1','bg':'rgba(168,178,193,.18)','sector':'Tech','region':'🇺🇸','exch':'NASDAQ','price':228.5,'chg':.92},
    {'id':'msft','name':'Microsoft','sym':'MSFT','col':'#00a4ef','bg':'rgba(0,164,239,.18)','sector':'Tech','region':'🇺🇸','exch':'NASDAQ','price':415.3,'chg':1.14},
    {'id':'nvda','name':'NVIDIA','sym':'NVDA','col':'#76b900','bg':'rgba(118,185,0,.18)','sector':'Tech','region':'🇺🇸','exch':'NASDAQ','price':138.6,'chg':2.31},
    {'id':'googl','name':'Alphabet','sym':'GOOGL','col':'#4285f4','bg':'rgba(66,133,244,.18)','sector':'Tech','region':'🇺🇸','exch':'NASDAQ','price':192.8,'chg':-.43},
    {'id':'meta','name':'Meta','sym':'META','col':'#0082fb','bg':'rgba(0,130,251,.18)','sector':'Tech','region':'🇺🇸','exch':'NASDAQ','price':612.4,'chg':1.05},
    {'id':'tsla','name':'Tesla','sym':'TSLA','col':'#cc0000','bg':'rgba(204,0,0,.18)','sector':'Auto','region':'🇺🇸','exch':'NASDAQ','price':248.9,'chg':-1.82},
    {'id':'amzn','name':'Amazon','sym':'AMZN','col':'#ff9900','bg':'rgba(255,153,0,.18)','sector':'Tech','region':'🇺🇸','exch':'NASDAQ','price':224.1,'chg':.68},
    {'id':'nflx','name':'Netflix','sym':'NFLX','col':'#e50914','bg':'rgba(229,9,20,.18)','sector':'Media','region':'🇺🇸','exch':'NASDAQ','price':912.3,'chg':1.45},
    {'id':'amd','name':'AMD','sym':'AMD','col':'#ed1c24','bg':'rgba(237,28,36,.18)','sector':'Tech','region':'🇺🇸','exch':'NASDAQ','price':172.4,'chg':1.88},
    {'id':'intc','name':'Intel','sym':'INTC','col':'#0071c5','bg':'rgba(0,113,197,.18)','sector':'Tech','region':'🇺🇸','exch':'NASDAQ','price':22.8,'chg':-.65},
    {'id':'jpm','name':'JPMorgan','sym':'JPM','col':'#005eb8','bg':'rgba(0,94,184,.18)','sector':'Finance','region':'🇺🇸','exch':'NYSE','price':248.6,'chg':.34},
    {'id':'bac','name':'Bank of America','sym':'BAC','col':'#dc1431','bg':'rgba(220,20,49,.18)','sector':'Finance','region':'🇺🇸','exch':'NYSE','price':43.8,'chg':.21},
    {'id':'gs','name':'Goldman Sachs','sym':'GS','col':'#6699cc','bg':'rgba(102,153,204,.18)','sector':'Finance','region':'🇺🇸','exch':'NYSE','price':588.9,'chg':-.44},
    {'id':'v','name':'Visa','sym':'V','col':'#1a1f71','bg':'rgba(26,31,113,.18)','sector':'Finance','region':'🇺🇸','exch':'NYSE','price':338.4,'chg':.63},
    {'id':'ma','name':'Mastercard','sym':'MA','col':'#eb001b','bg':'rgba(235,0,27,.18)','sector':'Finance','region':'🇺🇸','exch':'NYSE','price':572.3,'chg':.41},
    {'id':'jnj','name':'J&J','sym':'JNJ','col':'#d51900','bg':'rgba(213,25,0,.18)','sector':'Health','region':'🇺🇸','exch':'NYSE','price':148.2,'chg':-.18},
    {'id':'pfe','name':'Pfizer','sym':'PFE','col':'#0093d0','bg':'rgba(0,147,208,.18)','sector':'Health','region':'🇺🇸','exch':'NYSE','price':28.6,'chg':-.52},
    {'id':'xom','name':'ExxonMobil','sym':'XOM','col':'#ff0000','bg':'rgba(180,0,0,.18)','sector':'Energy','region':'🇺🇸','exch':'NYSE','price':112.8,'chg':.88},
    {'id':'wmt','name':'Walmart','sym':'WMT','col':'#0071ce','bg':'rgba(0,113,206,.18)','sector':'Retail','region':'🇺🇸','exch':'NYSE','price':98.4,'chg':.31},
    {'id':'ko','name':'Coca-Cola','sym':'KO','col':'#f40000','bg':'rgba(244,0,0,.18)','sector':'FMCG','region':'🇺🇸','exch':'NYSE','price':63.2,'chg':.15},
    {'id':'reliance','name':'Reliance','sym':'RELIANCE','col':'#1a6bc4','bg':'rgba(26,107,196,.18)','sector':'Energy','region':'🇮🇳','exch':'NSE','price':35.31,'chg':.73},
    {'id':'tcs','name':'TCS','sym':'TCS','col':'#c1272d','bg':'rgba(193,39,45,.18)','sector':'Tech','region':'🇮🇳','exch':'NSE','price':49.35,'chg':.41},
    {'id':'infy','name':'Infosys','sym':'INFY','col':'#007dc5','bg':'rgba(0,125,197,.18)','sector':'Tech','region':'🇮🇳','exch':'NSE','price':22.66,'chg':-.28},
    {'id':'hdfcbank','name':'HDFC Bank','sym':'HDFCBANK','col':'#004c8f','bg':'rgba(0,76,143,.18)','sector':'Finance','region':'🇮🇳','exch':'NSE','price':20.53,'chg':.56},
    {'id':'icicibank','name':'ICICI Bank','sym':'ICICIBANK','col':'#f7941d','bg':'rgba(247,148,29,.18)','sector':'Finance','region':'🇮🇳','exch':'NSE','price':14.22,'chg':.84},
    {'id':'sbi','name':'SBI','sym':'SBIN','col':'#1e4db7','bg':'rgba(30,77,183,.18)','sector':'Finance','region':'🇮🇳','exch':'NSE','price':9.4,'chg':1.02},
    {'id':'wipro','name':'Wipro','sym':'WIPRO','col':'#0d5eb4','bg':'rgba(13,94,180,.18)','sector':'Tech','region':'🇮🇳','exch':'NSE','price':6.58,'chg':-.41},
    {'id':'tatamotors','name':'Tata Motors','sym':'TATAMOTORS','col':'#2c6faf','bg':'rgba(44,111,175,.18)','sector':'Auto','region':'🇮🇳','exch':'NSE','price':10.05,'chg':-.88},
    {'id':'tsm','name':'TSMC','sym':'TSM','col':'#00b4d8','bg':'rgba(0,180,216,.18)','sector':'Tech','region':'🇹🇼','exch':'NYSE','price':182.3,'chg':1.67},
    {'id':'baba','name':'Alibaba','sym':'BABA','col':'#ff6600','bg':'rgba(255,102,0,.18)','sector':'Tech','region':'🇨🇳','exch':'NYSE','price':88.4,'chg':-1.24},
    {'id':'toyota','name':'Toyota','sym':'TM','col':'#eb0a1e','bg':'rgba(235,10,30,.18)','sector':'Auto','region':'🇯🇵','exch':'NYSE','price':212.4,'chg':.52},
  ],
  'crypto': [
    {'id':'bitcoin','name':'Bitcoin','sym':'BTC','col':'#f7931a','bg':'rgba(247,147,26,.18)','type':'c','exch':'Crypto'},
    {'id':'ethereum','name':'Ethereum','sym':'ETH','col':'#627eea','bg':'rgba(98,126,234,.18)','type':'c','exch':'Crypto'},
    {'id':'binancecoin','name':'BNB','sym':'BNB','col':'#f3ba2f','bg':'rgba(243,186,47,.18)','type':'c','exch':'Crypto'},
    {'id':'solana','name':'Solana','sym':'SOL','col':'#9945ff','bg':'rgba(153,69,255,.18)','type':'c','exch':'Crypto'},
    {'id':'ripple','name':'XRP','sym':'XRP','col':'#00aae4','bg':'rgba(0,170,228,.18)','type':'c','exch':'Crypto'},
    {'id':'cardano','name':'Cardano','sym':'ADA','col':'#0d9bd6','bg':'rgba(13,155,214,.18)','type':'c','exch':'Crypto'},
    {'id':'dogecoin','name':'Dogecoin','sym':'DOGE','col':'#c2a633','bg':'rgba(194,166,51,.18)','type':'c','exch':'Crypto'},
    {'id':'avalanche-2','name':'Avalanche','sym':'AVAX','col':'#e84142','bg':'rgba(232,65,66,.18)','type':'c','exch':'Crypto'},
    {'id':'chainlink','name':'Chainlink','sym':'LINK','col':'#2a5ada','bg':'rgba(42,90,218,.18)','type':'c','exch':'Crypto'},
    {'id':'near','name':'NEAR','sym':'NEAR','col':'#00c1de','bg':'rgba(0,193,222,.18)','type':'c','exch':'Crypto'},
    {'id':'polkadot','name':'Polkadot','sym':'DOT','col':'#e6007a','bg':'rgba(230,0,122,.18)','type':'c','exch':'Crypto'},
    {'id':'uniswap','name':'Uniswap','sym':'UNI','col':'#ff007a','bg':'rgba(255,0,122,.18)','type':'c','exch':'Crypto'},
    {'id':'litecoin','name':'Litecoin','sym':'LTC','col':'#bfbbbb','bg':'rgba(191,187,187,.15)','type':'c','exch':'Crypto'},
    {'id':'tron','name':'TRON','sym':'TRX','col':'#ff0013','bg':'rgba(255,0,19,.18)','type':'c','exch':'Crypto'},
    {'id':'stellar','name':'Stellar','sym':'XLM','col':'#08b5e5','bg':'rgba(8,181,229,.18)','type':'c','exch':'Crypto'},
  ]
}

@app.route('/api/prices')
def prices():
    with _lock:
        return jsonify({'prices': _cache, 'age': round(time.time()-_last_fetch), 'ok': bool(_cache)})

@app.route('/api/assets')
def assets():
    return jsonify(ASSETS)

@app.route('/')
@app.route('/<path:f>')
def serve(f='index.html'):
    return send_from_directory('.', f)

if __name__ == '__main__':
    print("TradeX starting — fetching prices…")
    threading.Thread(target=loop, daemon=True).start()
    while not _last_fetch: time.sleep(0.4)
    print("Ready → http://localhost:5000")
    app.run(host='0.0.0.0', port=int(__import__('os').environ.get('PORT', 5000)))
