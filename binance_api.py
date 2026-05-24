"""
Binance API — Radar Crypto PRO
Modo paper trading: solo lectura, sin órdenes reales
"""
import requests
import time

BASE_URL = "https://api.binance.com"


def get_klines(symbol, interval="4h", limit=220):
    """Obtener velas de Binance"""
    try:
        url = f"{BASE_URL}/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        # Excluir la vela en formación (última)
        data = data[:-1]
        return {
            "opens":   [float(k[1]) for k in data],
            "highs":   [float(k[2]) for k in data],
            "lows":    [float(k[3]) for k in data],
            "closes":  [float(k[4]) for k in data],
            "volumes": [float(k[5]) for k in data],
        }
    except Exception as e:
        print(f"[ERROR] get_klines {symbol}: {e}")
        return None


def get_price(symbol):
    """Obtener precio actual"""
    try:
        url = f"{BASE_URL}/api/v3/ticker/price"
        r = requests.get(url, params={"symbol": symbol}, timeout=5)
        r.raise_for_status()
        return float(r.json()["price"])
    except Exception as e:
        print(f"[ERROR] get_price {symbol}: {e}")
        return None


def get_btc_data():
    """Obtener datos de BTC para el monitor"""
    try:
        velas = get_klines("BTCUSDT", "4h", 220)
        precio = get_price("BTCUSDT")
        if not velas or not precio:
            return None
        return {
            "precio": precio,
            "closes": velas["closes"],
            "highs":  velas["highs"],
            "lows":   velas["lows"],
            "volumes": velas["volumes"],
        }
    except Exception as e:
        print(f"[ERROR] get_btc_data: {e}")
        return None


def get_24h_volume_usdt(symbol):
    """Obtener volumen diario en USDT (últimas 6 velas 4h * precio)"""
    try:
        velas = get_klines(symbol, "4h", 10)
        precio = get_price(symbol)
        if not velas or not precio:
            return 0
        vol_6v = sum(velas["volumes"][-6:])
        return vol_6v * precio
    except:
        return 0
