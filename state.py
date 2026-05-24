"""
Estado del bot — Radar Crypto PRO
Maneja capital, operaciones, enfriamiento y estadísticas
"""
import json
import os
from datetime import datetime, timezone

STATE_FILE = "state.json"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {
        "capital": 200.0,
        "resultado": 0.0,
        "operaciones": [],
        "enfriamiento": {},
        "btc_bloqueado": False,
        "velas_confirmacion": 0,
        "stats": {
            "total_wins": 0,
            "total_losses": 0,
            "ganancia_total": 0.0,
            "perdida_total": 0.0,
        }
    }


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)


def agregar_enfriamiento(state, symbol):
    state["enfriamiento"][symbol] = datetime.now(timezone.utc).isoformat()
    save_state(state)


def en_enfriamiento(state, symbol):
    ts = state["enfriamiento"].get(symbol)
    if not ts:
        return False
    desde = datetime.fromisoformat(ts)
    ahora = datetime.now(timezone.utc)
    horas = (ahora - desde).total_seconds() / 3600
    config = load_config()
    if horas >= config.get("enfriamiento_horas", 24):
        del state["enfriamiento"][symbol]
        save_state(state)
        return False
    return True


def tiempo_enfriamiento_restante(state, symbol):
    ts = state["enfriamiento"].get(symbol)
    if not ts:
        return None
    desde = datetime.fromisoformat(ts)
    ahora = datetime.now(timezone.utc)
    config = load_config()
    limite = config.get("enfriamiento_horas", 24) * 3600
    restante = limite - (ahora - desde).total_seconds()
    if restante <= 0:
        return None
    h = int(restante // 3600)
    m = int((restante % 3600) // 60)
    return f"{h}h {m}m"


def pares_activos(state):
    return set(
        op["symbol"] for op in state["operaciones"]
        if op["estado"] in ["esperando", "activa"]
    )


def get_operacion(state, symbol):
    for op in state["operaciones"]:
        if op["symbol"] == symbol and op["estado"] in ["esperando", "activa"]:
            return op
    return None


def win_rate(state):
    stats = state["stats"]
    tot = stats["total_wins"] + stats["total_losses"]
    if tot == 0:
        return None
    return stats["total_wins"] / tot * 100


def resumen_stats(state):
    stats = state["stats"]
    config = load_config()
    tot = stats["total_wins"] + stats["total_losses"]
    wr = f"{stats['total_wins']/tot*100:.1f}%" if tot > 0 else "—"
    capital_actual = config["capital"] + state["resultado"]
    return {
        "capital_inicial": config["capital"],
        "capital_actual": round(capital_actual, 2),
        "resultado": round(state["resultado"], 2),
        "wins": stats["total_wins"],
        "losses": stats["total_losses"],
        "total": tot,
        "win_rate": wr,
        "ganancia_total": round(stats["ganancia_total"], 2),
        "perdida_total": round(stats["perdida_total"], 2),
    }
