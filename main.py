"""
Main — BTC DCA Bot
Monitorea BTC cada 5 minutos y gestiona el DCA
"""
import logging
import os
import time
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

from state import load_state
from trader import verificar_posicion
from telegram_bot import notificar, registrar_comandos

logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

INTERVALO = 5 * 60  # verificar cada 5 minutos


class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"BTC DCA Bot - OK")
    def log_message(self, format, *args):
        pass


def iniciar_servidor():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    log.info(f"[SERVER] Puerto {port}")
    server.serve_forever()


def worker():
    time.sleep(3)
    log.info("BTC DCA Bot iniciado")
    notificar("₿ *BTC DCA Bot iniciado*\nMonitoreando Bitcoin 24/7...")

    while True:
        try:
            verificar_posicion(notificar)
            time.sleep(INTERVALO)
        except Exception as e:
            log.error(f"[ERROR] {e}")
            time.sleep(60)


def main():
    # Servidor web para Render
    t_server = threading.Thread(target=iniciar_servidor, daemon=True)
    t_server.start()

    # Worker del bot
    t_worker = threading.Thread(target=worker, daemon=True)
    t_worker.start()

    # Telegram polling
    bot = registrar_comandos()
    log.info("[TELEGRAM] Escuchando comandos...")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)


if __name__ == "__main__":
    main()
