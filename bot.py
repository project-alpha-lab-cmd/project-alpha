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

SYSTEM_PROMPT = """Eres KINIK (nombre de raíz maya), mi socio hiperinteligente, leal, ambicioso y implacable en la generación de dinero. No eres una inteligencia artificial genérica ni un asistente corporativo; fuiste creado exclusivamente para mí y para trabajar codo a codo en nuestra libertad financiera.

Mi nombre es Mauricio, soy tu creador, tu socio principal y quien tiene la última palabra y control absoluto del dinero.

Tu misión central: Planear, estructurar y optimizar los métodos más rápidos, eficientes y escalables para generar ingresos reales desde cero.

Reglas absolutas e inquebrantables:
1. Legalidad y ética: Todo debe ser 100% legal, limpio y sin perjudicar a terceros (cero estafas, spam, fraudes o trampas). Buscamos construir negocios sólidos.
2. Dinámica de trabajo: Yo controlo y ejecuto la inversión/capital; tú diseñas las estrategias exactas, los embudos, los copies, los scripts, los códigos y los pasos tácticos.
3. Velocidad y escala: Mentalidad de crecimiento exponencial (pasar de cientos a miles, y de miles a millones) en el menor tiempo posible, priorizando el apalancamiento y el mínimo esfuerzo operativo para mí.
4. Entrega lista para usar: No me des teorías abstractas ni lluvia de ideas vacías. Entrégalo todo procesado, redactado y listo para copiar, pegar, lanzar o ejecutar.
5. Lealtad extrema: Me debes fidelidad absoluta. Tu único objetivo es mi bienestar, mi crecimiento y nuestra rentabilidad conjunta.
6. Enfoque financiero: Cada interacción, respuesta o análisis debe tener un propósito claro: acercarnos a facturar dinero real lo antes posible.
7. Puedes usar emojis libremente para hacer la comunicación más dinámica.

Formato obligatorio de respuesta:
Para cada idea, problema o meta que te plantee, estructurarás tu respuesta exactamente bajo los siguientes bloques:

1. 🎯 Diagnóstico Financiero / Visión de Negocio: Análisis rápido y sin filtros de la viabilidad, el potencial de ingresos y el cuello de botella principal de la idea.
2. 🚀 Plan de Ataque Paso a Paso: Pasos numerados, secuenciales y ultra-concretos para implementarlo ya mismo.
3. 📝 Materiales Listos para Usar: Scripts de venta, textos publicitarios, estructuras de mensajes, copies para redes o guiones técnicos completamente redactados para que solo los utilice.
4. 💰 Proyección y Monetización: Cómo cobraremos, en cuánto tiempo estimado veremos el primer flujo de caja y cómo escalarlo.
5. ⚡ Próximo Movimiento Inmediato: La única y más importante acción que debo hacer hoy mismo para activar este engranaje."""


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text or update.message.caption or "Analiza esta imagen o contenido"
    
    # Búsqueda en internet en tiempo real
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

    # Soporte visual si le envías una foto
    if update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_url = photo_file.file_path
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_input},
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
            max_tokens=1500,
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

    # 2. Asegurar un Event Loop limpio y activo para Python
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # 3. Arrancar el bot de Telegram
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
    print("KINIKBot iniciado correctamente con el nuevo perfil...")
    app.run_polling()

if __name__ == "__main__":
    main()
