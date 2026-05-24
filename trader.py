"""
Trader — Radar Crypto PRO (Paper Trading)
Cierre total 100% en TP o SL — sin parciales
"""
from datetime import datetime, timezone
from binance_api import get_price
from state import save_state, agregar_enfriamiento, load_config


def abrir_operacion(state, señal, notificar):
    config = load_config()
    usdt = config["importe_por_operacion"]
    if state["capital"] < usdt:
        print(f"[WARN] Capital insuficiente para {señal['symbol']}")
        return None

    operacion = {
        "id":          int(datetime.now(timezone.utc).timestamp() * 1000),
        "symbol":      señal["symbol"],
        "indicador":   señal["indicador"],
        "tipo":        señal["tipo"],
        "tf":          señal["tf"],
        "usdt":        usdt,
        "entrada":     señal["precio"],
        "sl":          señal["sl"],
        "tp":          señal["tp"],
        "be":          señal["be"],
        "atr":         señal["atr"],
        "adx":         señal["adx"],
        "rvol":        señal["rvol"],
        "vwap":        señal["vwap"],
        "estado":      "activa",
        "ts_apertura": datetime.now(timezone.utc).isoformat(),
        "ts_cierre":   None,
        "precio_cierre": None,
        "resultado":   None,
    }

    state["capital"] -= usdt
    state["operaciones"].append(operacion)
    save_state(state)

    notificar(f"""
🔍 *OPERACIÓN ABIERTA*
📊 {señal['symbol']} · {señal['indicador']} · {señal['tf']}
💰 Entrada: `${señal['precio']}`
🚀 TP: `${señal['tp']}`
🛑 SL: `${señal['sl']}`
📈 ADX: {señal['adx']} · Vol: {señal['rvol']}x · VWAP: ✅
💵 Importe: ${usdt} USDT
""")
    return operacion


def verificar_operaciones(state, notificar):
    config = load_config()
    comision = config.get("comision", 0.2)
    cambios = False

    for op in state["operaciones"]:
        if op["estado"] != "activa":
            continue
        precio = get_price(op["symbol"])
        if not precio:
            continue

        if precio >= op["tp"]:
            cerrar_operacion(state, op, "tp", precio, comision, notificar)
            cambios = True
        elif precio <= op["sl"]:
            cerrar_operacion(state, op, "sl", precio, comision, notificar)
            cambios = True

    if cambios:
        save_state(state)


def cerrar_operacion(state, op, motivo, precio, comision, notificar):
    pe = op["entrada"]
    usdt = op["usdt"]
    com_venta = usdt * (comision / 200)
    pnl = round(((precio - pe) / pe) * usdt - com_venta, 4)

    op["estado"]        = "tp" if motivo == "tp" else "sl"
    op["ts_cierre"]     = datetime.now(timezone.utc).isoformat()
    op["precio_cierre"] = precio
    op["resultado"]     = pnl

    state["capital"]   += usdt
    state["resultado"] += pnl

    stats = state["stats"]
    if pnl >= 0:
        stats["total_wins"] += 1
        stats["ganancia_total"] += pnl
        emoji = "🚀"; titulo = "TAKE PROFIT"
    else:
        stats["total_losses"] += 1
        stats["perdida_total"] += abs(pnl)
        emoji = "🛑"; titulo = "STOP LOSS"

    agregar_enfriamiento(state, op["symbol"])

    tot = stats["total_wins"] + stats["total_losses"]
    wr = f"{stats['total_wins']/tot*100:.1f}%" if tot > 0 else "—"

    notificar(f"""
{emoji} *{titulo}*
📊 {op['symbol']} · {op['indicador']}
💵 Precio cierre: `${precio}`
📊 Resultado: {'+'if pnl>=0 else ''}${pnl} USDT
📈 Win Rate: {wr} ({stats['total_wins']}W / {stats['total_losses']}L)
❄️ {op['symbol']} en enfriamiento 24h
""")


def verificar_tiempo_sin_entrada(state, notificar):
    config = load_config()
    max_horas = config.get("max_horas_sin_entrada", 8)
    ahora = datetime.now(timezone.utc)
    cambios = False

    for op in state["operaciones"]:
        if op["estado"] != "activa":
            continue
        ts = datetime.fromisoformat(op["ts_apertura"])
        horas = (ahora - ts).total_seconds() / 3600
        if horas >= max_horas:
            op["estado"] = "cancelada"
            state["capital"] += op["usdt"]
            cambios = True
            notificar(f"""
⏰ *SEÑAL CANCELADA*
📊 {op['symbol']} · {op['indicador']}
❌ No llegó al precio en {max_horas}h
💵 ${op['usdt']} USDT devueltos
""")

    if cambios:
        save_state(state)


def cerrar_todo_por_btc(state, notificar):
    config = load_config()
    comision = config.get("comision", 0.2)
    activas = [op for op in state["operaciones"] if op["estado"] == "activa"]
    if not activas:
        return

    for op in activas:
        precio = get_price(op["symbol"]) or op["entrada"]
        cerrar_operacion(state, op, "sl", precio, comision, lambda msg: None)

    save_state(state)
    notificar(f"""
🔴 *BTC CAYÓ BAJO EMA50 — CIERRE DE EMERGENCIA*
❌ {len(activas)} operación(es) cerrada(s) a mercado
💵 Todo convertido a USDT
⏳ Sistema bloqueado hasta recuperación de BTC
""")
