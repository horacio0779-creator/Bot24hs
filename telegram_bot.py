"""
Telegram Bot — Radar Crypto PRO
"""
import os
import asyncio
from telegram import Bot, Update
from telegram.ext import ContextTypes
from state import load_state, save_state, load_config, save_config, resumen_stats
from horario import esta_habilitado, motivo_bloqueo
from btc_monitor import btc_esta_bloqueado

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID        = os.environ.get("TELEGRAM_CHAT_ID", "")

_bot = None

def get_bot():
    global _bot
    if _bot is None:
        _bot = Bot(token=TELEGRAM_TOKEN)
    return _bot

async def notificar(texto):
    try:
        await get_bot().send_message(chat_id=CHAT_ID, text=texto, parse_mode="Markdown")
    except Exception as e:
        print(f"[TELEGRAM] {e}")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🛰️ *Radar Crypto PRO — Activo*

/estado — Estado del sistema
/operaciones — Operaciones activas
/stats — Estadísticas
/resumen — Resumen del día
/config — Configuración
/capital [monto] — Modificar capital
/operacion [monto] — Modificar importe
/ayuda — Todos los comandos
""", parse_mode="Markdown")

async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    config = load_config()
    btc_bloq = btc_esta_bloqueado(state)
    hor_ok = esta_habilitado()
    activas = [o for o in state["operaciones"] if o["estado"] == "activa"]
    capital_actual = config["capital"] + state["resultado"]
    await update.message.reply_text(f"""
📡 *ESTADO DEL SISTEMA*

{'🔴 BTC BLOQUEADO' if btc_bloq else '🟢 BTC OK'}
{'🟢 Horario habilitado' if hor_ok else '🔴 '+motivo_bloqueo()}

💰 Capital inicial: ${config['capital']} USDT
📈 Resultado: {'+'if state['resultado']>=0 else ''}${round(state['resultado'],2)} USDT
💵 Capital actual: ${round(capital_actual,2)} USDT
📋 Operaciones activas: {len(activas)}
⚡ Por operación: ${config['importe_por_operacion']} USDT
""", parse_mode="Markdown")

async def cmd_operaciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    activas = [o for o in state["operaciones"] if o["estado"] == "activa"]
    if not activas:
        await update.message.reply_text("📋 No hay operaciones activas.")
        return
    texto = "📋 *OPERACIONES ACTIVAS*\n\n"
    for op in activas:
        tp1_txt = "✅" if op["tp1_alcanzado"] else "⏳"
        texto += f"*{op['symbol']}* · {op['indicador']}\n💰 Entrada: `${op['entrada']}` · TP1: {tp1_txt}\n🚀 TP: `${op['tp']}` · 🛑 SL: `${op['sl']}`\n\n"
    await update.message.reply_text(texto, parse_mode="Markdown")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    s = resumen_stats(state)
    await update.message.reply_text(f"""
📊 *ESTADÍSTICAS*

💰 Capital inicial: ${s['capital_inicial']} USDT
💵 Capital actual: ${s['capital_actual']} USDT
📈 Resultado: {'+'if s['resultado']>=0 else ''}${s['resultado']} USDT

✅ Ganadas: {s['wins']} (+${s['ganancia_total']} USDT)
❌ Perdidas: {s['losses']} (-${s['perdida_total']} USDT)
🎯 Win Rate: {s['win_rate']}
""", parse_mode="Markdown")

async def cmd_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import datetime, timezone
    state = load_state()
    ahora = datetime.now(timezone.utc)
    inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    ops = [o for o in state["operaciones"]
           if o.get("ts_cierre") and
           datetime.fromisoformat(o["ts_cierre"]) >= inicio]
    wins   = [o for o in ops if o["estado"] == "tp"]
    losses = [o for o in ops if o["estado"] == "sl"]
    gan    = sum(o.get("resultado", 0) for o in wins)
    per    = sum(o.get("resultado", 0) for o in losses)
    neto   = round(gan + per, 4)
    wr     = f"{len(wins)/(len(wins)+len(losses))*100:.1f}%" if ops else "—"
    await update.message.reply_text(f"""
📊 *RESUMEN HOY*

✅ Ganadas: {len(wins)} (+${round(gan,4)} USDT)
❌ Perdidas: {len(losses)} (${round(per,4)} USDT)
🎯 Win Rate: {wr}
📈 Neto: {'+'if neto>=0 else ''}${neto} USDT
""", parse_mode="Markdown")

async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    await update.message.reply_text(f"""
⚙️ *CONFIGURACIÓN*

💰 Capital: ${config['capital']} USDT
⚡ Por operación: ${config['importe_por_operacion']} USDT
🏷️ Comisión: {config['comision']}%
❄️ Enfriamiento: {config['enfriamiento_horas']}h
⏰ Tiempo máx sin entrada: {config['max_horas_sin_entrada']}h

/capital [monto] — ej: /capital 500
/operacion [monto] — ej: /operacion 25
""", parse_mode="Markdown")

async def cmd_capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nuevo = float(context.args[0])
        if nuevo < 10:
            await update.message.reply_text("❌ Mínimo $10 USDT")
            return
        config = load_config()
        config["capital"] = nuevo
        save_config(config)
        state = load_state()
        state["capital"] = nuevo
        save_state(state)
        await update.message.reply_text(f"✅ Capital: *${nuevo} USDT*", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ Uso: /capital 500")

async def cmd_operacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nuevo = float(context.args[0])
        if nuevo < 5:
            await update.message.reply_text("❌ Mínimo $5 USDT")
            return
        config = load_config()
        config["importe_por_operacion"] = nuevo
        save_config(config)
        await update.message.reply_text(f"✅ Por operación: *${nuevo} USDT*", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ Uso: /operacion 25")

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
📖 *COMANDOS*

/estado — Estado del sistema
/operaciones — Ver activas
/stats — Estadísticas generales
/resumen — Resumen del día
/config — Ver configuración
/capital [monto] — Modificar capital
/operacion [monto] — Modificar importe
/ayuda — Este menú
""", parse_mode="Markdown")
