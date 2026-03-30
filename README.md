# 🖥️ Bot de Monitoreo de Red — Telegram

Bot dockerizado que monitorea infraestructura de red cada 12 horas y reporta
el estado por Telegram. Soporta chequeo manual con `/chequear`.

---

## 📁 Estructura del proyecto

```
telegram-monitor-bot/
├── bot.py               # Lógica principal del bot
├── requirements.txt     # Dependencias Python
├── Dockerfile
├── docker-compose.yml
├── .env.example         # Plantilla de variables de entorno
├── .gitignore
└── data/
    └── red.xlsx         # Tu archivo Excel con las IPs (NO incluido en git)
```

---

## ⚙️ Configuración inicial

### 1. Clonar y preparar

```bash
git clone <repo>
cd telegram-monitor-bot
cp .env.example .env
mkdir -p data
```

### 2. Editar `.env`

```env
BOT_TOKEN=tu_token_aqui
CHAT_ID=tu_chat_id_aqui
```

**Obtener el Chat ID:**
- Enviá cualquier mensaje a tu bot
- Visitá: `https://api.telegram.org/bot<TOKEN>/getUpdates`
- Buscá el campo `"chat": { "id": ... }`

### 3. Copiar el Excel

Colocá tu archivo Excel en `data/red.xlsx`.

**Columnas requeridas (exactamente con estos nombres):**

| Columna              | Descripción                        |
|----------------------|------------------------------------|
| `Sistema`            | Nombre del lugar/sucursal          |
| `ROUTER`             | IP del router (se hace ping)       |
| `IPMI`               | IP de la placa IPMI (ping)         |
| `SERVIDOR (UIP)`     | IP del servidor UIP (puerto 80)    |
| `PROXMOX`            | IP de Proxmox (puerto 8006)        |
| `Puesto 1`           | IP del puesto 1 (ping)             |
| `Puesto 2`           | IP del puesto 2 (ping)             |
| `Puesto 3 (Director)`| IP del puesto del director (ping)  |

---

## 🚀 Despliegue

```bash
# Construir e iniciar
docker compose up -d --build

# Ver logs en tiempo real
docker compose logs -f

# Detener
docker compose down
```

---

## 💬 Comandos del bot

| Comando      | Descripción                          |
|--------------|--------------------------------------|
| `/start`     | Muestra ayuda y comandos disponibles |
| `/chequear`  | Ejecuta un chequeo manual inmediato  |
| `/estado`    | Muestra la hora del próximo chequeo  |

---

## 🔄 Actualizar el Excel sin reconstruir

El archivo Excel está montado como volumen. Para actualizar IPs:

```bash
# Simplemente reemplazá el archivo en tu máquina:
cp nuevo_red.xlsx data/red.xlsx
# El bot leerá la nueva versión en el próximo chequeo (o con /chequear)
```

---

## 📋 Ejemplo de mensaje de Telegram

```
🖥️ MONITOREO DE RED
🕐 15/07/2025 08:00

────────────────────────────────

📍 Sede Central
  🌐 Router: ✅ 192.168.1.1
  🖥️  Servidor UIP: ✅ 192.168.1.10:80
  📦 Proxmox: ✅ 192.168.1.20:8006
  💻 Puestos: ⚠️ 2/3 activos
     192.168.1.50 ✅ | 192.168.1.51 ✅ | 192.168.1.52 ❌
  🔧 IPMI: ✅ 192.168.1.30

────────────────────────────────

📍 Sucursal Norte
  🔴 TOTALMENTE CAÍDO (Router 10.0.0.1 sin respuesta)

────────────────────────────────

_Próximo chequeo en 12 hs_
```

---

## 🛠️ Notas técnicas

- Usa `network_mode: host` para alcanzar IPs internas de la red
- Las capacidades `NET_ADMIN` y `NET_RAW` son necesarias para `ping3`
- El scheduler ejecuta el chequeo también al iniciar el contenedor
- Los logs rotan automáticamente (máx. 10 MB × 3 archivos)
