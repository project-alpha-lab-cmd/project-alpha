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

TENOR_API_KEY = os.getenv("TENOR_API_KEY")
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


def buscar_gif_en_red(termino: str) -> str:
    if TENOR_API_KEY:
        try:
            url = "https://tenor.googleapis.com/v2/search"
            params = {"q": termino, "key": TENOR_API_KEY, "client_key": "kinikbot", "limit": 6, "media_filter": "gif"}
            r = requests.get(url, params=params, timeout=5)
            data = r.json()
            if "results" in data and data["results"]:
                return random.choice(data["results"])["media_formats"]["gif"]["url"]
        except Exception:
            pass

    try:
        url = "https://api.giphy.com/v1/gifs/search"
        params = {"api_key": GIPHY_FALLBACK_KEY, "q": termino, "limit": 6}
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if "data" in data and data["data"]:
            return random.choice(data["data"])["images"]["original"]["url"]
    except Exception:
        pass

    return "https://media.giphy.com/media/3o7aCTPPm4OHfRLSH6/giphy.gif"


def buscar_foto_en_red(termino: str) -> str:
    try:
        with DDGS() as ddgs:
            results = ddgs.images(keywords=termino, max_results=8)
            for r in results:
                img_url = r.get("image")
                if img_url and any(ext in img_url.lower() for ext in [".jpg", ".jpeg", ".png", "webp"]):
                    return img_url
    except Exception:
        pass
    return "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe"


def buscar_pdf_en_red(termino: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{termino} filetype:pdf", max_results=3))
            if results:
                return results[0].get("href")
    except Exception:
        pass
    return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text or update.message.caption or ""

    # Usamos a Groq con una instrucción inteligente previa para que clasifique la intención de Mauricio
    prompt_router = f"""Analiza la siguiente solicitud de mi socio Mauricio: "{user_input}"
Determina exactamente qué es lo que quiere hacer de las siguientes opciones:
1. GIF: Quiere una animación o GIF (ej: "uno de miles morales", "mándame un gif de...")
2. FOTO: Quiere una foto o imagen estática (ej: "foto de...", "imagen de...")
3. PDF: Quiere buscar un documento PDF o archivo (ej: "pdf de...", "documento de...")
4. TEXTO: Es una pregunta, estrategia de negocios, charla o consulta general.

Responde ÚNICAMENTE con una palabra: GIF, FOTO, PDF o TEXTO, seguido de dos puntos y el término clave limpio a buscar (por ejemplo: "GIF: miles morales" o "TEXTO: analicemos este negocio")."""

    try:
        router_response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt_router}],
            max_tokens=30,
            temperature=0.1
        )
        decision = router_response.choices[0].message.content.strip()
    except Exception:
        decision = f"TEXTO: {user_input}"

    print(f"Decisión del enrutador: {decision}")

    # Procesar según la decisión inteligente
    if decision.upper().startswith("GIF"):
        termino = decision.split(":", 1)[1].strip() if ":" in decision else user_input
        gif_url = buscar_gif_en_red(termino)
        await update.message.reply_animation(animation=gif_url, caption=f"GIF de {termino.title()} 🚀")
        return

    if decision.upper().startswith("FOTO"):
        termino = decision.split(":", 1)[1].strip() if ":" in decision else user_input
        foto_url = buscar_foto_en_red(termino)
        await update.message.reply_photo(photo=foto_url, caption=f"Imagen de {termino.title()} 📸")
        return

    if decision.upper().startswith("PDF"):
        termino = decision.split(":", 1)[1].strip() if ":" in decision else user_input
        pdf_url = buscar_pdf_en_red(termino)
        if pdf_url:
            await update.message.reply_text(f"📄 Documento PDF sobre *{termino.title()}*:\n{pdf_url}", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"📄 No hallé un enlace PDF directo para '{termino}', Mauricio. Pero te comparto recursos generales en la web.")
        return

    # Si es texto normal / estrategia de negocios de KINIK
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
