"""
Scanner — Radar Crypto PRO
Escanea los 30 pares con los 4 indicadores
"""
import time
from datetime import datetime, timezone
from binance_api import get_klines, get_price, get_24h_volume_usdt
from indicators import (
    calc_ema, calc_adx, calc_atr, calc_rsi, calc_vwap,
    check_rfibonacci, check_breaker_block, check_squeeze_momentum, check_keltner
)
from state import load_config, en_enfriamiento, pares_activos

VOLUMEN_MINIMO_USDT = 10_000_000

INDICADORES = [
    {"nombre": "RFibonacci",      "tipo": "alcista", "tf": "4h"},
    {"nombre": "Breaker Block",   "tipo": "alcista", "tf": "4h"},
    {"nombre": "Squeeze Momentum","tipo": "lateral", "tf": "4h"},
    {"nombre": "Canal Keltner",   "tipo": "lateral", "tf": "4h"},
]


def calc_sl(precio, atr, tipo_ind, comision):
    com = comision / 100
    if tipo_ind == "Breaker Block":
        return round(precio - atr * 1.0 - precio * com, 8)
    elif tipo_ind == "Squeeze Momentum":
        return round(precio - atr * 1.0 - precio * com, 8)
    elif tipo_ind == "Canal Keltner":
        return round(precio - atr * 0.8 - precio * com, 8)
    else:  # RFibonacci
        return round(precio - atr * 1.0 - precio * com, 8)


def calc_tp(precio, atr, tipo_ind, comision):
    com = comision / 100
    if tipo_ind == "Breaker Block":
        return round(precio + atr * 3.0 + precio * com, 8)
    elif tipo_ind == "Canal Keltner":
        return round(precio + atr * 1.5 + precio * com, 8)
    elif tipo_ind == "Squeeze Momentum":
        return round(precio + atr * 2.0 + precio * com, 8)
    else:  # RFibonacci
        return round(precio + atr * 2.0 + precio * com, 8)


def escanear_par(symbol, indicador, state):
    """Escanea un par con un indicador específico"""
    config = load_config()
    comision = config.get("comision", 0.2)

    # Verificar enfriamiento
    if en_enfriamiento(state, symbol):
        return None

    # Verificar si ya está activo
    if symbol in pares_activos(state):
        return None

    # Obtener velas
    velas = get_klines(symbol, indicador["tf"], 220)
    if not velas:
        return None

    closes  = velas["closes"]
    highs   = velas["highs"]
    lows    = velas["lows"]
    volumes = velas["volumes"]

    if len(closes) < 60:
        return None

    # Precio actual
    precio = get_price(symbol)
    if not precio:
        return None

    # Filtro volumen 10M diario
    vol_diario = sum(volumes[-6:]) * precio
    if vol_diario < VOLUMEN_MINIMO_USDT:
        return None

    # Calcular indicadores base
    atr     = calc_atr(highs, lows, closes, 14)
    adx     = calc_adx(highs, lows, closes, 14)
    rsi     = calc_rsi(closes, 14)
    ema200  = calc_ema(closes, 200)
    vwap    = calc_vwap(highs, lows, closes, volumes, 20)
    vol_ma  = sum(volumes[-20:]) / 20
    rvol    = volumes[-1] / vol_ma if vol_ma > 0 else 0

    # Filtro volatilidad mínima
    if precio < 0.01 or (atr / precio) * 100 < 1.5:
        return None

    # Verificar condición del indicador
    ok = False
    nombre = indicador["nombre"]

    if nombre == "RFibonacci":
        ok = check_rfibonacci(highs, lows, closes, volumes, precio, ema200, adx, vwap)
    elif nombre == "Breaker Block":
        ok = check_breaker_block(highs, lows, closes, volumes, precio, ema200, adx, vwap)
    elif nombre == "Squeeze Momentum":
        ok = check_squeeze_momentum(highs, lows, closes, volumes, precio, ema200, vwap)
    elif nombre == "Canal Keltner":
        ok = check_keltner(highs, lows, closes, volumes, adx, rsi)

    if not ok:
        return None

    # Calcular niveles
    sl   = calc_sl(precio, atr, nombre, comision)
    tp   = calc_tp(precio, atr, nombre, comision)
    tp1  = round((precio + tp) / 2, 8)
    be   = round(precio * (1 + comision / 200), 8)

    return {
        "symbol":    symbol,
        "indicador": nombre,
        "tipo":      indicador["tipo"],
        "tf":        indicador["tf"],
        "precio":    precio,
        "sl":        sl,
        "tp":        tp,
        "tp1":       tp1,
        "be":        be,
        "atr":       round(atr, 6),
        "adx":       round(adx, 1),
        "rsi":       round(rsi, 1),
        "rvol":      round(rvol, 2),
        "vwap":      round(vwap, 4),
        "vol_diario_m": round(vol_diario / 1_000_000, 1),
    }


def escanear_todos(state):
    """Escanea todos los pares con todos los indicadores"""
    config = load_config()
    pares = config["pares"]
    lista_negra = set(config["lista_negra"])
    señales = []

    for indicador in INDICADORES:
        for symbol in pares:
            if symbol in lista_negra:
                continue
            try:
                señal = escanear_par(symbol, indicador, state)
                if señal:
                    señales.append(señal)
                time.sleep(0.2)  # Rate limit
            except Exception as e:
                print(f"[ERROR] escanear {symbol} {indicador['nombre']}: {e}")

    return señales
