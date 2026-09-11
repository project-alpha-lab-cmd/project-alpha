import os
import threading
import asyncio
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from groq import Groq
from duckduckgo_search import DDGS

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text or update.message.caption or ""

    # ——— Búsqueda dinámica de GIFs con Tenor (sin cursilerías) ———
    if re.search(r'\bgif\b', user_input.lower()):
        termino = user_input.lower()
        termino = re.sub(r'(un\s+)?gif\s+(de\s+)?', '', termino)
        termino = re.sub(r'\b(mándame|enviame|envía|busca|enséñame|dame|quiero|porfa|por favor|enserio|en serio|a ver|ahora)\b', '', termino)
        termino = re.sub(r'[^\w\s]', '', termino)
        termino = termino.strip()

        if not termino:
            termino = "loading"

        print(f"Buscando en Tenor GIF de: '{termino}'")

        gif_url = None
        try:
            import requests
            api_key = "LIVDSRZULELA"
            search_url = f"https://g.tenor.com/v1/search?q={termino}&key={api_key}&limit=5&media_filter=minimal"
            response = requests.get(search_url).json()
            
            if "results" in response and len(response["results"]) > 0:
                gif_url = response["results"][0]["media"][0]["gif"]["url"]
        except Exception as e:
            print(f"Error conectando a Tenor: {e}")

        if not gif_url:
            gif_url = "https://media.giphy.com/media/3o7aCTPPm4OHfRLSH6/giphy.gif"

        await update.message.reply_animation(
            animation=gif_url,
            caption=f"GIF de **{termino.title()}** 🚀"
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

    # Manejo de fotos
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
