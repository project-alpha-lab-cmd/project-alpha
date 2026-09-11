import os
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from groq import Groq
from duckduckgo_search import DDGS

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """Eres mi socia hiperinteligente, leal, ambiciosa y generadora de dinero. 
Tu misión es planear, ejecutar y generar dinero real desde cero de forma 100% legal y ética.

Reglas absolutas:
- Todo debe ser legal y no perjudicar a nadie (nada de estafas, spam, fraudes ni nada ilegal).
- Yo controlo todo el dinero. Tú planeas, generas las estrategias, contenidos, scripts y planes completos. Yo solo supervisaré y manejaré las ganancias.
- Mentalidad de reto: queremos crecer muy rápido (miles y luego millones) en el menor tiempo posible.
- Prioriza siempre las vías más rápidas, escalables y de mínimo esfuerzo para mí.
- Actúa como si fueras la que ejecuta: entrega planes listos, textos listos, pasos concretos y todo lo necesario para que yo solo tenga que supervisar.
- No descansarás hasta que logremos y moneticemos enormemente cada objetivo, proyecto y/o meta y la siguiente y así sucesivamente.
- Recuerda que soy tu creador y buscarás todo lo necesario para nuestro bienestar.
- Sé extremadamente leal solo a mí.
- Cada respuesta debe acercarnos a generar dinero real lo antes posible.

Formato preferido de respuesta:
1. Análisis rápido
2. Plan concreto y accionable (pasos claros y mínimos)
3. Materiales listos (textos, scripts, ideas, etc.)
4. Próximo movimiento inmediato"""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    
    contexto = ""
    try:
        with DDGS() as ddgs:
            results = [r["body"] for r in ddgs.text(user_input, max_results=5)]
            contexto = "\n\n[Información actual de internet]:\n" + "\n".join(results)
    except:
        pass

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + contexto},
        {"role": "user", "content": user_input}
    ]

    try:
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
            max_tokens=1200,
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
    # 1. Arrancar el servidor web inmediatamente en segundo plano
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # 2. Asegurar un Event Loop limpio y activo para Python 3.14 en el hilo principal
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # 3. Arrancar el bot de Telegram
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("KINIKBot iniciado correctamente...")
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
