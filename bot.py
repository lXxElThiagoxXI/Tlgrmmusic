import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yt_dlp

# Token de tu bot de Telegram
TOKEN = "8645056069:AAGLd4zTu7uAgH84tujKSE_YdasP-N6E_BY"

# Playlist fija de YouTube
PLAYLIST_URL = "https://youtube.com/playlist?list=PLeWIQ3NZDVUU"
HISTORIAL_FILE = "descargadas.txt"

def cargar_historial():
    """Lee las canciones que ya han sido descargadas."""
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def guardar_en_historial(video_id):
    """Guarda el ID de la canción enviada en el archivo de texto."""
    with open(HISTORIAL_FILE, "a", encoding="utf-8") as f:
        f.write(f"{video_id}\n")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde al comando /start."""
    await update.message.reply_text(
        "¡Hola! Soy tu bot de música 24/7.\n\n"
        "Usa el comando /playlist para revisar tu lista de reproducción de YouTube y enviar las canciones nuevas."
    )

async def procesar_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obtiene y procesa las canciones de la playlist."""
    msg = await update.message.reply_text("🔎 Revisando la lista de reproducción...")
    historial = cargar_historial()

    ydl_opts_info = {
        'extract_flat': True,
        'quiet': True,
    }

    try:
        loop = asyncio.get_event_loop()

        def get_info():
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                return ydl.extract_info(PLAYLIST_URL, download=False)

        info = await loop.run_in_executor(None, get_info)

        if 'entries' not in info or not info['entries']:
            await msg.edit_text("❌ No se pudieron obtener videos de la lista de reproducción.")
            return

        # Filtrar canciones que aún no están en el historial
        pendientes = [e for e in info['entries'] if e and e.get('id') and e.get('id') not in historial]

        if not pendientes:
            await msg.edit_text("✅ ¡Tu lista está al día! No hay canciones nuevas por enviar.")
            return

        total = len(pendientes)
        await msg.edit_text(f"🎵 Se encontraron {total} canción(es) nueva(s). Procesando...")

        for index, entry in enumerate(pendientes, start=1):
            video_id = entry['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            ydl_opts_download = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': f'song_{video_id}.%(ext)s',
                'quiet': True,
                'noplaylist': True
            }

            def download_single():
                with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                    return ydl.extract_info(video_url, download=True)

            try:
                single_info = await loop.run_in_executor(None, download_single)
                filename = f"song_{video_id}.mp3"
                title = single_info.get('title', 'Audio de YouTube')

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
                await update.message.reply_text(f"⚠️️ Error procesando la canción ID {video_id}: {str(inner_e)}")
                continue

    except Exception as e:
        await msg.edit_text(f"❌ Ocurrió un error general: {str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("playlist", procesar_playlist))

    print("Bot activo y escuchando comandos...")
    app.run_polling()
