"""
Trader — Radar Crypto PRO (Paper Trading)
Gestiona apertura, TP1, breakeven, TP final y SL
"""
from datetime import datetime, timezone
from binance_api import get_price
from state import save_state, agregar_enfriamiento, load_config


def abrir_operacion(state, señal, notificar):
    """Abre una operación en paper trading"""
    config = load_config()
    usdt = config["importe_por_operacion"]

    if state["capital"] < usdt:
        print(f"[WARN] Capital insuficiente para abrir {señal['symbol']}")
        return None

    operacion = {
        "id":            int(datetime.now(timezone.utc).timestamp() * 1000),
        "symbol":        señal["symbol"],
        "indicador":     señal["indicador"],
        "tipo":          señal["tipo"],
        "tf":            señal["tf"],
        "usdt":          usdt,
        "entrada":       señal["precio"],
        "sl":            señal["sl"],
        "tp":            señal["tp"],
        "tp1":           señal["tp1"],
        "be":            señal["be"],
        "atr":           señal["atr"],
        "adx":           señal["adx"],
        "rvol":          señal["rvol"],
        "vwap":          señal["vwap"],
        "estado":        "activa",
        "tp1_alcanzado": False,
        "usdt_restante": usdt,
        "ganancia_50":   0.0,
        "ts_apertura":   datetime.now(timezone.utc).isoformat(),
        "ts_cierre":     None,
        "precio_cierre": None,
        "resultado":     None,
    }

    state["capital"] -= usdt
    state["operaciones"].append(operacion)
    save_state(state)

    notificar(f"""
🔍 *OPERACIÓN ABIERTA*
📊 {señal['symbol']} · {señal['indicador']} · {señal['tf']}
💰 Entrada: `${señal['precio']}`
🎯 TP1 (50%): `${señal['tp1']}`
🚀 TP Final: `${señal['tp']}`
🛑 SL: `${señal['sl']}`
📈 ADX: {señal['adx']} · Vol: {señal['rvol']}x · VWAP: ✅
💵 Importe: ${usdt} USDT
""")
    return operacion


def verificar_operaciones(state, notificar):
    """Verifica TP1, TP final y SL para cada operación activa"""
    config = load_config()
    comision = config.get("comision", 0.2)
    cambios = False

    for op in state["operaciones"]:
        if op["estado"] != "activa":
            continue

        precio = get_price(op["symbol"])
        if not precio:
            continue

        pe = op["entrada"]

        # ── TP1: cierre parcial 50% ──
        if not op["tp1_alcanzado"] and op["tipo"] != "lateral" and precio >= op["tp1"]:
            mitad = op["usdt"] / 2
            com_venta = mitad * (comision / 200)
            gan_neta = ((precio - pe) / pe) * mitad - com_venta
            op["tp1_alcanzado"] = True
            op["usdt_restante"] = mitad
            op["ganancia_50"] = round(gan_neta, 4)
            op["sl"] = round(pe * (1 + comision / 200), 8)  # SL a breakeven
            state["resultado"] += gan_neta
            cambios = True

            notificar(f"""
🎯 *TP1 EJECUTADO — 50%*
📊 {op['symbol']} · {op['indicador']}
💵 Precio: `${precio}`
✅ Ganancia parcial: +${round(gan_neta, 4)} USDT
⚖️ SL movido a Breakeven: `${op['sl']}`
""")

        # ── TP FINAL ──
        elif precio >= op["tp"]:
            cerrar_operacion(state, op, "tp", precio, comision, notificar)
            cambios = True

        # ── STOP LOSS ──
        elif precio <= op["sl"]:
            cerrar_operacion(state, op, "sl", precio, comision, notificar)
            cambios = True

    if cambios:
        save_state(state)


def cerrar_operacion(state, op, motivo, precio, comision, notificar):
    """Cierra una operación y actualiza estadísticas"""
    pe = op["entrada"]
    base_usdt = op["usdt_restante"] if op["tp1_alcanzado"] else op["usdt"]
    com_venta = base_usdt * (comision / 200)
    pnl_restante = ((precio - pe) / pe) * base_usdt - com_venta
    pnl_total = round(pnl_restante + op["ganancia_50"], 4)

    op["estado"]       = "tp" if motivo == "tp" else "sl"
    op["ts_cierre"]    = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    op["precio_cierre"]= precio
    op["resultado"]    = pnl_total

    state["capital"]  += op["usdt"]
    state["resultado"] += pnl_restante

    stats = state["stats"]
    if pnl_total >= 0:
        stats["total_wins"] += 1
        stats["ganancia_total"] += pnl_total
        emoji = "🚀"
        titulo = "TAKE PROFIT"
    else:
        stats["total_losses"] += 1
        stats["perdida_total"] += abs(pnl_total)
        emoji = "🛑"
        titulo = "STOP LOSS"

    agregar_enfriamiento(state, op["symbol"])

    tot = stats["total_wins"] + stats["total_losses"]
    wr = f"{stats['total_wins']/tot*100:.1f}%" if tot > 0 else "—"

    notificar(f"""
{emoji} *{titulo}*
📊 {op['symbol']} · {op['indicador']}
💵 Precio cierre: `${precio}`
{'🎯 TP1 previo: +$'+str(op['ganancia_50'])+' USDT' if op['tp1_alcanzado'] else ''}
📊 Resultado total: {'+'if pnl_total>=0 else ''}${pnl_total} USDT
📈 Win Rate: {wr} ({stats['total_wins']}W / {stats['total_losses']}L)
❄️ {op['symbol']} en enfriamiento 24h
""")


def verificar_tiempo_sin_entrada(state, notificar):
    """Cancela operaciones que no entraron en 8 horas"""
    config = load_config()
    max_horas = config.get("max_horas_sin_entrada", 8)
    ahora = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    cambios = False

    for op in state["operaciones"]:
        if op["estado"] != "esperando":
            continue
        ts = __import__("datetime").datetime.fromisoformat(op["ts_apertura"])
        horas = (ahora - ts).total_seconds() / 3600
        if horas >= max_horas:
            op["estado"] = "cancelada"
            state["capital"] += op["usdt"]
            cambios = True
            notificar(f"""
⏰ *SEÑAL CANCELADA*
📊 {op['symbol']} · {op['indicador']}
❌ No llegó al precio de entrada en {max_horas}h
💵 ${op['usdt']} USDT devueltos al capital
""")

    if cambios:
        save_state(state)


def cerrar_todo_por_btc(state, notificar):
    """Cierra todas las operaciones activas por caída de BTC"""
    config = load_config()
    comision = config.get("comision", 0.2)
    activas = [op for op in state["operaciones"] if op["estado"] == "activa"]
    if not activas:
        return

    for op in activas:
        precio = get_price(op["symbol"]) or op["entrada"]
        cerrar_operacion(state, op, "sl", precio, comision,
                        lambda msg: None)  # notificar individualmente abajo

    total_cerradas = len(activas)
    save_state(state)
    notificar(f"""
🔴 *BTC CAYÓ BAJO EMA50 — CIERRE DE EMERGENCIA*
❌ {total_cerradas} operación(es) cerrada(s) a precio de mercado
💵 Todo convertido a USDT
⏳ Sistema bloqueado hasta que BTC confirme recuperación
""")
