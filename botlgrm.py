import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

TOKEN = '8645056069:AAGLd4zTu7uAgH84tujKSE_YdasP-N6E_BY'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola. Enviame el enlace de una playlist publica "
        "y descargare las canciones para enviartelas directamente por aqui."
    )

async def procesar_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    # Validacion basica de enlace
    if "http://" not in url and "https://" not in url:
        await update.message.reply_text("Por favor, envia un enlace valido (que empiece por http:// o https://).")
        return

    await update.message.reply_text("Procesando la playlist... Esto puede tomar unos minutos segun el tamano.")

    # Carpeta temporal de descargas
    os.makedirs('downloads', exist_ok=True)

    # Configuracion de yt-dlp para extraer audio en MP3
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'noplaylist': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extraer informacion y descargar
            info = ydl.extract_info(url, download=True)
            
            # Si es una playlist, 'entries' contendra la lista de elementos
            entries = info.get('entries', [info])

            for entry in entries:
                if not entry:
                    continue
                
                title = entry.get('title', 'Audio')
                filename = ydl.prepare_filename(entry)
                filename_mp3 = os.path.splitext(filename)[0] + '.mp3'

                if os.path.exists(filename_mp3):
                    await update.message.reply_text(f"Enviando: {title}")
                    
                    # Enviar el audio a Telegram
                    with open(filename_mp3, 'rb') as audio_file:
                        await update.message.reply_audio(audio=audio_file, title=title)
                    
                    # Borrar el archivo local tras enviarlo para no llenar el disco
                    os.remove(filename_mp3)

        await update.message.reply_text("Playlist procesada y enviada por completo.")

    except Exception as e:
        await update.message.reply_text(f"Ocurrio un error al procesar el enlace: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Manejadores de comandos y mensajes
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_playlist))
    
    print("Bot activo y escuchando en Telegram...")
    app.run_polling()

if __name__ == '__main__':
    main()
