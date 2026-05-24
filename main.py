"""
Main — Radar Crypto PRO
"""
import logging
import os
import time
import threading
from datetime import datetime, timezone, timedelta

from state import load_state, load_config
from btc_monitor import verificar_btc, btc_esta_bloqueado
from horario import esta_habilitado
from scanner import escanear_todos
from trader import abrir_operacion, verificar_operaciones, verificar_tiempo_sin_entrada
from telegram_bot import notificar, registrar_comandos

logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

INTERVALO_PRECIOS  = 30
INTERVALO_ESCANEO  = 4 * 3600
INTERVALO_BTC      = 5 * 60
INTERVALO_CANCELAR = 30 * 60

ultimo_escaneo  = 0
ultimo_btc      = 0
ultimo_cancelar = 0
ultimo_resumen  = ""


def worker():
    global ultimo_escaneo, ultimo_btc, ultimo_cancelar, ultimo_resumen

    time.sleep(3)
    log.info("Radar Crypto PRO iniciado")
    notificar("🛰️ *Radar Crypto PRO iniciado*\nMonitoreando el mercado 24/7...")

    while True:
        try:
            ahora = time.time()
            state = load_state()

            if ahora - ultimo_btc >= INTERVALO_BTC:
                verificar_btc(state, notificar)
                ultimo_btc = ahora

            verificar_operaciones(state, notificar)

            if ahora - ultimo_cancelar >= INTERVALO_CANCELAR:
                verificar_tiempo_sin_entrada(state, notificar)
                ultimo_cancelar = ahora

            if ahora - ultimo_escaneo >= INTERVALO_ESCANEO:
                if btc_esta_bloqueado(state):
                    log.info("[SCAN] Bloqueado por BTC")
                elif not esta_habilitado():
                    log.info("[SCAN] Bloqueado por horario")
                else:
                    log.info("[SCAN] Iniciando escaneo...")
                    notificar("🔍 *Iniciando escaneo...*")
                    señales = escanear_todos(state)
                    if señales:
                        for s in señales:
                            state = load_state()
                            abrir_operacion(state, s, notificar)
                    else:
                        notificar("🔍 Sin señales en este ciclo")
                ultimo_escaneo = ahora

            ahora_arg = datetime.now(timezone.utc) - timedelta(hours=3)
            clave = ahora_arg.strftime("%Y-%m-%d")
            if ahora_arg.hour == 18 and ahora_arg.minute < 5 and ultimo_resumen != clave:
                ultimo_resumen = clave
                enviar_resumen_diario(state)
                if ahora_arg.weekday() == 4:
                    enviar_resumen_semanal(state)

            time.sleep(INTERVALO_PRECIOS)

        except Exception as e:
            log.error(f"[ERROR] {e}")
            time.sleep(60)


def enviar_resumen_diario(state):
    ahora = datetime.now(timezone.utc)
    inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    ops = [o for o in state["operaciones"]
           if o.get("ts_cierre") and datetime.fromisoformat(o["ts_cierre"]) >= inicio]
    wins   = [o for o in ops if o["estado"] == "tp"]
    losses = [o for o in ops if o["estado"] == "sl"]
    gan    = sum(o.get("resultado", 0) for o in wins)
    per    = sum(o.get("resultado", 0) for o in losses)
    neto   = round(gan + per, 4)
    wr     = f"{len(wins)/(len(wins)+len(losses))*100:.1f}%" if ops else "—"
    config = load_config()
    capital_actual = config["capital"] + state["resultado"]
    notificar(f"""
📊 *RESUMEN DIARIO — {ahora.strftime('%d/%m/%Y')}*

✅ Ganadas: {len(wins)} (+${round(gan,4)} USDT)
❌ Perdidas: {len(losses)} (${round(per,4)} USDT)
🎯 Win Rate: {wr}
📈 Neto: {'+'if neto>=0 else ''}${neto} USDT
💵 Capital: ${round(capital_actual,2)} USDT
""")


def main():
    # Iniciar worker en hilo separado
    t = threading.Thread(target=worker, daemon=True)
    t.start()

    # Iniciar bot de Telegram (bloqueante)
    bot = registrar_comandos()
    log.info("[TELEGRAM] Escuchando comandos...")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)


if __name__ == "__main__":
    main()


def enviar_resumen_semanal(state):
    from datetime import datetime, timezone, timedelta
    ahora = datetime.now(timezone.utc)
    inicio_semana = ahora - timedelta(days=ahora.weekday())
    inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)
    ops = [o for o in state["operaciones"]
           if o.get("ts_cierre") and datetime.fromisoformat(o["ts_cierre"]) >= inicio_semana]
    wins   = [o for o in ops if o["estado"] == "tp"]
    losses = [o for o in ops if o["estado"] == "sl"]
    gan    = sum(o.get("resultado", 0) for o in wins)
    per    = sum(o.get("resultado", 0) for o in losses)
    neto   = round(gan + per, 4)
    wr     = f"{len(wins)/(len(wins)+len(losses))*100:.1f}%" if ops else "—"
    config = load_config()
    capital_actual = config["capital"] + state["resultado"]
    notificar(f"""
📈 *RESUMEN SEMANAL — {ahora.strftime('%d/%m/%Y')}*

✅ Ganadas: {len(wins)} (+${round(gan,4)} USDT)
❌ Perdidas: {len(losses)} (${round(per,4)} USDT)
🏁 Total operaciones: {len(ops)}
🎯 Win Rate: {wr}
📈 Neto: {'+'if neto>=0 else ''}${neto} USDT
💵 Capital actual: ${round(capital_actual,2)} USDT
""")
