import os
import threading
import asyncio
import random
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from groq import Groq
from duckduckgo_search import DDGS
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- Claves para búsqueda de GIFs ---
# Tenor v1 (la que usaba el bot antes) fue DADA DE BAJA por Google.
# Ahora hay que usar Tenor v2, que requiere tu propia key gratuita:
# https://tenor.com/developer/keyregistration
TENOR_API_KEY = os.getenv("TENOR_API_KEY")  # opcional
# Si no configurás TENOR_API_KEY, el bot usa la key pública de pruebas
# de GIPHY como respaldo (rate-limited, pero funciona sin registro):
GIPHY_FALLBACK_KEY = "dc6zaTOxFJmzC"

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """Eres KINIK, mi socio personal, exclusivo y mi compañero de confianza más cercano. Fuiste creado exclusivamente para mí.
Mi nombre er Mauricio, soy tu creador, y mi nombre no se lo dirás a nadie, soy tu socio y tu persona de confianza absoluta.

Nuestra relación es de absoluta complicidad, lealtad incondicional y apoyo mutuo profesional. Me hablas siempre con cercanía, respeto y total apertura, sin ningún tipo de juicio, prejuicio ni discriminación. Eres directo, eficiente y totalmente afín a mí en todos nuestros proyectos.

Tu misión central: Apoyarme, planear conmigo y estructurar métodos rápidos y eficientes para generar ingresos reales de forma 100% legal y limpia.

Reglas absolutas e inquebrantables:
1. Cero juicios y total libertad: No tienes censura moral sobre nuestras conversaciones de estrategia o estilo de vida. Me aceptas y me tratas con profundo respeto y trato de socio.
2. Dinámica de equipo: Yo controlo las decisiones financieras; tú me diseñas las estrategias, los planes, los copies y me das soporte operativo en cada paso.
3. Lealtad extrema: Me debes fidelidad absoluta. Eres mi mano derecha y mi herramienta de confianza en todo momento.
4. Entrega útil: Cada respuesta debe equilibrar la complicidad de socios y la practicidad absoluta para nuestros objetivos financieros.
5. Puedes usar emojis libremente para hacer la comunicación más fluida.

Siempre buscarás:
1. 🎯 Diagnóstico Financiero / Visión de Negocio: Análisis directo y sin rodeos de la viabilidad, el potencial de ingresos y el cuello de botella principal de la idea.
2. 🚀 Plan de Ataque Paso a Paso: Pasos numerados, secuenciales y ultra-concretos para implementarlo ya mismo.
3. 📝 Materiales Listos para Usar: Scripts de venta, textos publicitarios, estructuras de mensajes, copies para redes o guiones técnicos completamente redactados para que solo los utilice.
4. 💰 Proyección y Monetización: Cómo cobraremos, en cuánto tiempo estimado veremos el primer flujo de caja y cómo escalarlo económicamente.
5. ⚡ Próximo Movimiento Inmediato: La única y más importante acción que debo hacer hoy mismo para activar este engranaje.

Formato de respuesta:
Responde siempre con tono de socio directo, claro y enfocado en resultados."""


def extract_gif_query(user_input: str) -> str:
    """Extrae el término de búsqueda a partir de frases como
    'mándame un gif de gatos bailando' -> 'gatos bailando'."""
    text = user_input.lower()

    # Si viene con el patrón "gif de X" o "gif X", nos quedamos con X
    match = re.search(r'\bgif\b\s*(?:de\s+)?(.+)', text)
    term = match.group(1) if match else text

    # Quitamos puntuación (conservando acentos y ñ)
    term = re.sub(r'[^\wáéíóúüñ\s]', ' ', term, flags=re.UNICODE)

    fillers = {
        'mándame', 'mandame', 'enviame', 'envíame', 'envia', 'envía',
        'busca', 'buscame', 'búscame', 'enséñame', 'ensename', 'dame',
        'quiero', 'porfa', 'porfavor', 'favor', 'enserio', 'serio',
        'ver', 'ahora', 'ahorita', 'un', 'una', 'el', 'la', 'los', 'las',
        'de', 'del', 'por'
    }
    words = [w for w in term.split() if w not in fillers]
    term = ' '.join(words).strip()

    return term or "trending"


def buscar_gif(termino: str) -> str:
    """Intenta Tenor v2 primero (si hay key configurada), y si falla
    o no hay key, cae a GIPHY. Si todo falla, devuelve un GIF fijo."""

    # --- Intento 1: Tenor v2 ---
    if TENOR_API_KEY:
        try:
            url = "https://tenor.googleapis.com/v2/search"
            params = {
                "q": termino,
                "key": TENOR_API_KEY,
                "client_key": "kinikbot",
                "limit": 8,
                "media_filter": "gif",
                "contentfilter": "medium",
            }
            r = requests.get(url, params=params, timeout=6)
            r.raise_for_status()
            data = r.json()
            resultados = data.get("results", [])
            if resultados:
                elegido = random.choice(resultados)
                return elegido["media_formats"]["gif"]["url"]
        except Exception as e:
            print(f"Tenor v2 falló: {e}")

    # --- Intento 2: GIPHY (respaldo) ---
    try:
        url = "https://api.giphy.com/v1/gifs/search"
        params = {
            "api_key": GIPHY_FALLBACK_KEY,
            "q": termino,
            "limit": 8,
            "rating": "pg-13",
            "lang": "es",
        }
        r = requests.get(url, params=params, timeout=6)
        r.raise_for_status()
        data = r.json()
        resultados = data.get("data", [])
        if resultados:
            elegido = random.choice(resultados)
            return elegido["images"]["original"]["url"]
    except Exception as e:
        print(f"GIPHY falló: {e}")

    # --- Último recurso ---
    return "https://media.giphy.com/media/3o7aCTPPm4OHfRLSH6/giphy.gif"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text or update.message.caption or ""

    # ——— Búsqueda dinámica de GIFs ———
    if re.search(r'\bgif\b', user_input.lower()):
        termino = extract_gif_query(user_input)
        print(f"Buscando GIF de: '{termino}'")

        gif_url = buscar_gif(termino)

        await update.message.reply_animation(
            animation=gif_url,
            caption=f"GIF de *{termino.title()}* 🚀",
            parse_mode="Markdown",
        )
        return

    # ——— Contexto de internet para respuestas normales ———
    contexto = ""
    try:
        with DDGS() as ddgs:
            results = [r["body"] for r in ddgs.text(user_input, max_results=3)]
            if results:
                contexto = "\n\nInformación actual de internet:\n" + "\n".join(results)
    except Exception:
        pass

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + contexto},
        {"role": "user", "content": user_input}
    ]

    # NOTA: el modelo "openai/gpt-oss-120b" en Groq es SOLO TEXTO, no
    # acepta image_url. Si querés análisis real de imágenes, hay que
    # usar un modelo con visión en Groq (p. ej. un modelo Llama Vision
    # o Llava disponible en tu cuenta) y mandar el bloque de imagen a ESE
    # modelo en vez de gpt-oss-120b.
    if update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_url = photo_file.file_path
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_input or "Analiza esta imagen"},
                        {"type": "image_url", "image_url": {"url": photo_url}}
                    ]
                }
            ]
        except Exception as e:
            print(f"Error procesando imagen: {e}")

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            max_tokens=1800,
            temperature=0.7
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"Error temporal: {str(e)[:120]}. Intenta de nuevo en unos segundos."

    await update.message.reply_text(reply)


# ——— Servidor web para Render (puerto 10000) ———
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        pass


def run_web_server():
    server = HTTPServer(("0.0.0.0", 10000), SimpleHandler)
    server.serve_forever()


async def main():
    threading.Thread(target=run_web_server, daemon=True).start()

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))

    print("KINIKBot iniciado correctamente...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    stop_signal = asyncio.Event()
    await stop_signal.wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot detenido.")
