import json
import os
from datetime import datetime, timedelta

import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

bot = telebot.TeleBot("8686137791:AAF4TOoXMoVLoP_FireDqIpsbbw4rFQru6w")
bot.remove_webhook()

ADMIN_ID = 6273485735
DATA_FILE = "afiliados_data.json"

BONO_POR_REFERIDO = 10
RETIRO_MINIMO = 100
RETIRO_COOLDOWN_DIAS = 3

CANAL_INFO_LINK = "https://t.me/CanalParzivalCash"
COMUNIDAD_LINK = "https://t.me/GrupoParzivalCash"
BOT_PRINCIPAL_LINK = "https://t.me/ParzivalCash_bot"
BOT_AFILIADOS_USERNAME = "AfiliadosParzivalCash_bot"

data = {}
waiting_withdraw_amount = {}


def cargar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "users": {},
        "withdrawals": {},
        "next_withdrawal_id": 1
    }


def guardar_datos():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def obtener_nombre_visible(user_obj):
    if user_obj.first_name and user_obj.first_name.strip():
        return user_obj.first_name.strip()
    if user_obj.username and user_obj.username.strip():
        return user_obj.username.strip()
    return "Usuario"


def obtener_usuario(user_id, nombre_visible="Usuario"):
    user_id = str(user_id)

    if user_id not in data["users"]:
        data["users"][user_id] = {
            "name": nombre_visible,
            "referrals": 0,
            "balance": 0,
            "referred_by": None,
            "last_withdraw": None
        }
    else:
        data["users"][user_id]["name"] = nombre_visible

    guardar_datos()
    return data["users"][user_id]


def teclado_principal():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("📢 Canal de Información"),
        KeyboardButton("💬 Comunidad ParzivalCash")
    )
    markup.row(
        KeyboardButton("🤖 Bot Principal"),
        KeyboardButton("🔗 Link de referidos")
    )
    markup.row(
        KeyboardButton("💰 Balance"),
        KeyboardButton("🏧 Retirar")
    )
    markup.row(
        KeyboardButton("📊 Ranking Top 10")
    )
    return markup


def texto_inicio():
    return (
        "🎁 Sistema de Afiliados - Parzival Cash\n\n"
        "💸 Gana 10 CUP por cada persona que entre a este bot con tu enlace personal.\n\n"
        "🤖 Desde aquí podrás:\n"
        "• obtener tu link de referido\n"
        "• revisar tu balance\n"
        "• solicitar retiros\n"
        "• ver el ranking de los mejores afiliados\n\n"
        "👇 Usa el menú para comenzar."
    )


def mostrar_balance(chat_id, user_id):
    usuario = data["users"].get(str(user_id))
    if not usuario:
        return

    texto = (
        f"👤 {usuario['name']}\n"
        f"👥 Referidos: {usuario['referrals']}\n"
        f"💰 Balance: {usuario['balance']} CUP"
    )
    bot.send_message(chat_id, texto)


def procesar_referido(nuevo_user_id, referrer_id, nuevo_nombre):
    nuevo_user_id = str(nuevo_user_id)
    referrer_id = str(referrer_id)

    if nuevo_user_id == referrer_id:
        return

    if referrer_id not in data["users"]:
        return

    usuario_nuevo = obtener_usuario(nuevo_user_id, nuevo_nombre)

    if usuario_nuevo["referred_by"] is not None:
        return

    usuario_nuevo["referred_by"] = referrer_id
    data["users"][referrer_id]["referrals"] += 1
    data["users"][referrer_id]["balance"] += BONO_POR_REFERIDO
    guardar_datos()

    try:
        bot.send_message(
            int(referrer_id),
            f"🎉 Nuevo referido registrado\n\n"
            f"👤 Usuario: {nuevo_nombre}\n"
            f"💸 Ganancia acreditada: {BONO_POR_REFERIDO} CUP\n"
            f"💰 Nuevo balance: {data['users'][referrer_id]['balance']} CUP"
        )
    except Exception as e:
        print("No se pudo notificar al referidor:", e)


def puede_retirar(user_id):
    usuario = data["users"].get(str(user_id))
    if not usuario:
        return False, "Usuario no encontrado."

    ultima = usuario.get("last_withdraw")
    if not ultima:
        return True, None

    try:
        fecha_ultima = datetime.fromisoformat(ultima)
    except Exception:
        return True, None

    proximo_retiro = fecha_ultima + timedelta(days=RETIRO_COOLDOWN_DIAS)
    if datetime.now() < proximo_retiro:
        faltante = proximo_retiro - datetime.now()
        dias = faltante.days
        horas = int((faltante.seconds or 0) / 3600)
        return False, f"⏳ Podrás retirar nuevamente en aproximadamente {dias} días y {horas} horas."

    return True, None


def mostrar_ranking(chat_id):
    usuarios = list(data["users"].values())

    if not usuarios:
        bot.send_message(chat_id, "📊 Aún no hay usuarios en el ranking.")
        return

    top = sorted(
        usuarios,
        key=lambda u: (u.get("referrals", 0), u.get("balance", 0)),
        reverse=True
    )[:10]

    texto = "🏆 Top 10 de Afiliados\n\n"

    for i, usuario in enumerate(top, start=1):
        texto += (
            f"{i}. {usuario.get('name', 'Usuario')} — "
            f"{usuario.get('referrals', 0)} referidos — "
            f"{usuario.get('balance', 0)} CUP\n"
        )

    bot.send_message(chat_id, texto)


@bot.message_handler(commands=['start'])
def start(message):
    nombre_visible = obtener_nombre_visible(message.from_user)
    user_id = message.from_user.id

    obtener_usuario(user_id, nombre_visible)

    partes = message.text.split()

    if len(partes) > 1:
        referrer_id = partes[1]
        if referrer_id.isdigit():
            procesar_referido(user_id, referrer_id, nombre_visible)

    bot.send_message(
        message.chat.id,
        texto_inicio(),
        reply_markup=teclado_principal()
    )


@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ No autorizado.")
        return

    total_users = len(data["users"])
    total_balance = sum(user["balance"] for user in data["users"].values())
    total_withdrawals = len(data["withdrawals"])
    pendientes = sum(1 for w in data["withdrawals"].values() if w["status"] == "pendiente")

    texto = (
        "🛠️ Panel de Admin\n\n"
        f"👥 Usuarios registrados: {total_users}\n"
        f"💰 Balance total acumulado: {total_balance} CUP\n"
        f"🏧 Solicitudes de retiro: {total_withdrawals}\n"
        f"🕐 Retiros pendientes: {pendientes}"
    )

    bot.send_message(message.chat.id, texto)


@bot.message_handler(func=lambda message: True)
def menu(message):
    user_id = str(message.from_user.id)
    nombre_visible = obtener_nombre_visible(message.from_user)
    obtener_usuario(user_id, nombre_visible)

    if message.text == "📢 Canal de Información":
        bot.send_message(
            message.chat.id,
            f"📢 Canal de Información oficial:\n{CANAL_INFO_LINK}",
            disable_web_page_preview=False
        )

    elif message.text == "💬 Comunidad ParzivalCash":
        bot.send_message(
            message.chat.id,
            f"💬 Comunidad oficial:\n{COMUNIDAD_LINK}",
            disable_web_page_preview=False
        )

    elif message.text == "🤖 Bot Principal":
        bot.send_message(
            message.chat.id,
            f"🤖 Bot Principal:\n{BOT_PRINCIPAL_LINK}",
            disable_web_page_preview=False
        )

    elif message.text == "🔗 Link de referidos":
        usuario = data["users"][user_id]
        link = f"https://t.me/{BOT_AFILIADOS_USERNAME}?start={user_id}"

        texto = (
            f"🔗 Tu link de referido:\n\n"
            f"{link}\n\n"
            f"👥 Referidos actuales: {usuario['referrals']}\n"
            f"💰 Ganancias acumuladas: {usuario['balance']} CUP\n\n"
            f"🎁 Ganas {BONO_POR_REFERIDO} CUP por cada persona que entre con tu enlace."
        )

        bot.send_message(
            message.chat.id,
            texto,
            disable_web_page_preview=False
        )

    elif message.text == "💰 Balance":
        mostrar_balance(message.chat.id, user_id)

    elif message.text == "📊 Ranking Top 10":
        mostrar_ranking(message.chat.id)

    elif message.text == "🏧 Retirar":
        usuario = data["users"].get(user_id)

        permitido, motivo = puede_retirar(user_id)
        if not permitido:
            bot.send_message(message.chat.id, motivo)
            return

        if usuario["balance"] < RETIRO_MINIMO:
            bot.send_message(
                message.chat.id,
                f"❌ No puedes retirar todavía.\n\n"
                f"💰 Balance actual: {usuario['balance']} CUP\n"
                f"📌 Retiro mínimo: {RETIRO_MINIMO} CUP"
            )
            return

        waiting_withdraw_amount[user_id] = True

        bot.send_message(
            message.chat.id,
            f"🏧 Solicitud de retiro\n\n"
            f"💰 Balance actual: {usuario['balance']} CUP\n"
            f"📌 Mínimo: {RETIRO_MINIMO} CUP\n\n"
            "✍️ Escribe ahora el monto que deseas retirar."
        )

    elif user_id in waiting_withdraw_amount:
        texto = message.text.strip()

        if not texto.isdigit():
            bot.send_message(message.chat.id, "❌ Monto no válido. Escribe solo números.")
            return

        monto = int(texto)
        usuario = data["users"].get(user_id)

        if monto < RETIRO_MINIMO:
            bot.send_message(
                message.chat.id,
                f"❌ El retiro mínimo es de {RETIRO_MINIMO} CUP."
            )
            return

        if monto > usuario["balance"]:
            bot.send_message(
                message.chat.id,
                f"❌ No tienes saldo suficiente.\n\n"
                f"💰 Balance actual: {usuario['balance']} CUP"
            )
            return

        withdraw_id = str(data["next_withdrawal_id"])
        data["next_withdrawal_id"] += 1

        data["withdrawals"][withdraw_id] = {
            "user_id": user_id,
            "name": usuario["name"],
            "amount": monto,
            "status": "pendiente",
            "created_at": datetime.now().isoformat()
        }
        guardar_datos()

        waiting_withdraw_amount.pop(user_id, None)

        bot.send_message(
            message.chat.id,
            f"✅ Solicitud de retiro enviada correctamente.\n\n"
            f"🆔 Solicitud: {withdraw_id}\n"
            f"💰 Monto: {monto} CUP"
        )

        try:
            bot.send_message(
                ADMIN_ID,
                f"🏧 Nueva solicitud de retiro\n\n"
                f"🆔 Solicitud: {withdraw_id}\n"
                f"👤 Usuario: {usuario['name']}\n"
                f"🆔 ID Telegram: {user_id}\n"
                f"💰 Monto: {monto} CUP\n\n"
                f"Para aprobar manualmente usa:\n"
                f"/aprobar {withdraw_id}"
            )
        except Exception as e:
            print("No se pudo enviar solicitud al admin:", e)

    else:
        bot.send_message(
            message.chat.id,
            "Escribe /start para abrir el menú."
        )


@bot.message_handler(commands=['aprobar'])
def aprobar_retiro(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ No autorizado.")
        return

    partes = message.text.split()
    if len(partes) < 2:
        bot.send_message(message.chat.id, "Uso correcto:\n/aprobar ID_SOLICITUD")
        return

    withdraw_id = partes[1]

    if withdraw_id not in data["withdrawals"]:
        bot.send_message(message.chat.id, "❌ Solicitud no encontrada.")
        return

    retiro = data["withdrawals"][withdraw_id]

    if retiro["status"] != "pendiente":
        bot.send_message(message.chat.id, "⚠️ Esta solicitud ya fue procesada.")
        return

    uid = str(retiro["user_id"])
    amount = retiro["amount"]

    if uid not in data["users"]:
        bot.send_message(message.chat.id, "❌ Usuario no encontrado.")
        return

    if data["users"][uid]["balance"] < amount:
        bot.send_message(message.chat.id, "❌ El usuario ya no tiene saldo suficiente.")
        return

    data["users"][uid]["balance"] -= amount
    data["users"][uid]["last_withdraw"] = datetime.now().isoformat()
    retiro["status"] = "aprobado"
    guardar_datos()

    bot.send_message(
        message.chat.id,
        f"✅ Retiro aprobado para el usuario {uid} por {amount} CUP."
    )

    try:
        bot.send_message(
            int(uid),
            f"✅ Tu retiro fue aprobado correctamente.\n\n"
            f"💰 Monto: {amount} CUP"
        )
    except Exception as e:
        print("No se pudo notificar retiro aprobado:", e)


data = cargar_datos()

print("✅ Bot de afiliados iniciado...")
bot.infinity_polling(skip_pending=True)