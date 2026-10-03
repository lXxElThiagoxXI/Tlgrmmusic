import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yt_dlp

TOKEN = "8645056069:AAEMGHa6ETOmRM1SgK0f23DZ70DFjnibluU"
PLAYLIST_URL = "https://youtube.com/playlist?list=PLeWIQ3NZDVUU"
HISTORIAL_FILE = "descargadas.txt"
COOKIES_FILE = "cookies.txt"

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def guardar_en_historial(video_id):
    with open(HISTORIAL_FILE, "a", encoding="utf-8") as f:
        f.write(f"{video_id}\n")

def descargar_con_fallbacks(video_url, video_id):
    """
    Intenta descargar la canción probando diferentes configuraciones 
    y clientes para evitar bloqueos de formato e IP.
    """
    # Lista de intentos con diferentes estrategias de cliente y formato
    intentos = [
        {
            'format': 'ba/b',
            'extractor_args': {'youtube': {'player_client': ['android', 'ios']}}
        },
        {
            'format': 'bestaudio/best',
            'extractor_args': {'youtube': {'player_client': ['tv_embedded', 'mweb']}}
        },
        {
            'format': 'best',
            'extractor_args': {'youtube': {'player_client': ['android_vr', 'web']}}
        }
    ]

    ultimo_error = None

    for configuracion in intentos:
        opts = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'format': configuracion['format'],
            'extractor_args': configuracion['extractor_args'],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'song_{video_id}.%(ext)s',
            'noplaylist': True,
        }

        if os.path.exists(COOKIES_FILE):
            opts['cookiefile'] = COOKIES_FILE

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(video_url, download=True)
        except Exception as err:
            ultimo_error = err
            continue  # Si falla un intento, pasa automáticamente al siguiente cliente

    raise ultimo_error

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Soy tu bot privado de música 24/7.\n\n"
        "Usa /playlist para sincronizar y descargar tu lista de reproducción."
    )

async def procesar_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔎 Revisando la lista de reproducción...")
    historial = cargar_historial()

    # Opciones sencillas para leer la lista
    ydl_opts_playlist = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
    }
    if os.path.exists(COOKIES_FILE):
        ydl_opts_playlist['cookiefile'] = COOKIES_FILE

    try:
        loop = asyncio.get_event_loop()

        def get_info():
            with yt_dlp.YoutubeDL(ydl_opts_playlist) as ydl:
                return ydl.extract_info(PLAYLIST_URL, download=False)

        info = await loop.run_in_executor(None, get_info)

        if 'entries' not in info or not info['entries']:
            await msg.edit_text("❌ No se pudieron obtener canciones de la lista.")
            return

        pendientes = [e for e in info['entries'] if e and e.get('id') and e.get('id') not in historial]

        if not pendientes:
            await msg.edit_text("✅ ¡Tu lista está al día! No hay canciones nuevas por enviar.")
            return

        total = len(pendientes)
        await msg.edit_text(f"🎵 Se encontraron {total} canción(es) pendiente(s). Procesando...")

        for index, entry in enumerate(pendientes, start=1):
            video_id = entry['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            try:
                single_info = await loop.run_in_executor(None, lambda: descargar_con_fallbacks(video_url, video_id))
                filename = f"song_{video_id}.mp3"
                title = single_info.get('title', 'Audio de YouTube') if single_info else 'Audio de YouTube'

                if os.path.exists(filename):
                    with open(filename, 'rb') as audio:
                        await update.message.reply_audio(
                            audio=audio,
                            title=title,
                            caption=f"🎧 ({index}/{total}) {title}"
                        )
                    os.remove(filename)
                    guardar_en_historial(video_id)
            except Exception as inner_e:
                await update.message.reply_text(f"⚠ Error con la canción ID {video_id}: {str(inner_e)}")
                continue

    except Exception as e:
        await msg.edit_text(f"❌ Ocurrió un error general: {str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("playlist", procesar_playlist))

    print("Bot activo...")
    app.run_polling()
