"""
Main — Radar Crypto PRO
Loop principal del bot
"""
import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta

from state import load_state, save_state, load_config
from binance_api import get_price
from btc_monitor import verificar_btc, btc_esta_bloqueado
from horario import esta_habilitado, motivo_bloqueo
from scanner import escanear_todos
from trader import (
    abrir_operacion, verificar_operaciones,
    verificar_tiempo_sin_entrada, cerrar_todo_por_btc
)
from telegram_bot import notificar, crear_app

logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# Intervalos en segundos
INTERVALO_PRECIOS   = 30     # verificar TP/SL cada 30s
INTERVALO_ESCANEO   = 4 * 3600  # escanear cada 4h (cierre de vela)
INTERVALO_BTC       = 5 * 60    # verificar BTC cada 5 minutos
INTERVALO_CANCELAR  = 30 * 60   # verificar tiempo sin entrada cada 30min

ultimo_escaneo  = 0
ultimo_btc      = 0
ultimo_cancelar = 0
ultimo_resumen  = ""


async def loop_principal():
    global ultimo_escaneo, ultimo_btc, ultimo_cancelar, ultimo_resumen

    log.info("🛰️ Radar Crypto PRO iniciado")
    notificar("🛰️ *Radar Crypto PRO iniciado*\nMonitoreando el mercado 24/7...")

    while True:
        try:
            ahora = time.time()
            state = load_state()

            # ── Monitor BTC cada 5 minutos ──
            if ahora - ultimo_btc >= INTERVALO_BTC:
                log.info("[BTC] Verificando estado...")
                verificar_btc(state, notificar)
                ultimo_btc = ahora

            # ── Verificar TP/SL cada 30 segundos ──
            verificar_operaciones(state, notificar)

            # ── Verificar tiempo sin entrada cada 30 min ──
            if ahora - ultimo_cancelar >= INTERVALO_CANCELAR:
                verificar_tiempo_sin_entrada(state, notificar)
                ultimo_cancelar = ahora

            # ── Escaneo cada 4 horas si sistema habilitado ──
            if ahora - ultimo_escaneo >= INTERVALO_ESCANEO:
                if btc_esta_bloqueado(state):
                    log.info("[SCAN] Bloqueado por BTC")
                elif not esta_habilitado():
                    log.info(f"[SCAN] Bloqueado por horario: {motivo_bloqueo()}")
                else:
                    log.info("[SCAN] Iniciando escaneo...")
                    notificar("🔍 *Iniciando escaneo de mercado...*")
                    señales = escanear_todos(state)
                    if señales:
                        log.info(f"[SCAN] {len(señales)} señales encontradas")
                        for s in señales:
                            state = load_state()
                            abrir_operacion(state, s, notificar)
                    else:
                        log.info("[SCAN] Sin señales")
                        notificar("🔍 Escaneo completado — Sin señales en este ciclo")
                ultimo_escaneo = ahora

            # ── Resumen diario a las 18hs Argentina ──
            ahora_arg = datetime.now(timezone.utc) - timedelta(hours=3)
            clave_resumen = ahora_arg.strftime("%Y-%m-%d")
            if ahora_arg.hour == 18 and ahora_arg.minute < 5 and ultimo_resumen != clave_resumen:
                ultimo_resumen = clave_resumen
                await enviar_resumen_diario(state)

            await asyncio.sleep(INTERVALO_PRECIOS)

        except Exception as e:
            log.error(f"[ERROR] Loop principal: {e}")
            await asyncio.sleep(60)


async def enviar_resumen_diario(state):
    from datetime import datetime, timezone, timedelta
    ahora = datetime.now(timezone.utc)
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    ops_hoy = [
        op for op in state["operaciones"]
        if op.get("ts_cierre") and
        datetime.fromisoformat(op["ts_cierre"]) >= inicio_dia
    ]

    wins   = [op for op in ops_hoy if op["estado"] == "tp"]
    losses = [op for op in ops_hoy if op["estado"] == "sl"]
    gan    = sum(op.get("resultado", 0) for op in wins)
    per    = sum(op.get("resultado", 0) for op in losses)
    neto   = round(gan + per, 4)
    wr     = f"{len(wins)/(len(wins)+len(losses))*100:.1f}%" if ops_hoy else "—"

    config = load_config()
    capital_actual = config["capital"] + state["resultado"]

    notificar(f"""
📊 *RESUMEN DIARIO — {ahora.strftime('%d/%m/%Y')}*

✅ Ganadas: {len(wins)} (+${round(gan,4)} USDT)
❌ Perdidas: {len(losses)} (${round(per,4)} USDT)
🏁 Total operaciones: {len(ops_hoy)}
🎯 Win Rate hoy: {wr}
📈 Resultado neto: {'+'if neto>=0 else ''}${neto} USDT
💵 Capital actual: ${round(capital_actual,2)} USDT

Hasta mañana, el sistema sigue monitoreando. 💪
""")


async def main():
    # Iniciar Telegram bot y loop principal en paralelo
    app = crear_app()
    async with app:
        await app.start()
        await app.updater.start_polling()
        log.info("[TELEGRAM] Bot iniciado, escuchando comandos...")
        await loop_principal()
        await app.updater.stop()
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
