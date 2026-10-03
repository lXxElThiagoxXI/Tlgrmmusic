import os
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yt_dlp

TOKEN = "8645056069:AAEMGHa6ETOmRM1SgK0f23DZ70DFjnibluU"
PLAYLIST_URL = "https://youtube.com/playlist?list=PLeWIQ3NZDVUU"
HISTORIAL_FILE = "descargadas.txt"

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def guardar_en_historial(video_id):
    with open(HISTORIAL_FILE, "a", encoding="utf-8") as f:
        f.write(f"{video_id}\n")

def descargar_con_cobalt(video_url, output_path):
    """ Envía la solicitud a la API de Cobalt emulando un navegador real """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    payload = {
        "url": video_url,
        "downloadMode": "audio",
        "audioFormat": "mp3"
    }
    
    response = requests.post("https://api.cobalt.tools/api/json", json=payload, headers=headers, timeout=15)
    
    if response.status_code == 200:
        data = response.json()
        download_url = data.get("url")
        
        if not download_url and data.get("status") == "redirect":
            download_url = data.get("url")

        if download_url:
            audio_req = requests.get(download_url, headers=headers, stream=True)
            if audio_req.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in audio_req.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
                
    raise Exception(f"Cobalt no pudo procesar este enlace (Estado HTTP: {response.status_code}).")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Soy tu bot privado de música 24/7.\n\n"
        "Usa /playlist para sincronizar y descargar tu lista de reproducción."
    )

async def procesar_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔎 Revisando la lista de reproducción...")
    historial = cargar_historial()

    ydl_opts_playlist = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
    }

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
            title = entry.get('title', f'Canción {video_id}')
            filename = f"song_{video_id}.mp3"

            try:
                await loop.run_in_executor(None, lambda: descargar_con_cobalt(video_url, filename))

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
                await update.message.reply_text(f"⚠ Error con {title}: {str(inner_e)}")
                continue

    except Exception as e:
        await msg.edit_text(f"❌ Ocurrió un error general: {str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("playlist", procesar_playlist))

    print("Bot activo...")
    app.run_polling()
