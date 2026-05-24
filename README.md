# 🛰️ Radar Crypto PRO — Bot de Trading

Bot de paper trading para Binance Spot con notificaciones por Telegram.
Corre 24/7 en Railway de forma gratuita.

---

## 📁 Archivos

```
radar_bot/
├── main.py          # Loop principal
├── scanner.py       # Escaneo de pares con indicadores
├── trader.py        # Gestión de operaciones (paper trading)
├── btc_monitor.py   # Monitor BTC / EMA50
├── horario.py       # Control de horario operativo
├── indicators.py    # Cálculo de indicadores técnicos
├── binance_api.py   # Consultas a Binance (solo lectura)
├── telegram_bot.py  # Comandos de Telegram
├── state.py         # Estado y estadísticas
├── config.json      # Configuración editable
└── requirements.txt # Dependencias
```

---

## 🚀 Instalación en Railway

### 1. Crear bot de Telegram
1. Abrí Telegram y buscá **@BotFather**
2. Escribí `/newbot`
3. Seguí los pasos y guardá el **TOKEN**
4. Escribí `/start` a tu bot para activarlo
5. Para obtener tu **CHAT_ID**: buscá @userinfobot y escribile `/start`

### 2. Subir a GitHub
1. Creá un repositorio nuevo en GitHub (ej: `radar-crypto-pro`)
2. Subí todos los archivos de esta carpeta
3. Asegurate que `config.json` y `state.json` estén en el repo

### 3. Configurar Railway
1. Entrá a [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub repo**
3. Seleccioná tu repositorio
4. En **Variables** agregá:
   - `TELEGRAM_TOKEN` = el token que te dio BotFather
   - `TELEGRAM_CHAT_ID` = tu chat ID
5. En **Settings** → **Start Command**: `python main.py`
6. Deploy!

---

## ⚙️ Configuración

Editá `config.json` directamente en GitHub o usá los comandos de Telegram:

```json
{
  "capital": 200,
  "importe_por_operacion": 10,
  "comision": 0.2,
  "enfriamiento_horas": 24,
  "max_horas_sin_entrada": 8
}
```

---

## 📱 Comandos de Telegram

| Comando | Descripción |
|---------|-------------|
| `/estado` | Estado del sistema (BTC, horario, capital) |
| `/operaciones` | Operaciones activas con PnL actual |
| `/stats` | Estadísticas generales acumuladas |
| `/resumen` | Resumen del día |
| `/config` | Ver configuración actual |
| `/capital [monto]` | Modificar capital (ej: `/capital 500`) |
| `/operacion [monto]` | Modificar importe por operación |
| `/ayuda` | Ver todos los comandos |

---

## 🛡️ Protecciones activas

- ✅ BTC bajo EMA50 → cierra todo y bloquea
- ✅ Desbloqueo: precio sobre EMA50 + ADX>25 + volumen
- ✅ Horario: Lunes a Jueves 9:00-18:00 hs Argentina
- ✅ Volumen mínimo: 10M USDT diarios
- ✅ Enfriamiento 24h por par tras cierre
- ✅ Señal cancelada si no entra en 8 horas
- ✅ VWAP como filtro adicional en alcistas

---

## 📊 Indicadores

| Indicador | Tipo | Ratio TP/SL |
|-----------|------|-------------|
| RFibonacci | Alcista 4h | 2:1 |
| Breaker Block | Alcista 4h | 3:1 |
| Squeeze Momentum | Lateral 4h | 2:1 |
| Canal Keltner | Lateral 4h | 1.5:1 |

---

## ⚠️ Importante

Este bot opera en **paper trading** (simulado). Los precios son reales
de Binance pero no se ejecutan órdenes reales. Cuando tengas estadística
suficiente podés conectar las API keys de Binance para operar real.
