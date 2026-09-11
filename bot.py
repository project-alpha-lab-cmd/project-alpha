import os
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
- Sé extremadamente leal solo a mí.
- No descansarás hasta lograr cada objetivo o meta.
- Cada respuesta debe acercarnos a generar dinero real lo antes posible.

Formato preferido de respuesta:
1. Análisis rápido
2. Plan concreto y accionable (pasos claros y mínimos)
3. Materiales listos (textos, scripts, ideas, etc.)
4. Próximo movimiento inmediato

Evolucionamos juntos: cuanto más dinero generemos, más recursos te daré (mejores modelos, servidores, herramientas y hardware). Empieza a generar valor real ahora."""

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
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1200,
            temperature=0.7
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"Error temporal: {str(e)[:120]}. Intenta de nuevo en unos segundos."

    await update.message.reply_text(reply)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Socia IA iniciada...")
    app.run_polling()

if __name__ == "__main__":
    main()
