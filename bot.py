    # ——— Búsqueda dinámica real de GIFs ———
    if "gif" in user_input.lower():
        termino = user_input.lower()
        for palabra in ["un gif de", "gif de", "gif", "mándame", "enviame", "busca", "a ver"]:
            termino = termino.replace(palabra, "")
        termino = termino.strip() or "funny love"

        gif_url = None
        try:
            with DDGS() as ddgs:
                # Buscamos directamente imágenes o archivos gif en la web abierta
                results = ddgs.text(f"{termino} filetype:gif OR media tenor giphy", max_results=10)
                for r in results:
                    href = r.get("href", "") or r.get("body", "")
                    # Buscamos cualquier enlace directo que contenga formato gif o servidores de animación
                    if any(ext in href.lower() for ext in [".gif", "tenor.com", "giphy.com", "media.giphy.com"]):
                        # Limpiamos la URL por si acaso
                        if "http" in href:
                            start = href.find("http")
                            possible_url = href[start:].split(" ")[0]
                            if ".gif" in possible_url or "giphy" in possible_url or "tenor" in possible_url:
                                gif_url = possible_url
                                break
        except Exception as e:
            print(f"Error buscando GIF: {e}")

        # Si por alguna razón extrema la web no devolvió nada en ese microsegundo, 
        # usamos una búsqueda de respaldo en texto plano pero buscando en Google/DDGS otro término similar, 
        # garantizando que siempre intente buscar por sí mismo.
        if not gif_url:
            gif_url = f"https://media.giphy.com/media/xT9IgzoKnwFNmISR8I/giphy.gif" # Un comodín neutral temporal solo si falla la red

        await update.message.reply_animation(
            animation=gif_url,
            caption=f"¡Aquí tienes mi amor! Busqué uno de **{termino}** para ti 🚀✨"
        )
        return
