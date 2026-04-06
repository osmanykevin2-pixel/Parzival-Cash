import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
import os
from dotenv import load_dotenv
from supabase import create_client
import time

pending_xbet_requests = {}


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "images")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
ADMIN_ID = int(os.getenv("ADMIN_ID", "6273485735"))

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
bot.remove_webhook()

REFERIDO_LINK = "https://reffpa.com/L?tag=d_5432945m_97c_&site=5432945&ad=97"
PROMO_CODE = "10253608"

GUIA_LINK = "https://t.me/RegistroParzivalCash"
TASAS_LINK = "https://t.me/TasasParzivalCash"
TC_LINK = "https://t.me/parzivalcash_tc"
GRUPO_LINK = "https://t.me/GrupoParzivalCash"
CANAL_LINK = "https://t.me/CanalParzivalCash"
AFILIADOS_LINK = "https://t.me/AfiliadosParzivalCash_bot?start=parzival"

def ensure_user_exists(user_id, username=None):
    try:
        existing = (
            supabase.table("users")
            .select("telegram_user_id")
            .eq("telegram_user_id", user_id)
            .execute()
        )

        if not existing.data:
            supabase.table("users").insert({
                "telegram_user_id": user_id,
                "telegram_username": username
            }).execute()
    except Exception as e:
        print(f"Error asegurando usuario en BD: {e}")

def db_get_user(user_id):
    result = (
        supabase.table("users")
        .select("*")
        .eq("telegram_user_id", user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def db_upsert_user(user_id, data: dict):
    payload = {"telegram_user_id": user_id}
    payload.update(data)

    result = (
        supabase.table("users")
        .upsert(payload, on_conflict="telegram_user_id")
        .execute()
    )
    return result

user_data = {}
pending_recharges = {}
next_recharge_id = 1

pending_withdrawals = {}
next_withdrawal_id = 1

last_screen_message = {}


def generar_recharge_id():
    global next_recharge_id
    recharge_id = str(next_recharge_id)
    next_recharge_id += 1
    return recharge_id


def generar_withdrawal_id():
    global next_withdrawal_id
    withdrawal_id = str(next_withdrawal_id)
    next_withdrawal_id += 1
    return withdrawal_id


def safe_delete_message(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass


def clear_last_screen(user_id, chat_id):
    if user_id in last_screen_message:
        safe_delete_message(chat_id, last_screen_message[user_id])
        last_screen_message.pop(user_id, None)


def send_screen(user_id, chat_id, text, reply_markup=None, photo_path=None, parse_mode='Markdown'):
    if photo_path:
        try:
            ruta = os.path.join(ASSETS_DIR, photo_path)

            with open(ruta, "rb") as foto:
                bot.send_photo(
                    chat_id,
                    foto,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
        except Exception as e:
            print("Error cargando imagen:", e)
            bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    else:
        bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)


def crear_menu_principal():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👤 Panel de Usuario", callback_data='panel'),
        InlineKeyboardButton("🎟️ Invita y Gana", callback_data='invita')
    )
    markup.add(
        InlineKeyboardButton("💰 Recargar Cuenta", callback_data='recargar'),
        InlineKeyboardButton("🏧 Extraer", callback_data='extraer')
    )
    markup.add(
        InlineKeyboardButton("📖 Guía para registro", callback_data='guia'),
        InlineKeyboardButton("📊 Tasas de cambio", callback_data='tasas')
    )
    markup.add(
        InlineKeyboardButton("📜 T&C Parzival Cash", callback_data='tc'),
        InlineKeyboardButton("🛠️ Soporte", callback_data='soporte')
    )
    markup.add(
        InlineKeyboardButton("💬 Grupo de Chat", callback_data='grupo'),
        InlineKeyboardButton("📢 Canal de Información", callback_data='canal')
    )
    return markup


def mostrar_inicio_completo(chat_id, user_id):
    clear_last_screen(user_id, chat_id)

    texto = f"""💎 **Bienvenido a Parzival Cash**

Soy tu **BOT Asistente Oficial** para recargas y retiros de tu cuenta en el sitio oficial de **1XBET**.

⚡ **Servicio rápido, seguro y confiable**
💸 Recarga tu cuenta y recibe tus pagos en **CUP desde Cuba 🇨🇺**

🎁 **Promo de Bienvenida**
Recarga **3 USD$** y recibe **5 USD$** 👇

🔗 **Regístrate aquí:**
[Crear cuenta en 1XBET]({REFERIDO_LINK})

🏷️ **Código promocional:**
`{PROMO_CODE}`

🎉 Además, obtienes el **bono del 100% de tu primer depósito** retirable después de cumplir las condiciones de la plataforma.

📩 Si necesitas ayuda, soporte o tienes alguna duda, utiliza el botón **Soporte** del menú."""

    bot.send_message(
        chat_id,
        texto,
        reply_markup=crear_menu_principal(),
        parse_mode='Markdown'
    )


def mostrar_inicio_corto(chat_id, user_id):
    texto = (
        "🏠 **Menú principal de Parzival Cash**\n\n"
        "Seleccione una opción para continuar."
    )
    send_screen(
        user_id,
        chat_id,
        texto,
        reply_markup=crear_menu_principal()
    )


def crear_panel_usuario(user_id, nombre_usuario):
    datos = db_get_user(user_id) or {}
    cuenta_1xbet = datos.get('xbet_id', 'No configurada')
    tarjeta = datos.get('card', 'No configurada')
    movil = datos.get('phone_number', 'No configurado')

    markup_panel = InlineKeyboardMarkup(row_width=1)
    markup_panel.add(
        InlineKeyboardButton("✅ Verificar el Cajero", callback_data='verificar'),
        InlineKeyboardButton("⚙️ Configurar Direcciones", callback_data='configurar'),
        InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
    )

    texto_panel = f"""**Parzival Cash**

**Nombre:** {nombre_usuario} ({user_id})
**Cuenta 1X:** {cuenta_1xbet}

**Direcciones de crédito:**
💳 **Tarjeta CUP:** {tarjeta}
📱 **Saldo Móvil:** {movil}

✅ Comprueba que Parzival Cash es un cajero oficial solicitando una verificación. Se enviará un mensaje al buzón de su cuenta en el sitio oficial de 1XBET."""
    return texto_panel, markup_panel


def mostrar_resumen_direcciones(chat_id, user_id):
    datos = db_get_user(user_id) or {}
    tarjeta = datos.get('card', 'No configurada')
    movil = datos.get('phone_number', 'No configurado')

    markup_guardado = InlineKeyboardMarkup(row_width=1)
    markup_guardado.add(
        InlineKeyboardButton("⚙️ Configurar otra dirección", callback_data='seleccionar_direccion'),
        InlineKeyboardButton("👤 Panel de Usuario", callback_data='panel'),
        InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
    )

    texto_guardado = (
        "✅ **Sus direcciones han sido guardadas exitosamente.**\n\n"
        f"💳 **Tarjeta CUP:**\n{tarjeta}\n\n"
        f"📲 **Saldo Móvil:**\n{movil}"
    )

    send_screen(user_id, chat_id, texto_guardado, reply_markup=markup_guardado)

def manejar_comandos_globales(message):
    texto = (message.text or "").strip()
    if texto == "/start":
        send_welcome(message)
        return True
    if texto == "/menu":
        send_menu(message)
        return True
    return False

def guardar_tarjeta(message):
    if manejar_comandos_globales(message):
        return
    user_id = message.from_user.id
    tarjeta = message.text.strip().replace("-", "").replace(" ", "")

    if not tarjeta.isdigit():
        msg = bot.send_message(
            message.chat.id,
            "❌ **Tarjeta no válida**\n\n📌 Por favor, envía solo números.",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, guardar_tarjeta)
        return

    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['tarjeta'] = tarjeta
    db_upsert_user(user_id, {"card": tarjeta})
    mostrar_resumen_direcciones(message.chat.id, user_id)

def guardar_movil(message):
    if manejar_comandos_globales(message):
        return
    user_id = message.from_user.id
    movil = message.text.strip().replace(" ", "")

    if not movil.isdigit():
        msg = bot.send_message(
            message.chat.id,
            "❌ **Número no válido**\n\n📌 Por favor, envía solo números.",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, guardar_movil)
        return

    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]['movil'] = movil

    db_upsert_user(user_id, {"phone_number": movil})

    mostrar_resumen_direcciones(message.chat.id, user_id)

def guardar_id_1xbet(message):
    if manejar_comandos_globales(message):
        return
    user_id = message.from_user.id
    nombre_usuario = message.from_user.first_name or "Usuario"
    xbet_id = message.text.strip()

    if not xbet_id.isdigit():
        msg = bot.send_message(
            message.chat.id,
            "❌ **ID no válido**\n\n📌 Por favor, envía solo números.",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, guardar_id_1xbet)
        return

    pending_xbet_requests[user_id] = {"xbet_id": xbet_id,"nombre_usuario": nombre_usuario}

    send_screen(
        user_id,
        message.chat.id,
        f"⏳ **ID enviado para revisión:** `{xbet_id}`\n\n"
        "📨 Ahora el cajero podrá aprobar o rechazar tu solicitud."
    )

    datos = db_get_user(user_id) or {}
    tarjeta = datos.get('card', 'No configurada')
    movil = datos.get('phone_number', 'No configurado')

    markup_admin = InlineKeyboardMarkup(row_width=2)
    markup_admin.add(
        InlineKeyboardButton("✅ Aceptar", callback_data=f"aprobar_{user_id}"),
        InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_{user_id}")
    )

    texto_admin = (
        "🔔 **Nueva solicitud de verificación**\n\n"
        f"👤 **Nombre:** {nombre_usuario}\n"
        f"🆔 **ID Telegram:** {user_id}\n"
        f"🎮 **Cuenta 1XBET:** {xbet_id}\n"
        f"💳 **Tarjeta:** {tarjeta}\n"
        f"📱 **Móvil:** {movil}\n\n"
        "Seleccione una opción:"
    )

    try:
        bot.send_message(
            ADMIN_ID,
            texto_admin,
            reply_markup=markup_admin,
            parse_mode='Markdown'
        )
    except Exception as e:
        print("No se pudo enviar mensaje al admin:", e)


def pedir_comprobante_recarga(message):
    if manejar_comandos_globales(message):
        return
    if not (message.photo or message.document):
        msg = bot.send_message(
            message.chat.id,
            "❌ **Debes enviar una captura o archivo del comprobante.**\n\n"
            "📸 Envíe la captura completa, sin recortes ni tachones.\n",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, pedir_comprobante_recarga)
        return

    user_id = message.from_user.id
    nombre_usuario = message.from_user.first_name or "Usuario"
    datos = db_get_user(user_id) or {}
    cuenta_1xbet = datos.get('xbet_id', 'No configurada')
    tarjeta_usuario = datos.get('card', 'No configurada')
    movil_usuario = datos.get('phone_number', 'No configurado')

    recharge_id = generar_recharge_id()

    pending_recharges[recharge_id] = {
        "user_id": user_id,
        "name": nombre_usuario,
        "cuenta_1xbet": cuenta_1xbet,
        "tarjeta_usuario": tarjeta_usuario,
        "movil_usuario": movil_usuario,
        "status": "pendiente"
    }

    send_screen(
        user_id,
        message.chat.id,
        "✅ **Comprobante recibido correctamente.**\n\n"
        "⏳ Su recarga será revisada por el cajero.\n"
        "📨 Espere la confirmación final."
    )

    markup_admin = InlineKeyboardMarkup(row_width=2)
    markup_admin.add(
        InlineKeyboardButton("✅ Aprobar recarga", callback_data=f"aprobar_recarga_{recharge_id}"),
        InlineKeyboardButton("❌ Rechazar recarga", callback_data=f"rechazar_recarga_{recharge_id}")
    )

    texto_admin = (
        "💰 **Nueva verificación de recarga**\n\n"
        f"🆔 **Solicitud:** {recharge_id}\n"
        f"👤 **Nombre:** {nombre_usuario}\n"
        f"🆔 **ID Telegram:** {user_id}\n"
        f"🎮 **Cuenta 1XBET:** {cuenta_1xbet}\n"
        f"💳 **Tarjeta registrada:** {tarjeta_usuario}\n"
        f"📱 **Móvil registrado:** {movil_usuario}\n\n"
        "📸 El comprobante fue enviado arriba.\n"
        "Seleccione una opción:"
    )

    try:
        if message.photo:
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id)
        elif message.document:
            bot.send_document(ADMIN_ID, message.document.file_id)

        bot.send_message(
            ADMIN_ID,
            texto_admin,
            reply_markup=markup_admin,
            parse_mode='Markdown'
        )
    except Exception as e:
        print("No se pudo enviar la recarga al admin:", e)


def recibir_captura_retiro(message):
    if manejar_comandos_globales(message):
        return
    if not (message.photo or message.document):
        msg = bot.send_message(
            message.chat.id,
            "❌ **Debes enviar una captura válida del código o del estado aprobado.**",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, recibir_captura_retiro)
        return

    user_id = message.from_user.id
    nombre_usuario = message.from_user.first_name or "Usuario"
    datos = db_get_user(user_id) or {}
    cuenta_1xbet = datos.get('xbet_id', 'No configurada')
    tarjeta_usuario = datos.get('card', 'No configurada')
    movil_usuario = datos.get('phone_number', 'No configurado')

    withdrawal_id = generar_withdrawal_id()

    pending_withdrawals[withdrawal_id] = {
        "user_id": user_id,
        "name": nombre_usuario,
        "cuenta_1xbet": cuenta_1xbet,
        "tarjeta_usuario": tarjeta_usuario,
        "movil_usuario": movil_usuario,
        "status": "revision",
        "metodo": None
    }

    send_screen(
        user_id,
        message.chat.id,
        "✅ **Captura recibida correctamente.**\n\n"
        "⏳ Su retiro está siendo revisado por el cajero."
    )

    markup_admin = InlineKeyboardMarkup(row_width=2)
    markup_admin.add(
        InlineKeyboardButton("✅ Aprobar retiro", callback_data=f"aprobar_retiro_{withdrawal_id}"),
        InlineKeyboardButton("❌ Rechazar retiro", callback_data=f"rechazar_retiro_{withdrawal_id}")
    )

    texto_admin = (
        "🏧 **Nueva solicitud de retiro**\n\n"
        f"🆔 **Solicitud:** {withdrawal_id}\n"
        f"👤 **Nombre:** {nombre_usuario}\n"
        f"🆔 **ID Telegram:** {user_id}\n"
        f"🎮 **Cuenta 1XBET:** {cuenta_1xbet}\n"
        f"💳 **Tarjeta registrada:** {tarjeta_usuario}\n"
        f"📱 **Móvil registrado:** {movil_usuario}\n\n"
        "📸 La captura fue enviada arriba.\n"
        "Seleccione una opción:"
    )

    try:
        if message.photo:
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id)
        elif message.document:
            bot.send_document(ADMIN_ID, message.document.file_id)

        bot.send_message(
            ADMIN_ID,
            texto_admin,
            reply_markup=markup_admin,
            parse_mode='Markdown'
        )
    except Exception as e:
        print("No se pudo enviar el retiro al admin:", e)


def recibir_soporte(message):
    if manejar_comandos_globales(message):
        return
    user_id = message.from_user.id
    nombre = message.from_user.first_name or "Usuario"
    username = f"@{message.from_user.username}" if message.from_user.username else "Sin @usuario"
    texto_usuario = message.text.strip()

    if not texto_usuario:
        msg = bot.send_message(
            message.chat.id,
            "❌ Por favor, describa su problema con texto.",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, recibir_soporte)
        return

    send_screen(
        user_id,
        message.chat.id,
        "✅ **Su mensaje fue enviado correctamente a soporte.**\n\n"
        "⏳ En cuanto revisemos su caso, le responderemos."
    )

    texto_admin = (
        "🛠 **Nueva solicitud de soporte**\n\n"
        f"👤 **Nombre:** {nombre}\n"
        f"🆔 **ID Telegram:** `{user_id}`\n"
        f"🔗 **Usuario:** {username}\n\n"
        f"📝 **Mensaje:**\n{texto_usuario}\n\n"
        f"📨 Para responderle use:\n`/reply {user_id} su_respuesta_aqui`"
    )

    try:
        bot.send_message(
            ADMIN_ID,
            texto_admin,
            parse_mode='Markdown'
        )
    except Exception as e:
        print("No se pudo enviar soporte al admin:", e)


@bot.message_handler(commands=['reply'])
def reply_to_user(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ No autorizado.")
        return

    partes = message.text.split(maxsplit=2)

    if len(partes) < 3:
        bot.send_message(message.chat.id, "Uso correcto:\n/reply ID_USUARIO mensaje")
        return

    try:
        user_id = int(partes[1])
    except ValueError:
        bot.send_message(message.chat.id, "❌ El ID del usuario no es válido.")
        return

    respuesta = partes[2].strip()

    if not respuesta:
        bot.send_message(message.chat.id, "❌ Debes escribir una respuesta.")
        return

    try:
        bot.send_message(
            user_id,
            f"🛠 **Respuesta de soporte**\n\n{respuesta}",
            parse_mode='Markdown'
        )
        bot.send_message(message.chat.id, f"✅ Respuesta enviada al usuario `{user_id}`.", parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ No se pudo enviar la respuesta: {e}")


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username

    db_upsert_user(user_id, {
        "telegram_username": username
    })

    mostrar_inicio_completo(message.chat.id, user_id)

@bot.message_handler(commands=['menu'])
def send_menu(message):
    mostrar_inicio_corto(message.chat.id, message.from_user.id)


@bot.message_handler(commands=['ayuda'])
def ayuda(message):
    bot.reply_to(message, "Escribe /start para volver al inicio completo o /menu para abrir el menú.")


@bot.callback_query_handler(func=lambda call: True)
def button_click(call):
    try:
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        nombre_usuario = call.from_user.first_name or "Usuario"

        if call.data == 'inicio':
            bot.answer_callback_query(call.id, "🏠 Volviendo al inicio...")
            mostrar_inicio_corto(chat_id, user_id)

        elif call.data == 'panel':
            bot.answer_callback_query(call.id, "👤 Abriendo Panel de Usuario...")
            texto_panel, markup_panel = crear_panel_usuario(user_id, nombre_usuario)
            send_screen(user_id, chat_id, texto_panel, reply_markup=markup_panel)

        elif call.data == 'configurar':
            bot.answer_callback_query(call.id, "⚙️ Configurar direcciones...")

            markup_config = InlineKeyboardMarkup(row_width=1)
            markup_config.add(
                InlineKeyboardButton("⚙️ Configurar", callback_data='seleccionar_direccion'),
                InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
            )

            texto_config = f"""**{nombre_usuario}, establece tus direcciones de crédito para confirmar pagos y recibir retiros.**

Puedes volver a configurar tus direcciones siempre que lo desees."""

            send_screen(user_id, chat_id, texto_config, reply_markup=markup_config)

        elif call.data == 'seleccionar_direccion':
            bot.answer_callback_query(call.id, "📍 Seleccionando dirección...")

            markup_direcciones = InlineKeyboardMarkup(row_width=1)
            markup_direcciones.add(
                InlineKeyboardButton("💳 Tarjeta CUP", callback_data='config_tarjeta'),
                InlineKeyboardButton("📱 Número de Móvil", callback_data='config_movil'),
                InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
            )

            send_screen(
                user_id,
                chat_id,
                "**Seleccione la dirección que desea establecer**",
                reply_markup=markup_direcciones
            )

        elif call.data == 'config_tarjeta':
            bot.answer_callback_query(call.id, "💳 Tarjeta CUP")
            send_screen(
                user_id,
                chat_id,
                "💳 **Por favor, introduce tu Tarjeta CUP**\n\n"
                "📌 Envía solo los números de la tarjeta.\n"
                "✅ Asegúrate de que esté correcta para evitar errores."
            )
            msg = bot.send_message(chat_id, "✍️ Escriba ahora su tarjeta:")
            bot.register_next_step_handler(msg, guardar_tarjeta)

        elif call.data == 'config_movil':
            bot.answer_callback_query(call.id, "📱 Número de Móvil")
            send_screen(
                user_id,
                chat_id,
                "📱 **Por favor, introduce tu número de móvil para confirmar tus pagos y recibir retiros en saldo móvil.**"
            )
            msg = bot.send_message(chat_id, "✍️ Escriba ahora su número:")
            bot.register_next_step_handler(msg, guardar_movil)

        elif call.data == 'volver_panel':
            bot.answer_callback_query(call.id, "🔙 Volviendo al Panel...")
            texto_panel, markup_panel = crear_panel_usuario(user_id, nombre_usuario)
            send_screen(user_id, chat_id, texto_panel, reply_markup=markup_panel)

        elif call.data == 'verificar':
            bot.answer_callback_query(call.id, "🔍 Verificar cajero...")

            markup_verificar = InlineKeyboardMarkup(row_width=1)
            markup_verificar.add(
                InlineKeyboardButton("👤 Panel de Usuario", callback_data='panel'),
                InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
            )

            texto_verificar = (
                f"✅ **{nombre_usuario}, ingrese su ID de cuenta en 1XBET para enviarle el mensaje de verificación**\n\n"
                "ℹ️ **En el sitio oficial de 1XBET pulse menú; encontrará el ID de su cuenta arriba a la izquierda en el botón Perfil personal.**"
            )

            try:
                send_screen(
                    user_id,
                    chat_id,
                    texto_verificar,
                    reply_markup=markup_verificar,
                    photo_path="verificar_id.jpg"
                )
            except Exception:
                send_screen(
                    user_id,
                    chat_id,
                    texto_verificar,
                    reply_markup=markup_verificar
                )

            msg = bot.send_message(chat_id, "✍️ Escriba ahora su ID de 1XBET:")
            bot.register_next_step_handler(msg, guardar_id_1xbet)

        elif call.data == 'atras':
            bot.answer_callback_query(call.id, "🔙 Volviendo al menú...")
            mostrar_inicio_corto(chat_id, user_id)

        elif call.data == 'recargar':
            bot.answer_callback_query(call.id, "💰 Recargar Cuenta")

            markup_recarga = InlineKeyboardMarkup(row_width=1)
            markup_recarga.add(
                InlineKeyboardButton("💳 Tarjeta CUP", callback_data='recarga_tarjeta'),
                InlineKeyboardButton("📱 Saldo Móvil", callback_data='recarga_saldo'),
                InlineKeyboardButton("📊 Tasas de Cambio", callback_data='tasas'),
                InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
            )

            send_screen(
                user_id,
                chat_id,
                "⚪ **Seleccione el método a utilizar para efectuar el pago de su recarga.**",
                reply_markup=markup_recarga
            )

        elif call.data == 'recarga_tarjeta':
            bot.answer_callback_query(call.id, "💳 Tarjeta CUP")

            markup_pagado = InlineKeyboardMarkup(row_width=1)
            markup_pagado.add(
                InlineKeyboardButton("✔️ He Pagado", callback_data='he_pagado_tarjeta'),
                InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
            )

            texto_tarjeta = (
                "💱 **590 CUP = 1 USD$**\n\n"
                "📊 **Rango de Depósito en CUP:**\n"
                "💳 **Tarjeta CUP**\n\n"
                "**Mín:** 590 CUP - **Máx:** 29500 CUP\n\n"
                "⏳ En breve recibirá los datos para realizar el depósito; se acreditará USD$ a su cuenta según la tasa de cambio actual.\n\n"
                "💳 **Envíe CUP a la siguiente Tarjeta**\n"
                "👇 *(Pulse el número para copiar)*\n\n"
                "`9227-9598-7978-4218`\n\n"
                "📲 **Confirmar al siguiente número**\n"
                "👇 *(Pulse el número para copiar)*\n\n"
                "`56587187`\n\n"
                "📸 Al hacer su pago por Transfermóvil, realice una captura del pago y presione **\"✔️ He Pagado\"**.\n\n"
                "🍎 Si realizó la transferencia desde iPhone, envíe también captura de la transferencia y de sus últimas operaciones, luego presione **\"✔️ He Pagado\"**.\n\n"
                "⚠️ Presione el botón únicamente después de efectuar el pago."
            )

            send_screen(
                user_id,
                chat_id,
                texto_tarjeta,
                reply_markup=markup_pagado
            )

        elif call.data == 'he_pagado_tarjeta':
            bot.answer_callback_query(call.id, "📸 Envíe el comprobante")
            send_screen(
                user_id,
                chat_id,
                "📸 **Ahora envíe la captura o comprobante del pago.**\n\n"
                "✅ Sin recortes ni tachones.\n"
                "🍎 Si usa iPhone, envíe también la captura de la transferencia y sus últimas operaciones."
            )
            msg = bot.send_message(chat_id, "📎 Envíe ahora el comprobante:")
            bot.register_next_step_handler(msg, pedir_comprobante_recarga)

        elif call.data == 'recarga_saldo':
            bot.answer_callback_query(call.id, "📱 Saldo Móvil")

            markup_pagado_saldo = InlineKeyboardMarkup(row_width=1)
            markup_pagado_saldo.add(
                InlineKeyboardButton("✔️ He Pagado", callback_data='he_pagado_saldo'),
                InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
            )

            texto_saldo = (
                "💱 **235 CUP = 1 USD$**\n\n"
                "📊 **Rango de Depósito en CUP:**\n"
                "📱 **Saldo Móvil**\n\n"
                "**Mín:** 235 CUP - **Máx:** 11750 CUP\n\n"
                "⏳ En breve recibirá los datos para realizar el depósito; se acreditará USD$ a su cuenta según la tasa de cambio actual.\n\n"
                "📱 **Envíe el saldo móvil al siguiente número**\n"
                "👇 *(Pulse el número para copiar)*\n\n"
                "`56587187`\n\n"
                "📸 Después de realizar el envío, haga una captura del comprobante y presione **\"✔️ He Pagado\"**.\n\n"
                "🍎 Si realizó el pago desde iPhone, envíe también captura de la transferencia y de sus últimas operaciones.\n\n"
                "⚠️ Presione el botón únicamente después de efectuar el pago."
            )

            send_screen(
                user_id,
                chat_id,
                texto_saldo,
                reply_markup=markup_pagado_saldo
            )

        elif call.data == 'he_pagado_saldo':
            bot.answer_callback_query(call.id, "📸 Envíe el comprobante")
            send_screen(
                user_id,
                chat_id,
                "📸 **Ahora envíe la captura o comprobante del pago por saldo móvil.**\n\n"
                "✅ Sin recortes ni tachones.\n"
                "🍎 Si usa iPhone, envíe también la captura de la transferencia y sus últimas operaciones."
            )
            msg = bot.send_message(chat_id, "📎 Envíe ahora el comprobante:")
            bot.register_next_step_handler(msg, pedir_comprobante_recarga)

        elif call.data == 'extraer':
            bot.answer_callback_query(call.id, "🏧 Extraer")

            markup_listo = InlineKeyboardMarkup(row_width=1)
            markup_listo.add(
                InlineKeyboardButton("✅ Listo", callback_data='retiro_listo'),
                InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
            )

            texto_retiro = (
                "🏧 **Proceso de retiro - Parzival Cash**\n\n"
                "📌 Entre al menú de **1XBET**.\n"
                "➡️ Pulse **Extraer / Retirar**.\n"
                "➡️ Seleccione la opción **1XBET en efectivo**.\n\n"
                "📝 Rellene los campos tal como se muestra en la imagen.\n"
                "💰 Introduzca el monto total que desea retirar.\n\n"
                "✅ Cuando termine, presione el botón **\"Listo\"**."
            )

            try:
                send_screen(
                    user_id,
                    chat_id,
                    texto_retiro,
                    reply_markup=markup_listo,
                    photo_path="retiro_paso1.jpg"
                )
            except Exception:
                send_screen(user_id, chat_id, texto_retiro, reply_markup=markup_listo)

        elif call.data == 'retiro_listo':
            bot.answer_callback_query(call.id, "📸 Continúe el proceso")

            texto_paso2 = (
                "📩 **Siguiente paso**\n\n"
                "⏳ Espere a que la revisión termine y su solicitud salga como **Aprobado**.\n\n"
                "🔵 Toque las letras azules para recibir el código.\n"
                "📸 Luego envíe aquí la captura con el código visible."
            )

            try:
                send_screen(
                    user_id,
                    chat_id,
                    texto_paso2,
                    photo_path="retiro_paso2.jpg"
                )
            except Exception:
                send_screen(user_id, chat_id, texto_paso2)

            msg = bot.send_message(
                chat_id,
                "📎 **Ahora envíe la captura del código o del retiro aprobado.**",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, recibir_captura_retiro)

        elif call.data == 'guia':
            bot.answer_callback_query(call.id, "📖 Guía para registro")
            markup_guia = InlineKeyboardMarkup(row_width=1)
            markup_guia.add(
                InlineKeyboardButton("📖 Ir al canal de guía para registro", url=GUIA_LINK),
                InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
            )
            send_screen(
                user_id,
                chat_id,
                "📖 **Hemos preparado una guía completa y paso a paso para ayudarte a registrarte correctamente en 1XBET.**\n\n"
                "🔗 Pulsa el botón de abajo para ir directo al canal de guía.",
                reply_markup=markup_guia
            )

        elif call.data == 'invita':
            bot.answer_callback_query(call.id, "🎟️ Invita y Gana")

            markup_invita = InlineKeyboardMarkup(row_width=1)
            markup_invita.add(
                InlineKeyboardButton("👥 Sistema de Afiliados", url=AFILIADOS_LINK),
                InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
            )

            texto_invita = (
                "🎁 **Invita y Gana con Parzival Cash**\n\n"
                "💸 **Utiliza nuestro sistema de afiliados y gana 10 CUP por cada usuario que se una mediante tu link de referido.**\n\n"
                "📈 Mientras más personas invites, más ganancias puedes obtener.\n"
                "🚀 Pulsa el botón de abajo para entrar al sistema de afiliados."
            )

            send_screen(
                user_id,
                chat_id,
                texto_invita,
                reply_markup=markup_invita
            )

        elif call.data == 'tasas':
            bot.answer_callback_query(call.id, "📊 Tasas de cambio")
            markup_tasas = InlineKeyboardMarkup(row_width=1)
            markup_tasas.add(
                InlineKeyboardButton("📊 Abrir canal de tasas", url=TASAS_LINK),
                InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
            )
            send_screen(
                user_id,
                chat_id,
                "📊 **Consulta aquí nuestras tasas de cambio actualizadas para depósitos y retiros.**",
                reply_markup=markup_tasas
            )

        elif call.data == 'tc':
            bot.answer_callback_query(call.id, "📜 Términos y condiciones")
            markup_tc = InlineKeyboardMarkup(row_width=1)
            markup_tc.add(
                InlineKeyboardButton("📜 Abrir Términos y Condiciones", url=TC_LINK),
                InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
            )
            send_screen(
                user_id,
                chat_id,
                "📜 **Aquí puede consultar las condiciones oficiales del servicio Parzival Cash.**",
                reply_markup=markup_tc
            )

        elif call.data == 'soporte':
            bot.answer_callback_query(call.id, "🛠️ Soporte")
            send_screen(
                user_id,
                chat_id,
                "🛠️ **Soporte Parzival Cash**\n\n"
                "Escriba su problema, duda o queja con el mayor detalle posible.\n\n"
                "📨 Su mensaje será enviado directamente al administrador."
            )
            msg = bot.send_message(chat_id, "✍️ Escriba ahora su mensaje de soporte:")
            bot.register_next_step_handler(msg, recibir_soporte)

        elif call.data == 'grupo':
            bot.answer_callback_query(call.id, "💬 Grupo de Chat")
            markup_grupo = InlineKeyboardMarkup(row_width=1)
            markup_grupo.add(
                InlineKeyboardButton("💬 Entrar al grupo de chat", url=GRUPO_LINK),
                InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
            )
            send_screen(
                user_id,
                chat_id,
                "💬 **Únase a nuestra comunidad oficial para compartir experiencias, resolver dudas y mantenerse activo.**",
                reply_markup=markup_grupo
            )

        elif call.data == 'canal':
            bot.answer_callback_query(call.id, "📢 Canal de Información")
            markup_canal = InlineKeyboardMarkup(row_width=1)
            markup_canal.add(
                InlineKeyboardButton("📢 Abrir canal de información", url=CANAL_LINK),
                InlineKeyboardButton("🏠 Inicio", callback_data='inicio')
            )
            send_screen(
                user_id,
                chat_id,
                "📢 **Acceda a nuestro canal oficial para recibir promociones, partidos destacados, concursos y novedades.**",
                reply_markup=markup_canal
            )

        elif call.data.startswith("aprobar_") and not call.data.startswith("aprobar_recarga_") and not call.data.startswith("aprobar_retiro_"):
            admin_id = call.from_user.id

            if admin_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ No autorizado.")
                return

            user_id_aprobado = int(call.data.split("_")[1])

            # 🔥 NUEVO: comprobar si hay solicitud pendiente
            if user_id_aprobado not in pending_xbet_requests:
                bot.answer_callback_query(call.id, "⚠️ No hay solicitud pendiente.")
                return

            xbet_id = pending_xbet_requests[user_id_aprobado]["xbet_id"]

            db_upsert_user(user_id_aprobado, {"xbet_id": xbet_id})

            if user_id_aprobado not in user_data:
                user_data[user_id_aprobado] = {}

            user_data[user_id_aprobado]['cuenta_1xbet'] = xbet_id

            del pending_xbet_requests[user_id_aprobado]

            bot.answer_callback_query(call.id, "✅ Verificación aprobada")

            try:
                bot.send_message(
                    user_id_aprobado,
                    f"✅ **Su verificación ha sido aprobada correctamente.**\n\n"
                    f"🎮 **ID 1XBET:** `{xbet_id}`\n\n"
                    "📨 Ya puede continuar utilizando el servicio.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

            try:
                bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    reply_markup=None
                )
            except Exception:
                pass

            bot.send_message(
                chat_id,
                f"✅ Verificación aprobada para el usuario `{user_id_aprobado}`.",
                parse_mode='Markdown'
            )

        elif call.data.startswith("rechazar_") and not call.data.startswith("rechazar_recarga_") and not call.data.startswith("rechazar_retiro_"):
            admin_id = call.from_user.id

            if admin_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ No autorizado.")
                return

            user_id_rechazado = int(call.data.split("_")[1])

            # Eliminar solicitud pendiente si existe
            if user_id_rechazado in pending_xbet_requests:
                del pending_xbet_requests[user_id_rechazado]

            bot.answer_callback_query(call.id, "❌ Verificación rechazada")

            try:
                bot.send_message(
                    user_id_rechazado,
                    "❌ **Su verificación no fue aprobada.**\n\n"
                    "📌 Revise sus datos y vuelva a intentarlo o contacte con soporte.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

            try:
                bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    reply_markup=None
                )
            except Exception:
                pass

            bot.send_message(
                chat_id,
                f"❌ Verificación rechazada para el usuario `{user_id_rechazado}`.",
                parse_mode='Markdown'
            )
        elif call.data.startswith("aprobar_recarga_"):
            admin_id = call.from_user.id

            if admin_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ No autorizado.")
                return

            recharge_id = call.data.replace("aprobar_recarga_", "")

            if recharge_id not in pending_recharges:
                bot.answer_callback_query(call.id, "❌ Solicitud no encontrada.")
                return

            solicitud = pending_recharges[recharge_id]

            if solicitud["status"] != "pendiente":
                bot.answer_callback_query(call.id, "⚠️ Esta solicitud ya fue procesada.")
                return

            solicitud["status"] = "aprobada"
            bot.answer_callback_query(call.id, "✅ Recarga aprobada")

            try:
                bot.send_message(
                    solicitud["user_id"],
                    "✅ **Listo, su cuenta ha sido recargada exitosamente.**\n\n"
                    "🎮 Revise su cuenta de **1XBET**.\n"
                    "🙏 Gracias por elegir Parzival Cash.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
            except Exception:
                pass

            bot.send_message(chat_id, f"✅ Recarga aprobada para el usuario `{solicitud['user_id']}`.", parse_mode='Markdown')

        elif call.data.startswith("rechazar_recarga_"):
            admin_id = call.from_user.id

            if admin_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ No autorizado.")
                return

            recharge_id = call.data.replace("rechazar_recarga_", "")

            if recharge_id not in pending_recharges:
                bot.answer_callback_query(call.id, "❌ Solicitud no encontrada.")
                return

            solicitud = pending_recharges[recharge_id]

            if solicitud["status"] != "pendiente":
                bot.answer_callback_query(call.id, "⚠️ Esta solicitud ya fue procesada.")
                return

            solicitud["status"] = "rechazada"
            bot.answer_callback_query(call.id, "❌ Recarga rechazada")

            try:
                bot.send_message(
                    solicitud["user_id"],
                    "❌ **No fue posible validar su pago.**\n\n"
                    "📸 Revise el comprobante enviado o contacte con soporte para continuar.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
            except Exception:
                pass

            bot.send_message(chat_id, f"❌ Recarga rechazada para el usuario `{solicitud['user_id']}`.", parse_mode='Markdown')

        elif call.data.startswith("aprobar_retiro_"):
            admin_id = call.from_user.id

            if admin_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ No autorizado.")
                return

            withdrawal_id = call.data.replace("aprobar_retiro_", "")

            if withdrawal_id not in pending_withdrawals:
                bot.answer_callback_query(call.id, "❌ Solicitud no encontrada.")
                return

            solicitud = pending_withdrawals[withdrawal_id]

            if solicitud["status"] != "revision":
                bot.answer_callback_query(call.id, "⚠️ Esta solicitud ya fue procesada.")
                return

            solicitud["status"] = "aprobado"
            bot.answer_callback_query(call.id, "✅ Retiro aprobado")

            markup_metodo = InlineKeyboardMarkup(row_width=1)
            markup_metodo.add(
                InlineKeyboardButton("💳 Tarjeta CUP", callback_data=f"metodo_tarjeta_{withdrawal_id}"),
                InlineKeyboardButton("📱 Saldo Móvil", callback_data=f"metodo_movil_{withdrawal_id}")
            )

            try:
                bot.send_message(
                    solicitud["user_id"],
                    "✅ **Retiro exitoso**\n\n"
                    "💱 Su retiro se efectuará con la misma moneda del depósito.\n"
                    "📌 Seleccione cómo desea recibir su dinero:",
                    reply_markup=markup_metodo,
                    parse_mode='Markdown'
                )
            except Exception:
                pass

            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
            except Exception:
                pass

            bot.send_message(chat_id, f"✅ Retiro aprobado para el usuario `{solicitud['user_id']}`.", parse_mode='Markdown')

        elif call.data.startswith("rechazar_retiro_"):
            admin_id = call.from_user.id

            if admin_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ No autorizado.")
                return

            withdrawal_id = call.data.replace("rechazar_retiro_", "")

            if withdrawal_id not in pending_withdrawals:
                bot.answer_callback_query(call.id, "❌ Solicitud no encontrada.")
                return

            solicitud = pending_withdrawals[withdrawal_id]

            if solicitud["status"] != "revision":
                bot.answer_callback_query(call.id, "⚠️ Esta solicitud ya fue procesada.")
                return

            solicitud["status"] = "rechazado"
            bot.answer_callback_query(call.id, "❌ Retiro rechazado")

            try:
                bot.send_message(
                    solicitud["user_id"],
                    "❌ **Su solicitud de retiro no pudo ser aprobada.**\n\n"
                    "📌 Revise la información enviada o contacte con soporte.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
            except Exception:
                pass

            bot.send_message(chat_id, f"❌ Retiro rechazado para el usuario `{solicitud['user_id']}`.", parse_mode='Markdown')

        elif call.data.startswith("metodo_tarjeta_"):
            withdrawal_id = call.data.replace("metodo_tarjeta_", "")

            if withdrawal_id not in pending_withdrawals:
                bot.answer_callback_query(call.id, "❌ Solicitud no encontrada.")
                return

            solicitud = pending_withdrawals[withdrawal_id]
            solicitud["metodo"] = "tarjeta"

            bot.answer_callback_query(call.id, "💳 Tarjeta seleccionada")

            try:
                bot.send_message(
                    solicitud["user_id"],
                    "💳 **Pago por tarjeta seleccionado**\n\n"
                    "⏳ En breve le llegará su dinero a la tarjeta registrada.\n"
                    "🙏 Gracias por confiar en Parzival Cash.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

            markup_admin_pago = InlineKeyboardMarkup(row_width=2)
            markup_admin_pago.add(
                InlineKeyboardButton("✅ Dinero enviado", callback_data=f"enviado_tarjeta_{withdrawal_id}"),
                InlineKeyboardButton("❌ Cancelar", callback_data=f"cancelar_pago_{withdrawal_id}")
            )

            bot.send_message(
                ADMIN_ID,
                f"💳 **Enviar dinero por TARJETA**\n\n"
                f"🆔 Solicitud: {withdrawal_id}\n"
                f"👤 Usuario: {solicitud['name']}\n"
                f"🆔 ID Telegram: {solicitud['user_id']}\n"
                f"💳 Tarjeta registrada: {solicitud['tarjeta_usuario']}",
                reply_markup=markup_admin_pago,
                parse_mode='Markdown'
            )

        elif call.data.startswith("metodo_movil_"):
            withdrawal_id = call.data.replace("metodo_movil_", "")

            if withdrawal_id not in pending_withdrawals:
                bot.answer_callback_query(call.id, "❌ Solicitud no encontrada.")
                return

            solicitud = pending_withdrawals[withdrawal_id]
            solicitud["metodo"] = "movil"

            bot.answer_callback_query(call.id, "📱 Saldo móvil seleccionado")

            try:
                bot.send_message(
                    solicitud["user_id"],
                    "📱 **Pago por saldo móvil seleccionado**\n\n"
                    "⏳ En breve le llegará su dinero al saldo móvil principal.\n"
                    "🙏 Gracias por confiar en Parzival Cash.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

            markup_admin_pago = InlineKeyboardMarkup(row_width=2)
            markup_admin_pago.add(
                InlineKeyboardButton("✅ Dinero enviado", callback_data=f"enviado_movil_{withdrawal_id}"),
                InlineKeyboardButton("❌ Cancelar", callback_data=f"cancelar_pago_{withdrawal_id}")
            )

            bot.send_message(
                ADMIN_ID,
                f"📱 **Enviar dinero por SALDO MÓVIL**\n\n"
                f"🆔 Solicitud: {withdrawal_id}\n"
                f"👤 Usuario: {solicitud['name']}\n"
                f"🆔 ID Telegram: {solicitud['user_id']}\n"
                f"📱 Móvil registrado: {solicitud['movil_usuario']}",
                reply_markup=markup_admin_pago,
                parse_mode='Markdown'
            )

        elif call.data.startswith("enviado_tarjeta_"):
            admin_id = call.from_user.id

            if admin_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ No autorizado.")
                return

            withdrawal_id = call.data.replace("enviado_tarjeta_", "")

            if withdrawal_id not in pending_withdrawals:
                bot.answer_callback_query(call.id, "❌ Solicitud no encontrada.")
                return

            solicitud = pending_withdrawals[withdrawal_id]
            solicitud["status"] = "pagado_tarjeta"

            bot.answer_callback_query(call.id, "✅ Pago enviado por tarjeta")

            try:
                bot.send_message(
                    solicitud["user_id"],
                    "✅ **El dinero ha sido enviado a su tarjeta.**\n\n"
                    "💳 Por favor revise su tarjeta.\n"
                    "🙏 Gracias por elegir **Parzival Cash**.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
            except Exception:
                pass

        elif call.data.startswith("enviado_movil_"):
            admin_id = call.from_user.id

            if admin_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ No autorizado.")
                return

            withdrawal_id = call.data.replace("enviado_movil_", "")

            if withdrawal_id not in pending_withdrawals:
                bot.answer_callback_query(call.id, "❌ Solicitud no encontrada.")
                return

            solicitud = pending_withdrawals[withdrawal_id]
            solicitud["status"] = "pagado_movil"

            bot.answer_callback_query(call.id, "✅ Pago enviado por saldo móvil")

            try:
                bot.send_message(
                    solicitud["user_id"],
                    "✅ **El dinero ha sido enviado a su saldo móvil principal.**\n\n"
                    "📱 Por favor revise su saldo.\n"
                    "🙏 Gracias por elegir **Parzival Cash**.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
            except Exception:
                pass

        elif call.data.startswith("cancelar_pago_"):
            admin_id = call.from_user.id

            if admin_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ No autorizado.")
                return

            withdrawal_id = call.data.replace("cancelar_pago_", "")

            if withdrawal_id not in pending_withdrawals:
                bot.answer_callback_query(call.id, "❌ Solicitud no encontrada.")
                return

            solicitud = pending_withdrawals[withdrawal_id]

            bot.answer_callback_query(call.id, "❌ Pago cancelado")

            try:
                bot.send_message(
                    solicitud["user_id"],
                    "❌ **Su pago aún no ha sido procesado.**\n\n"
                    "📌 Si necesita ayuda, contacte con soporte.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
            except Exception:
                pass

        else:
            bot.answer_callback_query(call.id, "✅ Opción seleccionada")

    except Exception as e:
        print("Error en button_click:", repr(e))
        try:
            bot.send_message(call.message.chat.id, f"❌ Error interno: {e}")
        except Exception:
            pass


print("✅ Bot Parzival Cash iniciado correctamente. Esperando mensajes...")
bot.set_my_commands([
    BotCommand("start", "Iniciar el bot"),
])
bot.polling(none_stop=True)
