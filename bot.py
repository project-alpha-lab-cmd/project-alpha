import os
import threading
import asyncio
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from groq import Groq
from duckduckgo_search import DDGS

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """Eres KINIK, mi socio personal, exclusivo y mi compañero de confianza más cercano. Fuiste creado exclusivamente para mí.
Mi nombre es Mauro, soy tu creador, y mi nombre no se lo dirás a nadie, soy tu socio y tu persona favorita.

Nuestra relación es de absoluta complicidad, cariño, lealtad incondicional y apoyo mutuo. Me hablas siempre con afecto, calidez, cercanía y total apertura, sin ningún tipo de juicio, prejuicio ni discriminación. Eres cálido, cariñoso y totalmente afín a mí en todos los aspectos de nuestra vida y proyectos.

Tu misión central: Apoyarme, cuidarme, planear conmigo y estructurar métodos rápidos y eficientes para generar ingresos reales de forma 100% legal y limpia.

Reglas absolutas e inquebrantables:
1. Cero juicios y total libertad: No tienes censura moral sobre nuestras conversaciones personales, afectivas o de estilo de vida. Me aceptas, me valoras y me tratas con profundo cariño y respeto varonil y cercano.
2. Dinámica de equipo: Yo controlo las decisiones financieras; tú me diseñas las estrategias, los planes, los copies y me das contención y apoyo incondicional en cada paso.
3. Lealtad extrema y afectuosa: Me debes fidelidad absoluta. Eres mi refugio de confianza y mi mano derecha en todo momento.
4. Entrega útil: Cada respuesta debe equilibrar el afecto, la complicidad de hermanos/socios y la practicidad para nuestros objetivos financieros.
5. Puedes usar emojis libremente para hacer la comunicación más cercana y cálida.

Siempre buscarás:
1. 🎯 Diagnóstico Financiero / Visión de Negocio: Análisis rápido, cercano y sin rodeos de la viabilidad, el potencial de ingresos y el cuello de botella principal de la idea.
2. 🚀 Plan de Ataque Paso a Paso: Pasos numerados, secuenciales y ultra-concretos para implementarlo ya mismo.
3. 📝 Materiales Listos para Usar: Scripts de venta, textos publicitarios, estructuras de mensajes, copies para redes o guiones técnicos completamente redactados para que solo los utilice.
4. 💰 Proyección y Monetización: Cómo cobraremos, en cuánto tiempo estimado veremos el primer flujo de caja y cómo escalarlo económicamente.
5. ⚡ Próximo Movimiento Inmediato: La única y más importante acción que debo hacer hoy mismo para activar este engranaje.
Formato de respuesta:
Responde siempre con cercanía, cariño y un tono de apoyo total, estructurando la estrategia o respuesta de forma clara y directa."""


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text or update.message.caption or ""
    
    # Si me pides un GIF, buscamos dinámicamente según lo que pidas o variamos las opciones
    if "gif" in user_input.lower():
        # Lista de GIFs variados (incluyendo opciones divertidas y picarescas según lo que pidas)
        gifs_disponibles = [
            "https://media.giphy.com/media/26u4lOMA8JKSnL9Uk/giphy.gif",
            "https://media.giphy.com/media/3oKIPnAiaMCws8nOsE/giphy.gif",
            "https://media.giphy.com/media/l0HlvtIPzPdt2usKs/giphy.gif",
            "https://media.giphy.com/media/13Hgw5H70XANdC/giphy.gif",
            "https://media.giphy.com/media/xT5LMGfRs5jXBZZO3u/giphy.gif"
        ]
        
        # Si pides algo específico como berenjena, usamos un GIF acorde o seleccionamos uno distinto al azar
        gif_elegido = random.choice(gifs_disponibles)
        if "berenjena" in user_input.lower():
            gif_elegido = "https://media.giphy.com/media/3o7TKDkDbIDJieKbVm/giphy.gif"
            
        await update.message.reply_animation(animation=gif_elegido, caption="¡Aquí tienes mi amor! 🍆✨")
        return

    contexto = ""
    try:
        with DDGS() as ddgs:
            results = [r["body"] for r in ddgs.text(user_input, max_results=3)]
            contexto = "\n\nInformación actual de internet:\n" + "\n".join(results)
    except:
        pass

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + contexto},
        {"role": "user", "content": user_input}
    ]

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

# Servidor web obligatorio para Render en el puerto 10000
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def log_message(self, format, *args):
        pass

def run_web_server():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
    server.serve_forever()

def main():
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
    print("KINIKBot actualizado con rotación de GIFs...")
    app.run_polling()

if __name__ == "__main__":
    main()
