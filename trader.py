"""
Trader — BTC DCA Bot
Lógica de entradas, recompras y TP
"""
import requests
from datetime import datetime, timezone
from state import load_state, save_state, load_config, capital_en_posicion

BINANCE = "https://api.binance.com"


def get_btc_price():
    try:
        r = requests.get(f"{BINANCE}/api/v3/ticker/price", params={"symbol": "BTCUSDT"}, timeout=5)
        return float(r.json()["price"])
    except:
        return None


def verificar_posicion(notificar):
    """Verifica si hay que entrar, recomprar o cerrar"""
    state = load_state()
    config = load_config()
    precio = get_btc_price()
    if not precio:
        return

    entrada = config["entrada_por_compra"]
    recompra_pct = config["recompra_pct"]
    tp_pct = config["tp_pct"]
    com = config["comision"] / 100

    pos = state.get("posicion")

    # ── Sin posición: entrar ──
    if not pos:
        if state["capital_libre"] >= entrada:
            state["posicion"] = {
                "entradas": [{"precio": precio, "usdt": entrada, "ts": datetime.now(timezone.utc).isoformat()}],
                "ts_apertura": datetime.now(timezone.utc).isoformat()
            }
            state["capital_libre"] -= entrada
            save_state(state)
            notificar(f"""
₿ *ENTRADA BTC DCA*
💰 Precio: `${precio:,.0f}`
💵 Invertido: ${entrada} USDT
💼 Capital libre: ${round(state['capital_libre'], 2)} USDT
🔄 Recompras posibles: {int(state['capital_libre'] // entrada)}
""")
        return

    entradas = pos["entradas"]
    total_usdt = sum(e["usdt"] for e in entradas)
    promedio = sum(e["precio"] * e["usdt"] for e in entradas) / total_usdt
    tp = promedio * (1 + tp_pct / 100)

    # ── Verificar TP ──
    if precio >= tp:
        gan = sum(((tp - e["precio"]) / e["precio"]) * e["usdt"] - e["usdt"] * (com / 2) for e in entradas)
        gan = round(gan, 4)

        state["capital_libre"] += total_usdt + gan
        state["resultado_total"] += gan
        state["posicion"] = None

        stats = state["stats"]
        stats["total_ops"] += 1
        stats["total_wins"] += 1
        stats["ganancia_total"] += gan
        stats["max_recompras_usadas"] = max(stats["max_recompras_usadas"], len(entradas) - 1)
        save_state(state)

        notificar(f"""
✅ *TAKE PROFIT BTC*
💰 TP alcanzado: `${tp:,.0f}`
📊 Promedio fue: `${promedio:,.0f}`
🔄 Recompras usadas: {len(entradas)-1}
💵 Ganancia: +${gan} USDT
📈 Total ganado: +${round(state['resultado_total'],2)} USDT
💼 Capital libre: ${round(state['capital_libre'],2)} USDT
""")
        return

    # ── Verificar recompra ──
    precio_entrada1 = entradas[0]["precio"]
    nivel_actual = len(entradas) - 1
    umbral_recompra = precio_entrada1 * (1 - (recompra_pct / 100) * (nivel_actual + 1))

    if precio <= umbral_recompra and state["capital_libre"] >= entrada:
        entradas.append({"precio": precio, "usdt": entrada, "ts": datetime.now(timezone.utc).isoformat()})
        state["capital_libre"] -= entrada

        # Recalcular promedio y TP nuevo
        total_u = sum(e["usdt"] for e in entradas)
        nuevo_prom = sum(e["precio"] * e["usdt"] for e in entradas) / total_u
        nuevo_tp = nuevo_prom * (1 + tp_pct / 100)
        caida_desde_entrada = ((precio_entrada1 - precio) / precio_entrada1) * 100

        save_state(state)
        notificar(f"""
🔄 *RECOMPRA DCA #{nivel_actual+1}*
💰 Precio: `${precio:,.0f}`
📉 Caída desde entrada: -{caida_desde_entrada:.1f}%
📊 Nuevo promedio: `${nuevo_prom:,.0f}`
🎯 Nuevo TP: `${nuevo_tp:,.0f}`
💵 Invertido total: ${round(total_u,2)} USDT
💼 Capital libre: ${round(state['capital_libre'],2)} USDT
🔄 Recompras posibles: {int(state['capital_libre'] // entrada)}
""")


def estado_posicion(state):
    """Retorna info de la posición activa"""
    config = load_config()
    pos = state.get("posicion")
    if not pos:
        return None
    precio = get_btc_price() or 0
    entradas = pos["entradas"]
    total_usdt = sum(e["usdt"] for e in entradas)
    promedio = sum(e["precio"] * e["usdt"] for e in entradas) / total_usdt
    tp = promedio * (1 + config["tp_pct"] / 100)
    pnl_actual = ((precio - promedio) / promedio) * total_usdt if precio > 0 else 0
    caida = ((entradas[0]["precio"] - precio) / entradas[0]["precio"]) * 100 if precio > 0 else 0
    return {
        "precio_actual": precio,
        "precio_entrada1": entradas[0]["precio"],
        "promedio": round(promedio, 0),
        "tp": round(tp, 0),
        "total_usdt": round(total_usdt, 2),
        "niveles": len(entradas) - 1,
        "pnl_actual": round(pnl_actual, 4),
        "caida_pct": round(caida, 1),
        "pct_al_tp": round(((tp - precio) / precio) * 100, 2) if precio > 0 else 0,
    }
