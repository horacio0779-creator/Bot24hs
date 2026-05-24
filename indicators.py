"""
Indicadores técnicos — Radar Crypto PRO
"""
import numpy as np


def calc_ema(closes, period):
    closes = np.array(closes, dtype=float)
    k = 2 / (period + 1)
    ema = [closes[0]]
    for c in closes[1:]:
        ema.append(c * k + ema[-1] * (1 - k))
    return ema[-1]


def calc_ema_series(closes, period):
    closes = np.array(closes, dtype=float)
    k = 2 / (period + 1)
    ema = [closes[0]]
    for c in closes[1:]:
        ema.append(c * k + ema[-1] * (1 - k))
    return ema


def calc_atr(highs, lows, closes, period=14):
    tr = []
    for i in range(1, len(closes)):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        ))
    return sum(tr[-period:]) / period if len(tr) >= period else sum(tr) / len(tr)


def calc_adx(highs, lows, closes, period=14):
    highs = list(highs)
    lows = list(lows)
    closes = list(closes)
    n = len(closes)
    if n < period + 1:
        return 0
    dm_plus, dm_minus, tr_list = [], [], []
    for i in range(1, n):
        h_diff = highs[i] - highs[i-1]
        l_diff = lows[i-1] - lows[i]
        dm_plus.append(h_diff if h_diff > l_diff and h_diff > 0 else 0)
        dm_minus.append(l_diff if l_diff > h_diff and l_diff > 0 else 0)
        tr_list.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        ))
    def smooth(data, p):
        s = sum(data[:p])
        result = [s]
        for v in data[p:]:
            s = s - s/p + v
            result.append(s)
        return result
    str_ = smooth(tr_list, period)
    sdp = smooth(dm_plus, period)
    sdm = smooth(dm_minus, period)
    di_plus = [100 * sdp[i] / str_[i] if str_[i] > 0 else 0 for i in range(len(str_))]
    di_minus = [100 * sdm[i] / str_[i] if str_[i] > 0 else 0 for i in range(len(str_))]
    dx = [100 * abs(di_plus[i] - di_minus[i]) / (di_plus[i] + di_minus[i])
          if (di_plus[i] + di_minus[i]) > 0 else 0
          for i in range(len(di_plus))]
    return sum(dx[-period:]) / period if len(dx) >= period else 0


def calc_rsi(closes, period=14):
    closes = list(closes)
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    if len(gains) < period:
        return 50
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_vwap(highs, lows, closes, volumes, period=20):
    h = list(highs[-period:])
    l = list(lows[-period:])
    c = list(closes[-period:])
    v = list(volumes[-period:])
    sum_pv = sum(((h[i]+l[i]+c[i])/3) * v[i] for i in range(len(c)))
    sum_v = sum(v)
    return sum_pv / sum_v if sum_v > 0 else closes[-1]


def calc_squeeze(highs, lows, closes, period=20, mult_bb=2.0, mult_kc=1.5):
    h = list(highs[-period:])
    l = list(lows[-period:])
    c = list(closes[-period:])
    mean = sum(c) / period
    std = (sum((x - mean)**2 for x in c) / period) ** 0.5
    bb_upper = mean + mult_bb * std
    bb_lower = mean - mult_bb * std
    atr = calc_atr(highs, lows, closes, period)
    ema = calc_ema(closes, period)
    kc_upper = ema + mult_kc * atr
    kc_lower = ema - mult_kc * atr
    in_squeeze = bb_upper < kc_upper and bb_lower > kc_lower
    mid_hl = (max(h) + min(l)) / 2
    mid_cl = sum(c) / period
    momentum = closes[-1] - ((mid_hl + mid_cl) / 2)
    return {"in_squeeze": in_squeeze, "momentum": momentum}


def check_rfibonacci(highs, lows, closes, volumes, precio, ema200, adx, vwap):
    """RFibonacci: ADX>25 en 3 velas, precio sobre EMA en 3 velas, vol>1x, precio>VWAP"""
    if len(closes) < 10:
        return False
    ema_series = calc_ema_series(closes, 20)
    adx3 = [calc_adx(highs[:-3+i] if i < 3 else highs, lows[:-3+i] if i < 3 else lows,
                     closes[:-3+i] if i < 3 else closes, 14) for i in range(3)]
    # Simplificado: usar ADX actual para las 3 velas
    vol_ma = sum(volumes[-20:]) / 20
    rvol = volumes[-1] / vol_ma if vol_ma > 0 else 0
    pr3 = closes[-3:]
    ema3 = ema_series[-3:]
    adx_ok = adx > 25
    precio_ema_ok = all(pr3[i] > ema3[i] for i in range(len(pr3)))
    vol_ok = rvol > 1.0
    vwap_ok = precio > vwap
    return adx_ok and precio_ema_ok and vol_ok and vwap_ok


def check_breaker_block(highs, lows, closes, volumes, precio, ema200, adx, vwap):
    """Breaker Block: fake out + breakout + retroceso al bloque"""
    if len(closes) < 15:
        return False
    ema50 = calc_ema(closes, 50)
    min_rec = min(lows[-10:-1])
    max_rec = max(highs[-10:-1])
    vol_ma = sum(volumes[-20:]) / 20
    hubo_fake_out = any(l < min_rec * 0.995 for l in lows[-6:-1])
    hubo_breakout = closes[-2] > max_rec * 0.998
    en_retroceso = max_rec * 0.990 <= precio <= max_rec * 1.005
    sobre_emas = precio > ema50 and precio > ema200
    vol_breakout = volumes[-2] > vol_ma * 1.2
    vwap_ok = precio > vwap
    return hubo_fake_out and hubo_breakout and en_retroceso and sobre_emas and vol_breakout and adx > 25 and vwap_ok


def check_squeeze_momentum(highs, lows, closes, volumes, precio, ema200, vwap):
    """Squeeze Momentum: liberacion de squeeze con momentum positivo y creciente"""
    if len(closes) < 25:
        return False
    sq = calc_squeeze(highs, lows, closes, 20)
    sq_ant = calc_squeeze(highs[:-1], lows[:-1], closes[:-1], 20)
    sq_prev = calc_squeeze(highs[:-2], lows[:-2], closes[:-2], 20)
    vol_ma = sum(volumes[-20:]) / 20
    rvol = volumes[-1] / vol_ma if vol_ma > 0 else 0
    squeeze_liberado = sq_ant["in_squeeze"] and not sq["in_squeeze"]
    momentum_creciente = sq["momentum"] > 0 and sq["momentum"] > sq_prev["momentum"]
    vwap_ok = precio > vwap
    return squeeze_liberado and momentum_creciente and precio > ema200 and vwap_ok and rvol > 1.1


def check_keltner(highs, lows, closes, volumes, adx, rsi):
    """Canal Keltner: mercado en rango, RSI bajo, volumen bajo"""
    if len(closes) < 20:
        return False
    vol_ma = sum(volumes[-20:]) / 20
    adx_ok = adx < 20
    rsi_ok = rsi < 35
    vol_ok = vol_ma > 0 and volumes[-1] < vol_ma * 0.8
    return adx_ok and rsi_ok and vol_ok
