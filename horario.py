"""
Control de horario — Radar Crypto PRO
Lunes a Jueves 9:00 a 18:00 hs Argentina
"""
from datetime import datetime, timezone, timedelta


def esta_habilitado():
    """Retorna True si estamos en horario operativo"""
    # UTC-3 Argentina
    ahora_utc = datetime.now(timezone.utc)
    ahora_arg = ahora_utc - timedelta(hours=3)
    dia  = ahora_arg.weekday()  # 0=Lunes, 4=Viernes, 5=Sábado, 6=Domingo
    hora = ahora_arg.hour + ahora_arg.minute / 60

    # Viernes, Sábado, Domingo: bloqueado
    if dia >= 4:
        return False

    # Lunes a Jueves: solo entre 9 y 18
    if hora < 9 or hora >= 18:
        return False

    return True


def motivo_bloqueo():
    """Retorna el motivo del bloqueo horario"""
    ahora_utc = datetime.now(timezone.utc)
    ahora_arg = ahora_utc - timedelta(hours=3)
    dia  = ahora_arg.weekday()
    hora = ahora_arg.hour

    dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    nombre_dia = dias[dia]

    if dia >= 4:
        return f"{nombre_dia} — mercado sin institucionales"
    if hora < 9:
        return f"Madrugada — volumen bajo (habilita a las 9:00 hs)"
    if hora >= 18:
        return f"Fuera de horario — después de las 18:00 hs"
    return ""
