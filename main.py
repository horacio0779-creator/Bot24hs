"""
Main — Radar Crypto PRO
"""
import asyncio
import logging
import os
import time
import threading
from datetime import datetime, timezone, timedelta
from telegram.ext import Application, CommandHandler

from state import load_state, load_config
from btc_monitor import verificar_btc, btc_esta_bloqueado
from horario import esta_habilitado
from scanner import escanear_todos
from trader import abrir_operacion, verificar_operaciones, verificar_tiempo_sin_entrada
from telegram_bot import (
    notificar, cmd_start, cmd_estado, cmd_operaciones,
    cmd_stats, cmd_resumen, cmd_config, cmd_capital,
    cmd_operacion, cmd_ayuda
)

logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

INTERVALO_PRECIOS  = 30
INTERVALO_ESCANEO  = 4 * 3600
INTERVALO_BTC      = 5 * 60
INTERVALO_CANCELAR = 30 * 60

ultimo_escaneo  = 0
ultimo_btc      = 0
ultimo_cancelar = 0
ultimo_resumen  = ""

loop = None


def notificar_sync(msg):
    if loop:
        asyncio.run_coroutine_threadsafe(notificar(msg), loop)


def worker():
    global ultimo_escaneo, ultimo_btc, ultimo_cancelar, ultimo_resumen

    # Esperar que el loop esté listo
    time.sleep(5)
    notificar_sync("🛰️ *Radar Crypto PRO iniciado*\nMonitoreando el mercado 24/7...")

    while True:
        try:
            ahora = time.time()
            state = load_state()

            if ahora - ultimo_btc >= INTERVALO_BTC:
                verificar_btc(state, notificar_sync)
                ultimo_btc = ahora

            verificar_operaciones(state, notificar_sync)

            if ahora - ultimo_cancelar >= INTERVALO_CANCELAR:
                verificar_tiempo_sin_entrada(state, notificar_sync)
                ultimo_cancelar = ahora

            if ahora - ultimo_escaneo >= INTERVALO_ESCANEO:
                if btc_esta_bloqueado(state):
                    log.info("[SCAN] Bloqueado por BTC")
                elif not esta_habilitado():
                    log.info("[SCAN] Bloqueado por horario")
                else:
                    log.info("[SCAN] Iniciando escaneo...")
                    notificar_sync("🔍 *Iniciando escaneo...*")
                    señales = escanear_todos(state)
                    if señales:
                        for s in señales:
                            state = load_state()
                            abrir_operacion(state, s, notificar_sync)
                    else:
                        notificar_sync("🔍 Sin señales en este ciclo")
                ultimo_escaneo = ahora

            ahora_arg = datetime.now(timezone.utc) - timedelta(hours=3)
            clave = ahora_arg.strftime("%Y-%m-%d")
            if ahora_arg.hour == 18 and ahora_arg.minute < 5 and ultimo_resumen != clave:
                ultimo_resumen = clave
                enviar_resumen_sync(state)

            time.sleep(INTERVALO_PRECIOS)

        except Exception as e:
            log.error(f"[ERROR] {e}")
            time.sleep(60)


def enviar_resumen_sync(state):
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
    notificar_sync(f"""
📊 *RESUMEN DIARIO — {ahora.strftime('%d/%m/%Y')}*

✅ Ganadas: {len(wins)} (+${round(gan,4)} USDT)
❌ Perdidas: {len(losses)} (${round(per,4)} USDT)
🎯 Win Rate: {wr}
📈 Neto: {'+'if neto>=0 else ''}${neto} USDT
💵 Capital: ${round(capital_actual,2)} USDT
""")


def main():
    global loop

    # Iniciar worker en hilo separado
    t = threading.Thread(target=worker, daemon=True)
    t.start()

    # Crear app de Telegram
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("estado",      cmd_estado))
    app.add_handler(CommandHandler("operaciones", cmd_operaciones))
    app.add_handler(CommandHandler("stats",       cmd_stats))
    app.add_handler(CommandHandler("resumen",     cmd_resumen))
    app.add_handler(CommandHandler("config",      cmd_config))
    app.add_handler(CommandHandler("capital",     cmd_capital))
    app.add_handler(CommandHandler("operacion",   cmd_operacion))
    app.add_handler(CommandHandler("ayuda",       cmd_ayuda))

    log.info("[TELEGRAM] Bot iniciado")
    loop = asyncio.get_event_loop()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
