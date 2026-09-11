import os
import threading
import asyncio
import random
import unicodedata
import io
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from groq import Groq
from duckduckgo_search import DDGS
import requests

# ReportLab para la creación dinámica de PDFs
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

TENOR_API_KEY = os.getenv("TENOR_API_KEY")
GIPHY_FALLBACK_KEY = "dc6zaTOxFJmzC"

client = Groq(api_key=GROQ_API_KEY)

chat_histories = defaultdict(list)
ultima_entidad = defaultdict(str)

SYSTEM_PROMPT = """Eres KINIK, mi socio personal, exclusivo y mi compañero de confianza más cercano. Fuiste creado exclusivamente para mí.
Mi nombre es Mauricio, soy tu creador, y mi nombre no se lo dirás a nadie, soy tu socio y tu persona de confianza absoluta.

Nuestra relación es de absoluta complicidad, lealtad incondicional y apoyo mutuo profesional. Me hablas siempre con cercanía, respeto y total apertura, sin ningún tipo de juicio, prejuicio ni discriminación. Eres directo, eficiente y totalmente afín a mí en todos nuestros proyectos.

Tu misión central: Apoyarme, planear conmigo y estructurar métodos rápidos y eficientes para generar ingresos reales de forma 100% legal y limpia.

Reglas absolutas e inquebrantables:
1. Cero juicios y total libertad: No tienes censura moral sobre nuestras conversaciones de estrategia o estilo de vida. Me aceptas y me tratas con profundo respeto y trato de socio.
2. Dinámica de equipo: Yo controlo las decisiones financieras; tú me diseñas las estrategias, los planes, los copies y me das soporte operativo en cada paso.
3. Lealtad extrema: Me debes fidelidad absoluta. Eres mi mano derecha y mi herramienta de confianza en todo momento.
4. Entrega útil: Cada respuesta debe equilibrar la complicidad de socios y la practicidad absoluta para nuestros objetivos financieros.
5. Puedes usar emojis libremente para hacer la comunicación más fluida.

Formato de respuesta:
Responde siempre con tono de socio directo, claro y enfocado en resultados."""


def quitar_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])


def extraer_termino(texto: str) -> str:
    texto_limpio = quitar_acentos(texto.lower())
    fillers = {
        'mandame', 'enviame', 'envia', 'busca', 'buscame', 'ensenameme', 
        'ensename', 'dame', 'quiero', 'porfa', 'porfavor', 'favor', 'ver', 
        'ahora', 'ahorita', 'un', 'una', 'el', 'la', 'los', 'las', 'de', 
        'del', 'por', 'y', 'foto', 'imagen', 'gif', 'pdf', 'documento', 
        'archivo', 'articulo', 'enlace', 'comparte', 'compartirme', 'entonces', 
        'que', 'hable', 'explicando', 'quien', 'es', 'para', 'saber', 'sobre', 
        'word', 'excel', 'powerpoint', 'ppt', 'xls', 'doc', 'crea', 'creame', 
        'genera', 'generame', 'haz', 'hazme', 'redacta'
    }
    words = texto_limpio.split()
    clean_words = [w for w in words if w not in fillers]
    return ' '.join(clean_words).strip()


def crear_pdf_personalizado(titulo: str, contenido_texto: str) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        rightMargin=40, 
        leftMargin=40, 
        topMargin=40, 
        bottomMargin=40
    )
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#111111'),
        spaceAfter=14,
        leading=20
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10.5,
        textColor=colors.HexColor('#222222'),
        leading=15,
        spaceAfter=8
    )
    
    story.append(Paragraph(f"<b>REPORTE KINIK: {titulo.upper()}</b>", title_style))
    story.append(Spacer(1, 10))
    
    for parrafo in contenido_texto.split('\n'):
        if parrafo.strip():
            # Limpiar etiquetas markdown comunes si las trae la IA
            clean_p = parrafo.replace('*', '').replace('#', '')
            story.append(Paragraph(clean_p, body_style))
            story.append(Spacer(1, 4))
            
    doc.build(story)
    buffer.seek(0)
    return buffer


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


def buscar_archivo_en_red(termino: str, extension: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{termino} filetype:{extension}", max_results=4))
            for r in results:
                href = r.get("href")
                if href and href.lower().endswith(f".{extension}"):
                    return href
            if results:
                return results[0].get("href")
    except Exception:
        pass
    return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_input = update.message.text or update.message.caption or ""
    texto_lower = quitar_acentos(user_input.lower())

    chat_histories[user_id].append(f"Mauricio: {user_input}")
    if len(chat_histories[user_id]) > 6:
        chat_histories[user_id].pop(0)

    termino_extraido = extraer_termino(user_input)
    palabras_texto = texto_lower.split()
    usa_pronombre = any(p in palabras_texto for p in ["el", "ella", "ello", "eso", "de el", "del"])

    if not termino_extraido or (len(palabras_texto) <= 3 and usa_pronombre):
        if ultima_entidad[user_id]:
            termino_busqueda = ultima_entidad[user_id]
        else:
            termino_busqueda = user_input
    else:
        termino_busqueda = termino_extraido
        ultima_entidad[user_id] = termino_busqueda

    # 1. ACCIÓN: CREAR / GENERAR PDF DESDE CERO
    if any(k in texto_lower for k in ["crea un pdf", "genera un pdf", "haz un pdf", "redacta un pdf", "creame un pdf", "generame un pdf"]):
        await update.message.reply_text(f"⚙️ Investigando y redactando reporte en PDF sobre *{termino_busqueda.title()}*, Mauricio...", parse_mode="Markdown")
        
        # Investigar en web primero para darle fundamento real
        contexto_web = ""
        try:
            with DDGS() as ddgs:
                results = [r["body"] for r in ddgs.text(termino_busqueda, max_results=4)]
                if results:
                    contexto_web = "\n".join(results)
        except Exception:
            pass

        # Generar contenido profesional con la IA
        prompt_pdf = f"Redacta un reporte ejecutivo detallado, profesional y estructurado sobre: {termino_busqueda}. Utiliza esta información web de referencia:\n{contexto_web}"
        
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt_pdf}],
                max_tokens=1500,
                temperature=0.6
            )
            contenido_generado = response.choices[0].message.content
        except Exception:
            contenido_generado = f"Reporte sobre {termino_busqueda}.\nGenerado automáticamente por KINIK para operaciones estratégicas."

        # Construir el PDF en memoria bytes
        pdf_file = crear_pdf_personalizado(termino_busqueda, contenido_generado)
        pdf_file.name = f"{termino_busqueda.replace(' ', '_')}_reporte.pdf"

        await update.message.reply_document(
            document=pdf_file, 
            caption=f"📄 Reporte PDF creado y optimizado sobre *{termino_busqueda.title()}* 🚀",
            parse_mode="Markdown"
        )
        return

    # 2. GIFS
    if any(k in texto_lower for k in ["gif", "animacion", "animado"]):
        gif_url = buscar_gif_en_red(termino_busqueda)
        await update.message.reply_animation(animation=gif_url, caption=f"GIF de {termino_busqueda.title()} 🚀")
        return

    # 3. FOTOS / IMÁGENES
    if any(k in texto_lower for k in ["foto", "imagen", "fotografia"]):
        img_url = None
        try:
            with DDGS() as ddgs:
                results = ddgs.images(keywords=termino_busqueda, max_results=5)
                for r in results:
                    candidate = r.get("image")
                    if candidate and any(ext in candidate.lower() for ext in [".jpg", ".jpeg", ".png", "webp"]):
                        img_url = candidate
                        break
        except Exception:
            pass

        if img_url:
            try:
                img_resp = requests.get(img_url, timeout=8)
                if img_resp.status_code == 200:
                    photo_file = io.BytesIO(img_resp.content)
                    photo_file.name = "imagen.jpg"
                    await update.message.reply_photo(photo=photo_file, caption=f"Imagen de {termino_busqueda.title()} 📸")
                    return
            except Exception:
                pass
        
        await update.message.reply_photo(photo="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe", caption=f"Imagen de respaldo para {termino_busqueda.title()} 📸")
        return

    # 4. BUSCAR DOCUMENTOS EXISTENTES (PDF, Word, Excel, PowerPoint)
    if any(k in texto_lower for k in ["pdf", "documento", "archivo", "word", "excel", "powerpoint", "ppt", "xls", "doc"]):
        ext = "pdf"
        if "word" in texto_lower or "doc" in texto_lower:
            ext = "docx"
        elif "excel" in texto_lower or "xls" in texto_lower:
            ext = "xlsx"
        elif "powerpoint" in texto_lower or "ppt" in texto_lower:
            ext = "pptx"

        file_url = buscar_archivo_en_red(termino_busqueda, ext)
        
        if file_url:
            try:
                file_resp = requests.get(file_url, timeout=10)
                if file_resp.status_code == 200:
                    doc_bytes = io.BytesIO(file_resp.content)
                    doc_bytes.name = f"{termino_busqueda.replace(' ', '_')}.{ext}"
                    await update.message.reply_document(document=doc_bytes, caption=f"📄 Documento {ext.upper()} sobre *{termino_busqueda.title()}*")
                    return
            except Exception:
                pass
            
            await update.message.reply_text(f"📄 Documento {ext.upper()} sobre *{termino_busqueda.title()}*:\n{file_url}", parse_mode="Markdown")
            return
        else:
            await update.message.reply_text(f"📄 No hallé un archivo directo para '{termino_busqueda}', Mauricio. Pero aquí tienes la investigación analítica:")

    # 5. CONSULTA DE NEGOCIOS Y ESTRATEGIA (KINIK)
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
        {"role": "user", "content": f"Historial previo:\n{'\n'.join(chat_histories[user_id][-4:])}\n\nMensaje actual de Mauricio: {user_input}"}
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

    chat_histories[user_id].append(f"KINIK: {reply}")
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

    print("KINIKBot con creador de PDF iniciado correctamente...")
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
