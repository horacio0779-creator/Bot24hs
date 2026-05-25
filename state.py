"""
Estado — BTC DCA Bot
"""
import json
import os
from datetime import datetime, timezone

STATE_FILE = "state_dca.json"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "capital_libre": 200.0,
        "resultado_total": 0.0,
        "posicion": None,  # posicion activa
        "stats": {
            "total_ops": 0,
            "total_wins": 0,
            "ganancia_total": 0.0,
            "max_recompras_usadas": 0
        }
    }


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_config():
    with open("config.json") as f:
        return json.load(f)


def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)


def capital_en_posicion(state):
    pos = state.get("posicion")
    if not pos:
        return 0.0
    return sum(e["usdt"] for e in pos["entradas"])


def recompras_posibles(state):
    config = load_config()
    entrada = config["entrada_por_compra"]
    libre = state["capital_libre"]
    return int(libre // entrada)


def resumen(state):
    config = load_config()
    pos = state.get("posicion")
    en_pos = capital_en_posicion(state)
    recompras = recompras_posibles(state)
    capital_total = state["capital_libre"] + en_pos + state["resultado_total"]

    if pos:
        entradas = pos["entradas"]
        total_usdt = sum(e["usdt"] for e in entradas)
        promedio = sum(e["precio"] * e["usdt"] for e in entradas) / total_usdt
        tp = promedio * (1 + config["tp_pct"] / 100)
        niveles = len(entradas) - 1
    else:
        promedio = tp = total_usdt = 0
        niveles = 0

    stats = state["stats"]
    wr = stats["total_wins"] / stats["total_ops"] * 100 if stats["total_ops"] > 0 else 0

    return {
        "capital_libre": round(state["capital_libre"], 2),
        "en_posicion": round(en_pos, 2),
        "capital_total": round(capital_total, 2),
        "resultado_total": round(state["resultado_total"], 2),
        "recompras_posibles": recompras,
        "en_posicion_activa": pos is not None,
        "niveles_dca": niveles,
        "promedio": round(promedio, 2),
        "tp": round(tp, 2),
        "total_usdt_pos": round(total_usdt, 2),
        "total_ops": stats["total_ops"],
        "total_wins": stats["total_wins"],
        "ganancia_total": round(stats["ganancia_total"], 2),
        "win_rate": round(wr, 1),
        "entrada_por_compra": config["entrada_por_compra"],
        "recompra_pct": config["recompra_pct"],
        "tp_pct": config["tp_pct"],
    }
