"""
Telegram Bot — Radar Crypto PRO
Notificaciones y comandos
"""
import os
import asyncio
import logging
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from state import load_state, save_state, load_config, save_config, resumen_stats
from horario import esta_habilitado, motivo_bloqueo
from btc_monitor import btc_esta_bloqueado

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID        = os.environ.get("TELEGRAM_CHAT_ID", "")


def get_bot():
    return Bot(token=TELEGRAM_TOKEN)


async def enviar_mensaje(texto):
    """Envía un mensaje al chat del usuario"""
    try:
        bot = get_bot()
        await bot.send_message(
            chat_id=CHAT_ID,
            text=texto,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")


def notificar(texto):
    """Wrapper sincrónico para enviar mensajes"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(enviar_mensaje(texto))
        else:
            loop.run_until_complete(enviar_mensaje(texto))
    except Exception as e:
        print(f"[NOTIFICAR ERROR] {e}")


# ── COMANDOS ──

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🛰️ *Radar Crypto PRO — Activo*

Comandos disponibles:
/estado — Estado actual del sistema
/operaciones — Operaciones activas
/stats — Estadísticas generales
/resumen — Resumen del día
/config — Ver configuración actual
/capital [monto] — Modificar capital
/operacion [monto] — Modificar importe por operación
/ayuda — Ver todos los comandos
""", parse_mode="Markdown")


async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    config = load_config()
    btc_bloq = btc_esta_bloqueado(state)
    hor_ok = esta_habilitado()

    estado_btc = "🔴 BTC BLOQUEADO" if btc_bloq else "🟢 BTC OK"
    estado_hor = "🟢 Horario habilitado" if hor_ok else f"🔴 {motivo_bloqueo()}"

    activas = [op for op in state["operaciones"] if op["estado"] == "activa"]
    capital_actual = config["capital"] + state["resultado"]

    await update.message.reply_text(f"""
📡 *ESTADO DEL SISTEMA*

{estado_btc}
{estado_hor}

💰 Capital: ${config['capital']} USDT
📊 Resultado: {'+'if state['resultado']>=0 else ''}${round(state['resultado'],2)} USDT
💵 Capital actual: ${round(capital_actual,2)} USDT
📋 Operaciones activas: {len(activas)}
⚡ Importe por operación: ${config['importe_por_operacion']} USDT
""", parse_mode="Markdown")


async def cmd_operaciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    activas = [op for op in state["operaciones"] if op["estado"] == "activa"]

    if not activas:
        await update.message.reply_text("📋 No hay operaciones activas en este momento.")
        return

    texto = "📋 *OPERACIONES ACTIVAS*\n\n"
    for op in activas:
        from binance_api import get_price
        precio_actual = get_price(op["symbol"]) or op["entrada"]
        pe = op["entrada"]
        pnl_actual = ((precio_actual - pe) / pe) * op["usdt"]
        tp1_txt = "✅" if op["tp1_alcanzado"] else "⏳"

        texto += f"""
*{op['symbol']}* · {op['indicador']}
💰 Entrada: `${pe}` → Actual: `${precio_actual:.4f}`
📊 PnL: {'+'if pnl_actual>=0 else ''}${round(pnl_actual,4)} USDT
🎯 TP1: {tp1_txt} · 🚀 TP: `${op['tp']}` · 🛑 SL: `${op['sl']}`
"""
    await update.message.reply_text(texto, parse_mode="Markdown")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    s = resumen_stats(state)

    await update.message.reply_text(f"""
📊 *ESTADÍSTICAS GENERALES*

💰 Capital inicial: ${s['capital_inicial']} USDT
💵 Capital actual: ${s['capital_actual']} USDT
📈 Resultado neto: {'+'if s['resultado']>=0 else ''}${s['resultado']} USDT

✅ Ganadas: {s['wins']} (+${s['ganancia_total']} USDT)
❌ Perdidas: {s['losses']} (-${s['perdida_total']} USDT)
🏁 Total: {s['total']}
🎯 Win Rate: {s['win_rate']}
""", parse_mode="Markdown")


async def cmd_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resumen del día"""
    from datetime import datetime, timezone, timedelta
    state = load_state()
    ahora = datetime.now(timezone.utc)
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    ops_hoy = [
        op for op in state["operaciones"]
        if op.get("ts_cierre") and
        datetime.fromisoformat(op["ts_cierre"]) >= inicio_dia
    ]

    wins_hoy   = [op for op in ops_hoy if op["estado"] == "tp"]
    losses_hoy = [op for op in ops_hoy if op["estado"] == "sl"]
    gan_hoy    = sum(op.get("resultado", 0) for op in wins_hoy)
    per_hoy    = sum(op.get("resultado", 0) for op in losses_hoy)
    neto_hoy   = round(gan_hoy + per_hoy, 4)

    wr_hoy = f"{len(wins_hoy)/(len(wins_hoy)+len(losses_hoy))*100:.1f}%" if ops_hoy else "—"

    await update.message.reply_text(f"""
📊 *RESUMEN DEL DÍA*
{ahora.strftime('%d/%m/%Y')} (UTC)

✅ Operaciones ganadoras: {len(wins_hoy)} (+${round(gan_hoy,4)} USDT)
❌ Operaciones perdedoras: {len(losses_hoy)} (${round(per_hoy,4)} USDT)
🏁 Total cerradas: {len(ops_hoy)}
🎯 Win Rate hoy: {wr_hoy}
📈 Resultado neto: {'+'if neto_hoy>=0 else ''}${neto_hoy} USDT
""", parse_mode="Markdown")


async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    await update.message.reply_text(f"""
⚙️ *CONFIGURACIÓN ACTUAL*

💰 Capital: ${config['capital']} USDT
⚡ Importe por operación: ${config['importe_por_operacion']} USDT
🏷️ Comisión: {config['comision']}%
❄️ Enfriamiento: {config['enfriamiento_horas']}h
⏰ Tiempo máximo sin entrada: {config['max_horas_sin_entrada']}h

Para modificar:
/capital [monto] — ej: /capital 500
/operacion [monto] — ej: /operacion 25
""", parse_mode="Markdown")


async def cmd_capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nuevo = float(context.args[0])
        if nuevo < 10:
            await update.message.reply_text("❌ El capital mínimo es $10 USDT")
            return
        config = load_config()
        config["capital"] = nuevo
        save_config(config)
        state = load_state()
        state["capital"] = nuevo
        save_state(state)
        await update.message.reply_text(f"✅ Capital actualizado: *${nuevo} USDT*", parse_mode="Markdown")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Uso: /capital [monto] — ej: /capital 500")


async def cmd_operacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nuevo = float(context.args[0])
        if nuevo < 5:
            await update.message.reply_text("❌ El mínimo por operación es $5 USDT")
            return
        config = load_config()
        config["importe_por_operacion"] = nuevo
        save_config(config)
        await update.message.reply_text(f"✅ Importe por operación: *${nuevo} USDT*", parse_mode="Markdown")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Uso: /operacion [monto] — ej: /operacion 25")


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
📖 *COMANDOS DISPONIBLES*

/estado — Estado del sistema (BTC, horario, capital)
/operaciones — Ver operaciones activas con PnL actual
/stats — Estadísticas generales acumuladas
/resumen — Resumen del día de hoy
/config — Ver configuración actual
/capital [monto] — Modificar capital total
/operacion [monto] — Modificar importe por operación
/ayuda — Este menú
""", parse_mode="Markdown")


def crear_app():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("estado",     cmd_estado))
    app.add_handler(CommandHandler("operaciones",cmd_operaciones))
    app.add_handler(CommandHandler("stats",      cmd_stats))
    app.add_handler(CommandHandler("resumen",    cmd_resumen))
    app.add_handler(CommandHandler("config",     cmd_config))
    app.add_handler(CommandHandler("capital",    cmd_capital))
    app.add_handler(CommandHandler("operacion",  cmd_operacion))
    app.add_handler(CommandHandler("ayuda",      cmd_ayuda))
    return app
