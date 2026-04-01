import os
import socket
import logging
from datetime import datetime

import pandas as pd
from ping3 import ping
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
EXCEL_PATH = os.getenv("EXCEL_PATH", "/data/red.xlsx")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Utilidades de red
# ─────────────────────────────────────────────

def check_ping(host: str, timeout: float = 2.0) -> bool:
    if not host or str(host).strip().lower() in ("nan", ""):
        return False
    try:
        result = ping(str(host).strip(), timeout=timeout, unit="s")
        return result is not None and result is not False
    except Exception:
        return False


def check_port(host: str, port: int, timeout: float = 3.0) -> bool:
    if not host or str(host).strip().lower() in ("nan", ""):
        return False
    try:
        with socket.create_connection((str(host).strip(), port), timeout=timeout):
            return True
    except Exception:
        return False


# ─────────────────────────────────────────────
#  Lógica de monitoreo
# ─────────────────────────────────────────────

def monitorear_red() -> str:
    try:
        df = pd.read_excel(EXCEL_PATH, dtype=str)
    except Exception as e:
        return f"❌ *Error al leer el archivo Excel:*\n`{e}`"

    df.columns = [c.strip() for c in df.columns]

    columnas_requeridas = [
        "Sistema", "ROUTER", "IPMI",
        "SERVIDOR (UIP)", "PROXMOX",
        "Puesto 1", "Puesto 2", "Puesto 3 (Director)"
    ]
    for col in columnas_requeridas:
        if col not in df.columns:
            return f"❌ *Columna faltante en el Excel:* `{col}`"

    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    lineas = [
        "🖥️ *MONITOREO DE RED*",
        f"🕐 `{ahora}`",
        "─" * 32,
    ]

    for _, row in df.iterrows():
        sistema = str(row.get("Sistema", "Sin nombre")).strip()
        if sistema.lower() == "nan":
            sistema = "Sin nombre"

        router_ip = str(row.get("ROUTER", "")).strip()
        lineas.append(f"\n📍 *{sistema}*")

        router_ok = check_ping(router_ip)
        if not router_ok:
            lineas.append(f"  🔴 *TOTALMENTE CAÍDO* (Router `{router_ip}` sin respuesta)")
            lineas.append("─" * 32)
            continue

        lineas.append(f"  🌐 Router: ✅ `{router_ip}`")

        uip_ip = str(row.get("SERVIDOR (UIP)", "")).strip()
        if uip_ip and uip_ip.lower() != "nan":
            uip_ok = check_port(uip_ip, 80)
            lineas.append(f"  🖥️  Servidor UIP: {'✅' if uip_ok else '❌'} `{uip_ip}:80`")
        else:
            lineas.append("  🖥️  Servidor UIP: ⚠️ No configurado")

        proxmox_ip = str(row.get("PROXMOX", "")).strip()
        if proxmox_ip and proxmox_ip.lower() != "nan":
            prox_ok = check_port(proxmox_ip, 8006)
            lineas.append(f"  📦 Proxmox: {'✅' if prox_ok else '❌'} `{proxmox_ip}:8006`")
        else:
            lineas.append("  📦 Proxmox: ⚠️ No configurado")

        puestos = {
            "Puesto 1": str(row.get("Puesto 1", "")).strip(),
            "Puesto 2": str(row.get("Puesto 2", "")).strip(),
            "Puesto 3": str(row.get("Puesto 3 (Director)", "")).strip(),
        }

        activos, total, detalles = 0, 0, []
        for nombre, ip in puestos.items():
            if ip and ip.lower() != "nan":
                total += 1
                ok = check_ping(ip)
                if ok:
                    activos += 1
                detalles.append(f"`{ip}` {'✅' if ok else '❌'}")

        if total > 0:
            icono = "✅" if activos == total else ("❌" if activos == 0 else "⚠️")
            lineas.append(f"  💻 Puestos: {icono} {activos}/{total} activos")
            lineas.append(f"     {' | '.join(detalles)}")
        else:
            lineas.append("  💻 Puestos: ⚠️ No configurados")

        ipmi_ip = str(row.get("IPMI", "")).strip()
        if ipmi_ip and ipmi_ip.lower() != "nan":
            ipmi_ok = check_ping(ipmi_ip)
            lineas.append(f"  🔧 IPMI: {'✅' if ipmi_ok else '❌'} `{ipmi_ip}`")

        lineas.append("─" * 32)

    lineas.append("\n_Próximo chequeo en 12 hs_")
    return "\n".join(lineas)


# ─────────────────────────────────────────────
#  Tarea programada (job_queue de PTB)
# ─────────────────────────────────────────────

async def tarea_monitoreo(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Ejecutando monitoreo automático...")
    mensaje = monitorear_red()
    for i in range(0, len(mensaje), 4000):
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=mensaje[i:i + 4000],
            parse_mode="Markdown"
        )
    logger.info("Informe automático enviado.")


# ─────────────────────────────────────────────
#  Handlers de comandos
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Bot de Monitoreo de Red activo.*\n\n"
        "Comandos disponibles:\n"
        "• `/chequear` — Ejecuta un chequeo inmediato\n"
        "• `/estado` — Muestra el próximo chequeo programado",
        parse_mode="Markdown"
    )


async def cmd_chequear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Iniciando chequeo manual, aguardá un momento...")
    mensaje = monitorear_red()
    for i in range(0, len(mensaje), 4000):
        await update.message.reply_text(mensaje[i:i + 4000], parse_mode="Markdown")


async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = context.job_queue.get_jobs_by_name("monitoreo_red")
    if jobs:
        proximo = jobs[0].next_t
        texto = f"⏰ Próximo chequeo automático:\n`{proximo.strftime('%d/%m/%Y %H:%M:%S')}`"
    else:
        texto = "⚠️ No hay tareas programadas."
    await update.message.reply_text(texto, parse_mode="Markdown")


# ─────────────────────────────────────────────
#  post_init: registrar jobs dentro del event
#  loop de PTB (evita el conflicto de loops)
# ─────────────────────────────────────────────

async def post_init(application: Application):
    # Chequeo inicial 10 segundos después de arrancar
    application.job_queue.run_once(
        tarea_monitoreo, when=10, name="monitoreo_inicial"
    )
    # Luego cada 12 horas
    application.job_queue.run_repeating(
        tarea_monitoreo,
        interval=43200,
        first=43200,
        name="monitoreo_red"
    )
    logger.info("Jobs registrados: inicio en 10 s, luego cada 12 hs.")


# ─────────────────────────────────────────────
#  Main — sin asyncio.run(), PTB maneja el loop
# ─────────────────────────────────────────────

def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("chequear", cmd_chequear))
    app.add_handler(CommandHandler("estado", cmd_estado))

    logger.info("Bot iniciado. Esperando mensajes...")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
