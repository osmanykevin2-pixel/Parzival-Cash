import os
from datetime import datetime, timedelta

import telebot
from dotenv import load_dotenv
from supabase import create_client
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from telebot.types import ReplyKeyboardRemove

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_AFILIADOS") or os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6273485735"))

# Puedes usar IDs reales o usernames publicos.
CANAL_INFO_CHAT = os.getenv("AFILIADOS_CANAL_CHAT", "@CanalParzivalCash")
COMUNIDAD_CHAT = os.getenv("AFILIADOS_COMUNIDAD_CHAT", "@GrupoParzivalCash")

CANAL_INFO_LINK = os.getenv("AFILIADOS_CANAL_LINK", "https://t.me/CanalParzivalCash")
COMUNIDAD_LINK = os.getenv("AFILIADOS_COMUNIDAD_LINK", "https://t.me/GrupoParzivalCash")
BOT_PRINCIPAL_LINK = os.getenv("BOT_PRINCIPAL_LINK", "https://t.me/ParzivalCash_bot")
BOT_AFILIADOS_USERNAME = os.getenv("BOT_AFILIADOS_USERNAME", "AfiliadosParzivalCash_bot")

BONO_POR_REFERIDO = int(os.getenv("BONO_POR_REFERIDO", "10"))
RETIRO_MINIMO = int(os.getenv("RETIRO_MINIMO", "100"))
RETIRO_COOLDOWN_DIAS = int(os.getenv("RETIRO_COOLDOWN_DIAS", "3"))

@bot.message_handler(func=lambda message: message.chat.type != "private")
def limpiar_teclado_grupo(message):
    bot.send_message(
        message.chat.id,
        " ",
        reply_markup=ReplyKeyboardRemove()
    )

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Falta TELEGRAM_BOT_TOKEN_AFILIADOS o TELEGRAM_BOT_TOKEN en .env")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
bot.remove_webhook()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Datos temporales del flujo. No crean usuarios en DB antes de validar.
pending_referrals = {}
waiting_withdraw_amount = {}
pending_withdrawals = {}
next_withdrawal_id = 1

bot.set_my_commands([], scope=telebot.types.BotCommandScopeAllGroupChats())

@bot.message_handler(func=lambda message: message.chat.type != "private")
def ignore_groups(message):
    return

def db_get_user(user_id: int):
    result = (
        supabase.table("users")
        .select("*")
        .eq("telegram_user_id", int(user_id))
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def db_upsert_user(user_id: int, data: dict):
    payload = {"telegram_user_id": int(user_id)}
    payload.update(data)
    return (
        supabase.table("users")
        .upsert(payload, on_conflict="telegram_user_id")
        .execute()
    )


def db_get_top_users(limit: int = 10):
    result = (
        supabase.table("users")
        .select("telegram_user_id, telegram_username, referrals, balance_afiliados")
        .order("referrals", desc=True)
        .order("balance_afiliados", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def obtener_nombre_visible(user_obj):
    if user_obj.first_name and user_obj.first_name.strip():
        return user_obj.first_name.strip()
    if user_obj.username and user_obj.username.strip():
        return user_obj.username.strip()
    return "Usuario"


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


def teclado_validacion():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("📢 Canal de Información"),
        KeyboardButton("💬 Comunidad ParzivalCash")
    )
    markup.row(
        KeyboardButton("✅ Ya me uní")
    )
    return markup


def texto_inicio():
    return (
        "🎁 Sistema de Afiliados - Parzival Cash\n\n"
        f"💸 Gana {BONO_POR_REFERIDO} CUP por cada persona que entre a este bot con tu enlace personal.\n\n"
        "🤖 Desde aquí podrás:\n"
        "• obtener tu link de referido\n"
        "• revisar tu balance\n"
        "• solicitar retiros\n"
        "• ver el ranking de los mejores afiliados\n\n"
        "👇 Usa el menú para comenzar."
    )


def mostrar_balance(chat_id, user_id):
    usuario = db_get_user(user_id)

    if not usuario:
        bot.send_message(
            chat_id,
            "❌ No encontramos tu cuenta en el sistema de afiliados. "
            "Accede primero desde el bot principal o valida tu ingreso si vienes con un link de referido."
        )
        return

    texto = (
        f"👤 {usuario.get('telegram_username', 'Usuario')}\n"
        f"👥 Referidos: {usuario.get('referrals', 0)}\n"
        f"💰 Balance: {usuario.get('balance_afiliados', 0)} CUP"
    )
    bot.send_message(chat_id, texto)


def procesar_referido(nuevo_user_id: int, referrer_id: int):
    nuevo_user_id = int(nuevo_user_id)
    referrer_id = int(referrer_id)

    if nuevo_user_id == referrer_id:
        return

    referrer = db_get_user(referrer_id)
    if not referrer:
        return

    usuario_existente = db_get_user(nuevo_user_id)

    # Si ya estaba validado o ya tenía referidor, no sobreescribimos nada.
    if usuario_existente and (usuario_existente.get("validated") or usuario_existente.get("referred_by")):
        return

    # Guardamos pendiente en memoria. Aún NO se crea ni modifica fila del usuario nuevo.
    pending_referrals[nuevo_user_id] = referrer_id


def esta_en_chat(chat_ref, user_id):
    try:
        estado = bot.get_chat_member(chat_ref, int(user_id))
        return estado.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Error verificando membresía en {chat_ref}: {e}")
        return False


def esta_en_canal(user_id):
    return esta_en_chat(CANAL_INFO_CHAT, user_id)


def esta_en_grupo(user_id):
    return esta_en_chat(COMUNIDAD_CHAT, user_id)


def puede_retirar(user_id):
    usuario = db_get_user(user_id)
    if not usuario:
        return False, "Usuario no encontrado."

    ultima = usuario.get("last_withdraw")
    if not ultima:
        return True, None

    try:
        fecha_ultima = datetime.fromisoformat(ultima.replace("Z", "+00:00"))
    except Exception:
        return True, None

    ahora = datetime.now(fecha_ultima.tzinfo) if fecha_ultima.tzinfo else datetime.now()
    proximo_retiro = fecha_ultima + timedelta(days=RETIRO_COOLDOWN_DIAS)

    if ahora < proximo_retiro:
        faltante = proximo_retiro - ahora
        dias = faltante.days
        horas = int((faltante.seconds or 0) / 3600)
        return False, f"⏳ Podrás retirar nuevamente en aproximadamente {dias} días y {horas} horas."

    return True, None


def mostrar_ranking(chat_id):
    usuarios = db_get_top_users(10)

    if not usuarios:
        bot.send_message(chat_id, "📊 Aún no hay usuarios en el ranking.")
        return

    texto = "🏆 Top 10 de Afiliados\n\n"

    for i, usuario in enumerate(usuarios, start=1):
        nombre = usuario.get("telegram_username") or f"Usuario {usuario.get('telegram_user_id')}"
        referrals = usuario.get("referrals", 0) or 0
        balance = usuario.get("balance_afiliados", 0) or 0
        texto += f"{i}. {nombre} — {referrals} referidos — {balance} CUP\n"

    bot.send_message(chat_id, texto)


@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type != "private":
        return
    user_id = int(message.from_user.id)
    partes = message.text.split(maxsplit=1)

    # Si viene con link de referido, solo guardamos el pendiente y mostramos validación.
    if len(partes) > 1:
        referrer_id = partes[1].strip()

        if referrer_id.isdigit():
            procesar_referido(user_id, int(referrer_id))

            bot.send_message(
                message.chat.id,
                texto_inicio() + "\n\n⚠️ Debes unirte al canal y al grupo antes de continuar.",
                reply_markup=teclado_validacion()
            )
            return

    # Sin referido: acceso directo.
    bot.send_message(
        message.chat.id,
        texto_inicio(),
        reply_markup=teclado_principal()
    )


@bot.message_handler(commands=['admin'])
def admin_panel(message):

    if message.chat.type != "private":
        return
        
    if int(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ No autorizado.")
        return

    users_result = supabase.table("users").select("telegram_user_id", count="exact").execute()
    total_users = users_result.count or 0

    balance_result = supabase.table("users").select("balance_afiliados").execute()
    total_balance = sum((u.get("balance_afiliados") or 0) for u in (balance_result.data or []))

    pendientes = len(pending_withdrawals)

    texto = (
        "🛠️ Panel de Admin\n\n"
        f"👥 Usuarios registrados: {total_users}\n"
        f"💰 Balance total acumulado: {total_balance} CUP\n"
        f"🏧 Retiros pendientes en memoria: {pendientes}"
    )

    bot.send_message(message.chat.id, texto)


@bot.message_handler(commands=['aprobar'])
def aprobar_retiro(message):
    if int(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ No autorizado.")
        return

    partes = message.text.split()
    if len(partes) < 2:
        bot.send_message(message.chat.id, "Uso correcto:\n/aprobar ID_SOLICITUD")
        return

    withdraw_id = partes[1]

    if withdraw_id not in pending_withdrawals:
        bot.send_message(message.chat.id, "❌ Solicitud no encontrada.")
        return

    retiro = pending_withdrawals[withdraw_id]
    uid = int(retiro["user_id"])
    amount = retiro["amount"]

    usuario = db_get_user(uid)
    if not usuario:
        bot.send_message(message.chat.id, "❌ Usuario no encontrado.")
        return

    balance_actual = usuario.get("balance_afiliados", 0) or 0
    if balance_actual < amount:
        bot.send_message(message.chat.id, "❌ El usuario ya no tiene saldo suficiente.")
        return

    db_upsert_user(uid, {
        "balance_afiliados": balance_actual - amount,
        "last_withdraw": datetime.utcnow().isoformat()
    })

    pending_withdrawals.pop(withdraw_id, None)

    bot.send_message(
        message.chat.id,
        f"✅ Retiro aprobado para el usuario {uid} por {amount} CUP."
    )

    try:
        bot.send_message(
            uid,
            f"✅ Tu retiro fue aprobado correctamente.\n\n"
            f"💰 Monto: {amount} CUP"
        )
    except Exception as e:
        print("No se pudo notificar retiro aprobado:", e)


@bot.message_handler(func=lambda message: True)
def menu(message):

    if message.chat.type != "private":
        return
    global next_withdrawal_id

    user_id = int(message.from_user.id)

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
        usuario = db_get_user(user_id)

        if not usuario:
            bot.send_message(
                message.chat.id,
                "❌ Tu cuenta aún no está activa en el sistema de afiliados."
            )
            return

        link = f"https://t.me/{BOT_AFILIADOS_USERNAME}?start={user_id}"

        texto = (
            f"🔗 Tu link de referido:\n\n"
            f"{link}\n\n"
            f"👥 Referidos actuales: {usuario.get('referrals', 0)}\n"
            f"💰 Ganancias acumuladas: {usuario.get('balance_afiliados', 0)} CUP\n\n"
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
        usuario = db_get_user(user_id)

        if not usuario:
            bot.send_message(
                message.chat.id,
                "❌ Tu cuenta aún no está activa en el sistema de afiliados."
            )
            return

        permitido, motivo = puede_retirar(user_id)
        if not permitido:
            bot.send_message(message.chat.id, motivo)
            return

        balance_actual = usuario.get("balance_afiliados", 0) or 0

        if balance_actual < RETIRO_MINIMO:
            bot.send_message(
                message.chat.id,
                f"❌ No puedes retirar todavía.\n\n"
                f"💰 Balance actual: {balance_actual} CUP\n"
                f"📌 Retiro mínimo: {RETIRO_MINIMO} CUP"
            )
            return

        waiting_withdraw_amount[user_id] = True

        bot.send_message(
            message.chat.id,
            f"🏧 Solicitud de retiro\n\n"
            f"💰 Balance actual: {balance_actual} CUP\n"
            f"📌 Mínimo: {RETIRO_MINIMO} CUP\n\n"
            "✍️ Escribe ahora el monto que deseas retirar."
        )

    elif message.text == "✅ Ya me uní":
        if not esta_en_canal(user_id) or not esta_en_grupo(user_id):
            bot.send_message(
                message.chat.id,
                "❌ Debes unirte al canal y al grupo antes de continuar."
            )
            return

        referrer_id = pending_referrals.get(user_id)

        if referrer_id is None:
            bot.send_message(
                message.chat.id,
                texto_inicio(),
                reply_markup=teclado_principal()
            )
            return

        usuario = db_get_user(user_id)

        # Si ya existe y ya estaba validado, no repetimos nada.
        if usuario and usuario.get("validated"):
            pending_referrals.pop(user_id, None)
            bot.send_message(
                message.chat.id,
                texto_inicio(),
                reply_markup=teclado_principal()
            )
            return

        nombre_visible = obtener_nombre_visible(message.from_user)

        if not usuario:
            db_upsert_user(user_id, {
                "telegram_username": nombre_visible,
                "referrals": 0,
                "balance_afiliados": 0,
                "referred_by": referrer_id,
                "validated": True
            })
        else:
            db_upsert_user(user_id, {
                "telegram_username": nombre_visible,
                "referred_by": usuario.get("referred_by") or referrer_id,
                "validated": True
            })

        referrer = db_get_user(referrer_id)
        if referrer:
            nuevo_referrals = (referrer.get("referrals") or 0) + 1
            nuevo_balance = (referrer.get("balance_afiliados") or 0) + BONO_POR_REFERIDO

            db_upsert_user(referrer_id, {
                "referrals": nuevo_referrals,
                "balance_afiliados": nuevo_balance
            })

            try:
                bot.send_message(
                    int(referrer_id),
                    f"🎉 Nuevo referido validado\n\n"
                    f"👤 Usuario: {nombre_visible}\n"
                    f"💸 Ganancia: {BONO_POR_REFERIDO} CUP"
                )
            except Exception as e:
                print("No se pudo notificar al referidor:", e)

        pending_referrals.pop(user_id, None)

        bot.send_message(
            message.chat.id,
            "✅ Verificación completada. Ya puedes usar el bot.",
            reply_markup=teclado_principal()
        )

    elif user_id in waiting_withdraw_amount:
        texto = message.text.strip()

        if not texto.isdigit():
            bot.send_message(message.chat.id, "❌ Monto no válido. Escribe solo números.")
            return

        monto = int(texto)
        usuario = db_get_user(user_id)

        if not usuario:
            bot.send_message(message.chat.id, "❌ Usuario no encontrado.")
            waiting_withdraw_amount.pop(user_id, None)
            return

        balance_actual = usuario.get("balance_afiliados", 0) or 0

        if monto < RETIRO_MINIMO:
            bot.send_message(
                message.chat.id,
                f"❌ El retiro mínimo es de {RETIRO_MINIMO} CUP."
            )
            return

        if monto > balance_actual:
            bot.send_message(
                message.chat.id,
                f"❌ No tienes saldo suficiente.\n\n"
                f"💰 Balance actual: {balance_actual} CUP"
            )
            return

        withdraw_id = str(next_withdrawal_id)
        next_withdrawal_id += 1

        pending_withdrawals[withdraw_id] = {
            "user_id": user_id,
            "name": usuario.get("telegram_username", "Usuario"),
            "amount": monto,
            "created_at": datetime.utcnow().isoformat()
        }

        waiting_withdraw_amount.pop(user_id, None)

        bot.send_message(
            message.chat.id,
            f"✅ Solicitud de retiro enviada correctamente.\n\n"
            f"🆔 Solicitud: {withdraw_id}\n"
            f"💰 Monto: {monto} CUP"
        )

        try:
            tarjeta = usuario.get("card", "No configurada")
            markup_admin = InlineKeyboardMarkup()
            markup_admin.row(
                InlineKeyboardButton("✅ Completar", callback_data=f"aprobar_{withdraw_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_{withdraw_id}")
            )           
            bot.send_message(
                ADMIN_ID,
                f"🏧 Nueva solicitud de retiro\n\n"
                f"🆔 Solicitud: {withdraw_id}\n"
                f"👤 Usuario: {usuario.get('telegram_username', 'Usuario')}\n"
                f"🆔 ID Telegram: {user_id}\n"
                f"💳 Tarjeta: {tarjeta}\n"
                f"💰 Monto: {monto} CUP\n\n",
                reply_markup=markup_admin
            )
        except Exception as e:
            print("No se pudo enviar solicitud al admin:", e)

    else:
        bot.send_message(
            message.chat.id,
            "Escribe /start para abrir el menú."
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_admin_actions(call):

    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ No autorizado")
        return

    data = call.data

    if data.startswith("aprobar_"):
        withdraw_id = data.replace("aprobar_", "")

        if withdraw_id not in pending_withdrawals:
            bot.answer_callback_query(call.id, "❌ No encontrada")
            return

        retiro = pending_withdrawals[withdraw_id]
        user_id = retiro["user_id"]
        amount = retiro["amount"]

        usuario = db_get_user(user_id)
        balance = usuario.get("balance_afiliados", 0)

        if balance < amount:
            bot.send_message(call.message.chat.id, "❌ Sin saldo suficiente")
            return

        db_upsert_user(user_id, {
            "balance_afiliados": balance - amount,
            "last_withdraw": datetime.utcnow().isoformat()
        })

        bot.send_message(user_id, f"✅ Tu retiro fue exitoso\n💰 {amount} CUP")

        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )

        bot.answer_callback_query(call.id, "✅ Aprobado")

    elif data.startswith("rechazar_"):
        withdraw_id = data.replace("rechazar_", "")

        if withdraw_id not in pending_withdrawals:
            bot.answer_callback_query(call.id, "❌ No encontrada")
            return

        retiro = pending_withdrawals[withdraw_id]
        user_id = retiro["user_id"]

        bot.send_message(user_id, "❌ Tu solicitud fue rechazada")

        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )

        bot.answer_callback_query(call.id, "❌ Rechazado")


print("✅ Bot de afiliados iniciado...")
bot.infinity_polling(skip_pending=True)
