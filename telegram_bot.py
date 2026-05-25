"""
Telegram Bot — BTC DCA Bot
"""
import os
import telebot
from state import load_state, save_state, load_config, save_config, resumen
from trader import get_btc_price, estado_posicion

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN_DCA", "")
CHAT_ID        = os.environ.get("TELEGRAM_CHAT_ID_DCA", "")

bot = telebot.TeleBot(TELEGRAM_TOKEN)


def notificar(texto):
    try:
        bot.send_message(CHAT_ID, texto, parse_mode="Markdown")
    except Exception as e:
        print(f"[TELEGRAM] {e}")


def registrar_comandos():

    @bot.message_handler(commands=["start", "ayuda"])
    def cmd_start(msg):
        bot.reply_to(msg, """
₿ *BTC DCA Bot — Activo*

/estado — Capital y márgenes
/posicion — Posición activa detallada
/stats — Estadísticas generales
/config — Ver configuración
/capital [monto] — Cambiar capital
/entrada [monto] — Cambiar entrada por compra
/tp [pct] — Cambiar TP %
/recompra [pct] — Cambiar % de recompra
/ayuda — Este menú
""", parse_mode="Markdown")

    @bot.message_handler(commands=["estado"])
    def cmd_estado(msg):
        state = load_state()
        r = resumen(state)
        precio = get_btc_price() or 0

        bot.reply_to(msg, f"""
₿ *ESTADO BTC DCA*

💰 BTC precio actual: `${precio:,.0f}`

💼 Capital libre: ${r['capital_libre']} USDT
📊 En posición: ${r['en_posicion']} USDT
💵 Capital total: ${r['capital_total']} USDT
📈 Resultado acumulado: {'+'if r['resultado_total']>=0 else ''}${r['resultado_total']} USDT

🔄 Recompras posibles: {r['recompras_posibles']} (${r['entrada_por_compra']} c/u)
{'📋 Posición activa: Sí — DCA nivel '+str(r['niveles_dca']) if r['en_posicion_activa'] else '📋 Sin posición activa'}
""", parse_mode="Markdown")

    @bot.message_handler(commands=["posicion"])
    def cmd_posicion(msg):
        state = load_state()
        config = load_config()
        pos = estado_posicion(state)

        if not pos:
            bot.reply_to(msg, "📋 No hay posición activa en este momento.")
            return

        bot.reply_to(msg, f"""
₿ *POSICIÓN ACTIVA BTC*

💰 Precio actual: `${pos['precio_actual']:,.0f}`
📥 Entrada inicial: `${pos['precio_entrada1']:,.0f}`
📊 Promedio: `${pos['promedio']:,.0f}`
🎯 TP objetivo: `${pos['tp']:,.0f}`
📈 Falta para TP: +{pos['pct_al_tp']}%

📉 Caída desde entrada: -{pos['caida_pct']}%
🔄 Recompras hechas: {pos['niveles']}
💵 Capital en posición: ${pos['total_usdt']} USDT
📊 PnL actual: {'+'if pos['pnl_actual']>=0 else ''}${pos['pnl_actual']} USDT
""", parse_mode="Markdown")

    @bot.message_handler(commands=["stats"])
    def cmd_stats(msg):
        state = load_state()
        r = resumen(state)
        bot.reply_to(msg, f"""
📊 *ESTADÍSTICAS*

🏁 Operaciones cerradas: {r['total_ops']}
✅ Ganadas: {r['total_wins']}
🎯 Win Rate: {r['win_rate']}%
💵 Ganancia total: +${r['ganancia_total']} USDT
📈 Capital total: ${r['capital_total']} USDT
""", parse_mode="Markdown")

    @bot.message_handler(commands=["config"])
    def cmd_config(msg):
        config = load_config()
        state = load_state()
        r = resumen(state)
        bot.reply_to(msg, f"""
⚙️ *CONFIGURACIÓN*

💰 Capital: ${config['capital']} USDT
⚡ Entrada por compra: ${config['entrada_por_compra']} USDT
🔄 Recompra cada: {config['recompra_pct']}%
🎯 TP sobre promedio: {config['tp_pct']}%
🏷️ Comisión: {config['comision']}%
🔄 Recompras posibles ahora: {r['recompras_posibles']}

/capital [monto] · /entrada [monto]
/tp [pct] · /recompra [pct]
""", parse_mode="Markdown")

    @bot.message_handler(commands=["capital"])
    def cmd_capital(msg):
        try:
            nuevo = float(msg.text.split()[1])
            if nuevo < 20:
                bot.reply_to(msg, "❌ Mínimo $20 USDT")
                return
            config = load_config()
            config["capital"] = nuevo
            save_config(config)
            state = load_state()
            state["capital_libre"] = nuevo
            save_state(state)
            bot.reply_to(msg, f"✅ Capital: *${nuevo} USDT*", parse_mode="Markdown")
        except:
            bot.reply_to(msg, "❌ Uso: /capital 500")

    @bot.message_handler(commands=["entrada"])
    def cmd_entrada(msg):
        try:
            nuevo = float(msg.text.split()[1])
            if nuevo < 5:
                bot.reply_to(msg, "❌ Mínimo $5 USDT")
                return
            config = load_config()
            config["entrada_por_compra"] = nuevo
            save_config(config)
            bot.reply_to(msg, f"✅ Entrada por compra: *${nuevo} USDT*", parse_mode="Markdown")
        except:
            bot.reply_to(msg, "❌ Uso: /entrada 20")

    @bot.message_handler(commands=["tp"])
    def cmd_tp(msg):
        try:
            nuevo = float(msg.text.split()[1])
            if nuevo < 1 or nuevo > 20:
                bot.reply_to(msg, "❌ TP entre 1% y 20%")
                return
            config = load_config()
            config["tp_pct"] = nuevo
            save_config(config)
            bot.reply_to(msg, f"✅ TP: *{nuevo}% sobre promedio*", parse_mode="Markdown")
        except:
            bot.reply_to(msg, "❌ Uso: /tp 4")

    @bot.message_handler(commands=["recompra"])
    def cmd_recompra(msg):
        try:
            nuevo = float(msg.text.split()[1])
            if nuevo < 1 or nuevo > 10:
                bot.reply_to(msg, "❌ Recompra entre 1% y 10%")
                return
            config = load_config()
            config["recompra_pct"] = nuevo
            save_config(config)
            bot.reply_to(msg, f"✅ Recompra cada: *{nuevo}% de caída*", parse_mode="Markdown")
        except:
            bot.reply_to(msg, "❌ Uso: /recompra 3")

    return bot
