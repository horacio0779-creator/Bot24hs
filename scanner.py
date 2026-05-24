"""
Scanner — Radar Crypto PRO
Solo Canal Keltner (60% WR histórico)
"""
import time
from binance_api import get_klines, get_price
from indicators import calc_ema, calc_adx, calc_atr, calc_rsi
from state import load_config, en_enfriamiento, pares_activos

VOLUMEN_MINIMO_USDT = 10_000_000


def calc_sl(precio, atr, comision):
    return round(precio - atr * 0.8 - precio * (comision/100), 8)

def calc_tp(precio, atr, comision):
    return round(precio + atr * 1.5 + precio * (comision/100), 8)


def escanear_par(symbol, state):
    config = load_config()
    comision = config.get("comision", 0.2)

    if en_enfriamiento(state, symbol):
        return None
    if symbol in pares_activos(state):
        return None

    velas = get_klines(symbol, "4h", 220)
    if not velas:
        return None

    cl = velas["closes"]; hi = velas["highs"]
    lo = velas["lows"];   vo = velas["volumes"]

    if len(cl) < 60:
        return None

    precio = get_price(symbol)
    if not precio:
        return None

    # Filtro volumen 10M diario
    vol_diario = sum(vo[-6:]) * precio
    if vol_diario < VOLUMEN_MINIMO_USDT:
        return None

    atr   = calc_atr(hi, lo, cl, 14)
    adx   = calc_adx(hi, lo, cl, 14)
    rsi   = calc_rsi(cl, 14)
    vol_ma = sum(vo[-20:]) / 20

    if precio < 0.01 or (atr/precio)*100 < 1.5:
        return None

    # Canal Keltner: ADX<20 + RSI<35 + volumen bajo
    ok = adx < 20 and rsi < 35 and vo[-1] < vol_ma * 0.8

    if not ok:
        return None

    sl = calc_sl(precio, atr, comision)
    tp = calc_tp(precio, atr, comision)
    be = round(precio * (1 + comision/200), 8)

    return {
        "symbol":    symbol,
        "indicador": "Canal Keltner",
        "tipo":      "lateral",
        "tf":        "4h",
        "precio":    precio,
        "sl":        sl,
        "tp":        tp,
        "tp1":       round((precio+tp)/2, 8),
        "be":        be,
        "atr":       round(atr, 6),
        "adx":       round(adx, 1),
        "rvol":      round(vo[-1]/vol_ma, 2) if vol_ma > 0 else 0,
        "vwap":      precio,
        "vol_diario_m": round(vol_diario/1_000_000, 1),
    }


def escanear_todos(state):
    config = load_config()
    pares = config["pares"]
    lista_negra = set(config["lista_negra"])
    senales = []

    for symbol in pares:
        if symbol in lista_negra:
            continue
        try:
            senal = escanear_par(symbol, state)
            if senal:
                senales.append(senal)
            time.sleep(0.2)
        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")

    return senales
