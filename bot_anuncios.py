import json
import os
import threading
import time
from datetime import datetime

import telebot

# =========================
# CONFIGURACIÓN PRINCIPAL
# =========================
TOKEN = "8789719959:AAGaWhOQQkyGa9dYxIfxX6Qw_IAHkvcO3oM"
ADMIN_ID = 6273485735
DATA_FILE = "anuncios_data.json"

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

# =========================
# ESTADO GLOBAL
# =========================
waiting_state = {}
loop_thread = None
loop_running = False


def cargar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "group_id": None,
        "interval_seconds": 7200,   # 2 horas por defecto
        "messages": [],
        "enabled": False,
        "current_index": 0,
        "last_sent_at": None
    }


def guardar_datos():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = cargar_datos()


# =========================
# UTILIDADES
# =========================
def es_admin(user_id):
    return user_id == ADMIN_ID


def formatear_intervalo(segundos):
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60

    if horas > 0 and minutos > 0:
        return f"{horas}h {minutos}m"
    if horas > 0:
        return f"{horas}h"
    return f"{minutos}m"


def ahora_texto():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def enviar_siguiente_mensaje():
    if not data["group_id"]:
        print("No hay group_id configurado.")
        return

    if not data["messages"]:
        print("No hay mensajes configurados.")
        return

    idx = data["current_index"]
    mensaje = data["messages"][idx]

    try:
        bot.send_message(data["group_id"], mensaje, disable_web_page_preview=True)
        data["last_sent_at"] = ahora_texto()
        data["current_index"] = (idx + 1) % len(data["messages"])
        guardar_datos()
        print(f"Mensaje enviado correctamente a las {data['last_sent_at']}")
    except Exception as e:
        print("Error enviando mensaje automático:", e)


def loop_anuncios():
    global loop_running

    while loop_running:
        try:
            if data["enabled"]:
                enviar_siguiente_mensaje()
            else:
                print("El sistema está desactivado.")
        except Exception as e:
            print("Error en loop de anuncios:", e)

        intervalo = max(60, int(data["interval_seconds"]))
        for _ in range(intervalo):
            if not loop_running:
                break
            time.sleep(1)


def iniciar_loop_si_hace_falta():
    global loop_thread, loop_running

    if loop_running:
        return

    loop_running = True
    loop_thread = threading.Thread(target=loop_anuncios, daemon=True)
    loop_thread.start()
    print("Loop de anuncios iniciado.")


def detener_loop():
    global loop_running
    loop_running = False
    print("Loop de anuncios detenido.")


# =========================
# COMANDOS
# =========================
@bot.message_handler(commands=["start"])
def start(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "❌ No autorizado.")
        return

    texto = (
        "📢 *Parzival Anuncios Bot*\n\n"
        "Este bot sirve para enviar mensajes automáticos al grupo.\n\n"
        "*Comandos disponibles:*\n"
        "/help - Ver ayuda\n"
        "/setgroup - Guardar este grupo como destino\n"
        "/group - Ver grupo actual\n"
        "/setinterval - Cambiar intervalo\n"
        "/addmsg - Añadir mensaje\n"
        "/listmsgs - Ver mensajes\n"
        "/delmsg - Eliminar mensaje por número\n"
        "/sendnow - Enviar un mensaje ahora\n"
        "/startads - Activar anuncios automáticos\n"
        "/stopads - Desactivar anuncios automáticos\n"
        "/status - Ver estado actual\n"
    )

    bot.send_message(message.chat.id, texto, parse_mode="Markdown")


@bot.message_handler(commands=["help"])
def help_cmd(message):
    if not es_admin(message.from_user.id):
        return

    texto = (
        "🛠 *Guía rápida*\n\n"
        "1. Mete este bot al grupo y hazlo admin.\n"
        "2. En el grupo escribe: /setgroup\n"
        "3. En privado escribe: /addmsg para guardar mensajes\n"
        "4. En privado escribe: /setinterval\n"
        "5. En privado escribe: /startads\n\n"
        "*Importante:*\n"
        "- /setgroup se ejecuta dentro del grupo.\n"
        "- Los demás comandos mejor en privado con el bot.\n"
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")


@bot.message_handler(commands=["setgroup"])
def setgroup(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "❌ No autorizado.")
        return

    if message.chat.type not in ["group", "supergroup"]:
        bot.reply_to(message, "⚠️ Este comando se usa dentro del grupo.")
        return

    data["group_id"] = message.chat.id
    guardar_datos()

    bot.reply_to(
        message,
        f"✅ Grupo guardado correctamente.\n\n"
        f"🆔 Group ID: `{message.chat.id}`\n"
        f"📛 Grupo: {message.chat.title}",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["group"])
def ver_group(message):
    if not es_admin(message.from_user.id):
        return

    if data["group_id"]:
        bot.send_message(
            message.chat.id,
            f"📌 Grupo configurado:\n`{data['group_id']}`",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "⚠️ Aún no has configurado ningún grupo.")


@bot.message_handler(commands=["setinterval"])
def setinterval(message):
    if not es_admin(message.from_user.id):
        return

    waiting_state[message.from_user.id] = "set_interval"
    bot.send_message(
        message.chat.id,
        "⏱ Envía el nuevo intervalo.\n\n"
        "Ejemplos válidos:\n"
        "`120`  → 120 minutos\n"
        "`180`  → 180 minutos\n\n"
        "👉 Escribe solo el número en minutos.",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["addmsg"])
def addmsg(message):
    if not es_admin(message.from_user.id):
        return

    waiting_state[message.from_user.id] = "add_message"
    bot.send_message(
        message.chat.id,
        "📝 Envíame ahora el mensaje que quieres agregar a la rotación."
    )


@bot.message_handler(commands=["listmsgs"])
def listmsgs(message):
    if not es_admin(message.from_user.id):
        return

    if not data["messages"]:
        bot.send_message(message.chat.id, "⚠️ No hay mensajes guardados.")
        return

    partes = ["📋 *Mensajes guardados:*\n"]
    for i, msg in enumerate(data["messages"], start=1):
        preview = msg if len(msg) <= 180 else msg[:180] + "..."
        partes.append(f"*{i}.* {preview}")

    texto = "\n\n".join(partes)
    bot.send_message(message.chat.id, texto, parse_mode="Markdown", disable_web_page_preview=True)


@bot.message_handler(commands=["delmsg"])
def delmsg(message):
    if not es_admin(message.from_user.id):
        return

    if not data["messages"]:
        bot.send_message(message.chat.id, "⚠️ No hay mensajes para eliminar.")
        return

    waiting_state[message.from_user.id] = "delete_message"
    bot.send_message(
        message.chat.id,
        "🗑 Envía el número del mensaje que quieres eliminar.\n\n"
        "Usa /listmsgs para ver la lista."
    )


@bot.message_handler(commands=["sendnow"])
def sendnow(message):
    if not es_admin(message.from_user.id):
        return

    if not data["group_id"]:
        bot.send_message(message.chat.id, "⚠️ Primero configura el grupo con /setgroup.")
        return

    if not data["messages"]:
        bot.send_message(message.chat.id, "⚠️ No hay mensajes guardados.")
        return

    enviar_siguiente_mensaje()
    bot.send_message(message.chat.id, "✅ Mensaje enviado ahora mismo al grupo.")


@bot.message_handler(commands=["startads"])
def startads(message):
    if not es_admin(message.from_user.id):
        return

    if not data["group_id"]:
        bot.send_message(message.chat.id, "⚠️ Primero configura el grupo con /setgroup.")
        return

    if not data["messages"]:
        bot.send_message(message.chat.id, "⚠️ No hay mensajes guardados. Usa /addmsg.")
        return

    data["enabled"] = True
    guardar_datos()
    iniciar_loop_si_hace_falta()

    bot.send_message(
        message.chat.id,
        f"✅ Anuncios automáticos activados.\n\n"
        f"⏱ Intervalo actual: {formatear_intervalo(data['interval_seconds'])}"
    )


@bot.message_handler(commands=["stopads"])
def stopads(message):
    if not es_admin(message.from_user.id):
        return

    data["enabled"] = False
    guardar_datos()

    bot.send_message(message.chat.id, "⛔ Anuncios automáticos desactivados.")


@bot.message_handler(commands=["status"])
def status(message):
    if not es_admin(message.from_user.id):
        return

    estado = "ACTIVADO ✅" if data["enabled"] else "DESACTIVADO ⛔"
    group_id = data["group_id"] if data["group_id"] else "No configurado"
    total_msgs = len(data["messages"])
    last_sent = data["last_sent_at"] if data["last_sent_at"] else "Nunca"

    texto = (
        "📊 *Estado del bot de anuncios*\n\n"
        f"*Estado:* {estado}\n"
        f"*Grupo:* `{group_id}`\n"
        f"*Intervalo:* {formatear_intervalo(data['interval_seconds'])}\n"
        f"*Mensajes guardados:* {total_msgs}\n"
        f"*Último envío:* {last_sent}\n"
        f"*Índice actual:* {data['current_index'] + 1 if total_msgs else 0}"
    )

    bot.send_message(message.chat.id, texto, parse_mode="Markdown")


# =========================
# CAPTURA DE RESPUESTAS
# =========================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def capturar_textos(message):
    user_id = message.from_user.id

    if not es_admin(user_id):
        return

    estado = waiting_state.get(user_id)
    if not estado:
        return

    if estado == "set_interval":
        texto = message.text.strip()

        if not texto.isdigit():
            bot.send_message(message.chat.id, "❌ Envía solo números enteros en minutos.")
            return

        minutos = int(texto)
        if minutos < 1:
            bot.send_message(message.chat.id, "❌ El intervalo mínimo es 1 minuto.")
            return

        data["interval_seconds"] = minutos * 60
        guardar_datos()
        waiting_state.pop(user_id, None)

        bot.send_message(
            message.chat.id,
            f"✅ Intervalo actualizado a {formatear_intervalo(data['interval_seconds'])}."
        )
        return

    if estado == "add_message":
        texto = message.text.strip()

        if not texto:
            bot.send_message(message.chat.id, "❌ El mensaje no puede estar vacío.")
            return

        data["messages"].append(texto)
        guardar_datos()
        waiting_state.pop(user_id, None)

        bot.send_message(
            message.chat.id,
            f"✅ Mensaje agregado correctamente.\n\n"
            f"📦 Total guardados: {len(data['messages'])}"
        )
        return

    if estado == "delete_message":
        texto = message.text.strip()

        if not texto.isdigit():
            bot.send_message(message.chat.id, "❌ Debes enviar el número del mensaje.")
            return

        numero = int(texto)

        if numero < 1 or numero > len(data["messages"]):
            bot.send_message(message.chat.id, "❌ Número fuera de rango.")
            return

        eliminado = data["messages"].pop(numero - 1)

        if data["current_index"] >= len(data["messages"]) and data["messages"]:
            data["current_index"] = 0
        elif not data["messages"]:
            data["current_index"] = 0

        guardar_datos()
        waiting_state.pop(user_id, None)

        preview = eliminado if len(eliminado) <= 120 else eliminado[:120] + "..."
        bot.send_message(
            message.chat.id,
            f"🗑 Mensaje eliminado:\n\n{preview}"
        )
        return


# =========================
# INICIO
# =========================
iniciar_loop_si_hace_falta()

print("✅ Bot de anuncios iniciado correctamente.")
bot.infinity_polling(skip_pending=True)