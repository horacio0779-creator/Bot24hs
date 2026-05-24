"""
Monitor BTC — Radar Crypto PRO
Bloquea/desbloquea el sistema según EMA50 + ADX + Volumen
"""
from binance_api import get_btc_data
from indicators import calc_ema, calc_adx, calc_atr
from state import save_state, load_config


def verificar_btc(state, notificar):
    """
    Verifica estado de BTC:
    - BLOQUEO: vela 4h cierra bajo EMA50
    - DESBLOQUEO: precio sobre EMA50 + ADX>25 + volumen sobre promedio
    """
    data = get_btc_data()
    if not data:
        return state.get("btc_bloqueado", False)

    closes  = data["closes"]
    highs   = data["highs"]
    lows    = data["lows"]
    volumes = data["volumes"]
    precio  = data["precio"]

    ema50   = calc_ema(closes, 50)
    adx     = calc_adx(highs, lows, closes, 14)
    vol_ma  = sum(volumes[-20:]) / 20
    hay_vol = volumes[-2] > vol_ma  # ultima vela cerrada

    ultima_vela_cerro    = closes[-1]  # ultima cerrada
    anterior_vela_cerro  = closes[-2]

    btc_bloqueado = state.get("btc_bloqueado", False)

    # ── BLOQUEO: vela cerrada bajo EMA50 ──
    if not btc_bloqueado and ultima_vela_cerro < ema50:
        state["btc_bloqueado"] = True
        state["velas_confirmacion"] = 0
        save_state(state)
        notificar(f"""
🔴 *BTC BAJO EMA50 — SISTEMA BLOQUEADO*
📉 BTC: `${precio:.0f}` · EMA50: `${ema50:.0f}`
⚠️ Para desbloquear: precio sobre EMA50 + ADX>25 + volumen
""")
        return True

    # ── DESBLOQUEO: precio sobre EMA50 + ADX>25 + volumen ──
    if btc_bloqueado:
        precio_ok = precio > ema50
        adx_ok    = adx > 25
        vol_ok    = hay_vol

        if precio_ok and adx_ok and vol_ok:
            state["btc_bloqueado"] = False
            state["velas_confirmacion"] = 1
            save_state(state)
            notificar(f"""
🟢 *BTC RECUPERADO — SISTEMA HABILITADO*
📈 BTC: `${precio:.0f}` · EMA50: `${ema50:.0f}`
📊 ADX: {adx:.1f} ✅ · Volumen: ✅
✅ Podés operar normalmente
""")
            return False
        else:
            falta = []
            if not precio_ok: falta.append(f"Precio bajo EMA50 (${precio:.0f} < ${ema50:.0f})")
            if not adx_ok:    falta.append(f"ADX {adx:.1f} (necesita >25)")
            if not vol_ok:    falta.append("Volumen insuficiente")
            print(f"[BTC] Bloqueado. Falta: {', '.join(falta)}")
            return True

    return btc_bloqueado


def btc_esta_bloqueado(state):
    return state.get("btc_bloqueado", False)
