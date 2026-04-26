"""
Maritime Shorts Bot — Denizcilik YouTube Shorts Otomasyon Pipeline
Telegram üzerinden kontrol edilen uçtan uca video üretim sistemi.

Pipeline: Fikir Üretimi → AI Video → Seslendirme → Birleştirme → YouTube Upload
"""

import os
import json
import asyncio
import logging
import uuid
from datetime import time, datetime
import base64
from pathlib import Path
import pytz

from openai import AsyncOpenAI
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
)

from content_engine import generate_content
from video_producer import produce_video, check_credits
from voice_producer import produce_voice
from video_assembler import assemble_with_mixed_audio, assemble_video, cleanup_temp_files
from youtube_uploader import upload_video, check_youtube_ready
from maritime_topics import get_all_categories, get_total_topic_count, get_random_topic
from ops_logger import get_ops_logger

# ── Yapılandırma ────────────────────────────────────────────────────────────
_env_path = Path(__file__).parent / "config.env"
load_dotenv(_env_path)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
KIE_API_KEY = os.getenv("KIE_API_KEY")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Railway Secret Sync ───────────────────────────────────────────
def sync_railway_secrets():
    """Environment variables'dan Base64 ile gelen dosyaları diske yazar."""
    for env_name, filename in [
        ("YOUTUBE_TOKEN_BASE64", "token.json"),
        ("YOUTUBE_CLIENT_SECRETS_BASE64", "client_secrets.json")
    ]:
        val = os.getenv(env_name)
        if val:
            try:
                content = base64.b64decode(val)
                file_path = Path(__file__).parent / filename
                file_path.write_bytes(content)
                logger.info(f"✅ Secret file synced: {filename}")
            except Exception as e:
                logger.error(f"❌ Failed to sync secret {filename}: {e}")

sync_railway_secrets()

# Zorunlu anahtarları kontrol et
for _key_name, _key_val in [
    ("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN),
    ("OPENAI_API_KEY", OPENAI_API_KEY),
    ("KIE_API_KEY", KIE_API_KEY),
]:
    if not _key_val:
        raise RuntimeError(
            f"❌ {_key_name} environment variable tanımlı değil! "
            f"config.env dosyasını kontrol edin."
        )


ops = get_ops_logger("Maritime_Shorts", "Bot")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Aktif üretimler (aynı anda birden fazla istek engellenir)
active_generations: set[int] = set()

# Bekleyen onay havuzu (Hafızada tutulur)
# upload_id: { "path": str, "content": dict, "publish_at": str, "model": str, "chat_id": int }
pending_uploads: dict[str, dict] = {}


# ══════════════════════════════════════════════════════════════════════════════
#  Pipeline — Uçtan Uca Video Üretimi
# ══════════════════════════════════════════════════════════════════════════════

async def full_pipeline(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    custom_idea: str | None = None,
    category: str | None = None,
    upload_to_youtube: bool = True,
    prefer_model: str = "veo",
    publish_at: str | None = None,
    auto_upload: bool = False,
) -> bool:
    """
    Tam pipeline: İçerik → Video → Ses → Birleştir → YouTube

    Args:
        chat_id: Telegram chat ID
        context: Telegram bot context
        custom_idea: Kullanıcının özel fikri (optional)
        category: Konu kategorisi (optional)
        upload_to_youtube: YouTube'a yükle?
        prefer_model: "veo" veya "seedance"

    Returns:
        bool: Pipeline başarılı mı?
    """
    ops.start("Full Pipeline", f"chat_id={chat_id}")

    async def progress(msg: str):
        """Kullanıcıya ilerleme mesajı gönder."""
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg)
        except Exception:
            pass

    temp_files = []

    try:
        # ── 1. İçerik Üret ───────────────────────────────────────────────
        await progress("💡 Generating maritime video idea...")

        topic = None
        if not custom_idea:
            topic = get_random_topic()

        content = await generate_content(
            openai_client,
            topic=topic,
            custom_idea=custom_idea,
            category=category,
        )

        await progress(
            f"📝 **{content['title']}**\n\n"
            f"🎙️ _{content['voiceover_text']}_\n\n"
            f"🎬 Generating video now... (~3-5 min)"
        )

        # ── 2. Video Üret ────────────────────────────────────────────────
        video_result = await produce_video(
            api_key=KIE_API_KEY,
            prompt=content["video_prompt"],
            prefer_model=prefer_model,
            progress_callback=progress,
        )

        if not video_result["path"]:
            await progress("❌ Video generation failed. Please try again later.")
            ops.error("Video generation failed")
            return False

        temp_files.append(video_result["path"])
        await progress(f"✅ Video ready! (Model: {video_result['model']})")

        # ── 3. Seslendirme Üret ──────────────────────────────────────────
        voice_result = await produce_voice(
            api_key=KIE_API_KEY,
            text=content["voiceover_text"],
            voice="Daniel",
            progress_callback=progress,
        )

        if voice_result["path"]:
            temp_files.append(voice_result["path"])

        # ── 4. Birleştir ─────────────────────────────────────────────────
        if voice_result["path"]:
            final_path = await assemble_with_mixed_audio(
                video_path=video_result["path"],
                voiceover_path=voice_result["path"],
                voice_volume=1.0,
                bg_volume=0.2,
                progress_callback=progress,
            )
        else:
            # Ses yoksa video olduğu gibi
            logger.warning("Voiceover failed, using video without narration")
            await progress("⚠️ Voiceover failed, using video with ambient sound only")
            final_path = video_result["path"]

        if not final_path:
            await progress("❌ Video assembly failed.")
            ops.error("Video assembly failed")
            return False

        if final_path != video_result["path"]:
            temp_files.append(final_path)

        # ── 5. Otomatik Yükleme (Günlük Otomasyon için) ────────────────
        if auto_upload:
            try:
                if check_youtube_ready():
                    await progress("📤 YouTube'a yükleniyor (otomatik)...")
                    youtube_result = upload_video(
                        video_path=final_path,
                        title=content["title"],
                        description=content["description"],
                        tags=content["tags"],
                        category_id="28",
                        privacy="private",
                        publish_at=publish_at,
                    )
                    if youtube_result:
                        msg_parts = [
                            f"🎉 **Otomatik Video Yüklendi!**",
                            f"📝 {content['title']}",
                            f"🎬 Model: {video_result['model']}",
                        ]
                        if publish_at:
                            msg_parts.append(f"⏰ Yayın: {publish_at}")
                        msg_parts.append(f"📺 {youtube_result['url']}")
                        await progress("\n".join(msg_parts))
                        ops.success("Auto Pipeline", f"title={content['title'][:60]}")
                        return True
                    else:
                        await progress("❌ YouTube yükleme başarısız!")
                        ops.error("Auto upload failed")
                        return False
                else:
                    await progress("⚠️ YouTube hazır değil (client_secrets bulunamadı)")
                    ops.error("YouTube not ready")
                    return False
            finally:
                cleanup_temp_files(final_path, *[f for f in temp_files if f != final_path])

        # ── 5b. Yükleme Öncesi Telegram'dan Onay İste (Manuel Mod) ───────
        upload_id = str(uuid.uuid4())
        
        # Videonun geçici dosyasını ileride yüklemek üzere havuzda tutacağız
        # cleanup_temp_files'dan çıkarmamız gerek.
        if final_path in temp_files:
            temp_files.remove(final_path)
            
        pending_uploads[upload_id] = {
            "path": final_path,
            "content": content,
            "publish_at": publish_at,
            "model": video_result["model"],
            "chat_id": chat_id,
        }

        try:
            with open(final_path, "rb") as vf:
                caption_parts = [f"✅ **{content['title']}**"]
                caption_parts.append(f"🎬 Model: {video_result['model']}")
                if publish_at:
                    caption_parts.append(f"⏰ Hedeflenen Yayın Saati: {publish_at}")
                caption_parts.append(f"🎙️ {content['voiceover_text']}")
                
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Onayla ve Yükle", callback_data=f"approve_{upload_id}"),
                        InlineKeyboardButton("❌ İptal Et (Sil)", callback_data=f"reject_{upload_id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await context.bot.send_video(
                    chat_id=chat_id,
                    video=vf,
                    caption="\n".join(caption_parts),
                    reply_markup=reply_markup,
                    supports_streaming=True,
                    width=1080,
                    height=1920,
                )
            await progress("⏳ Lütfen videoyu izleyip yukarıdaki butonlardan onay verin. (30 dakika içinde yanıt vermezseniz **otomatik** olarak yüklenecektir).")
            
            # --- 30 DAKİKALIK OTOMATİK ONAY SÜRECİ ---
            async def auto_upload_task(uid: str):
                await asyncio.sleep(1800)  # 30 dakika (1800 saniye)
                if uid in pending_uploads:
                    logger.info(f"Yarı otomatik süre doldu, {uid} id'li video otomatik yükleniyor...")
                    data = pending_uploads.pop(uid)
                    
                    try:
                        if check_youtube_ready():
                            youtube_result = upload_video(
                                video_path=data["path"],
                                title=data["content"]["title"],
                                description=data["content"]["description"],
                                tags=data["content"]["tags"],
                                category_id="28",
                                privacy="public",
                                publish_at=data["publish_at"],
                            )
                            if youtube_result:
                                await context.bot.send_message(
                                    chat_id=data["chat_id"], 
                                    text=f"⏰ **Otomatik Yükleme Devrede!**\n30 dakika boyunca iptal komutu gelmediği için video programlanan saatte yayınlanmak üzere YouTube'a gönderildi!\n\n📝 {data['content']['title']}",
                                    parse_mode="Markdown"
                                )
                        else:
                            await context.bot.send_message(chat_id=data["chat_id"], text="⚠️ Otomatik yükleme yapılamadı. `client_secrets.json` geçersiz veya yetkisiz.")
                    except Exception as e:
                        logger.error(f"Auto-upload error: {e}")
                    finally:
                        cleanup_temp_files(data["path"])

            # Arka plana sayacı yerleştir
            asyncio.create_task(auto_upload_task(upload_id))

        except Exception as e:
            logger.error(f"Telegram video send error: {e}")
            await progress("⚠️ Video Telegram'a gönderilemedi. Dosya boyutu büyük olabilir veya bağlantı kesildi.")
            # Hata verirse temizleyebiliriz
            cleanup_temp_files(final_path)
            pending_uploads.pop(upload_id, None)

        ops.success("Full Pipeline (Pending Approval)", f"title={content['title'][:60]}")
        return True

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        await progress(f"❌ Pipeline error: {str(e)[:200]}")
        ops.error("Pipeline crashed", exception=e)
        return False

    finally:
        # Onay bekleyen `final_path` harici diğer gereksiz geçici dosyaları temizle.
        cleanup_temp_files(*temp_files)


# ══════════════════════════════════════════════════════════════════════════════
#  Automated Daily Job (US Prime Time Scheduling)
# ══════════════════════════════════════════════════════════════════════════════

async def automatic_daily_video(context: ContextTypes.DEFAULT_TYPE):
    """Her gün 00:05 Berlin saatinde otomatik pipeline → 03:05'te yayın."""
    if ADMIN_CHAT_ID == 0:
        logger.warning("Automated job skipped: ADMIN_CHAT_ID is 0")
        return

    berlin_tz = pytz.timezone('Europe/Berlin')
    now_berlin = datetime.now(berlin_tz)

    # 03:05 Berlin saatinde yayınla (3 saat sonra)
    publish_dt = now_berlin.replace(hour=3, minute=5, second=0, microsecond=0)
    publish_at_str = publish_dt.isoformat()

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(
                    f"🤖 **Günlük Otomasyon Başladı** (Deneme {attempt}/{max_retries})\n"
                    f"🕐 Üretim: {now_berlin.strftime('%H:%M %Z')}\n"
                    f"📅 Yayın: 03:05 Berlin\n"
                    f"⏳ Video üretiliyor..."
                ),
                parse_mode="Markdown",
            )

            result = await full_pipeline(
                chat_id=ADMIN_CHAT_ID,
                context=context,
                publish_at=publish_at_str,
                auto_upload=True,
            )

            if result:
                logger.info(f"Daily automation succeeded on attempt {attempt}")
                return
            else:
                logger.warning(f"Daily automation failed on attempt {attempt}")

        except Exception as e:
            logger.error(f"Daily automation attempt {attempt} error: {e}")

        # Başarısızsa yeniden dene (5 dk, 10 dk bekleme)
        if attempt < max_retries:
            wait_minutes = attempt * 5
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"⚠️ Deneme {attempt} başarısız. {wait_minutes} dk sonra tekrar denenecek...",
                )
            except Exception:
                pass
            await asyncio.sleep(wait_minutes * 60)

    # Tüm denemeler başarısız
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"❌ Günlük otomasyon {max_retries} denemeden sonra başarısız oldu!",
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  Telegram Handlers (Approval & Commands)
# ══════════════════════════════════════════════════════════════════════════════

async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının videoyu onaylama/reddetme reaksiyonunu işler."""
    query = update.callback_query
    await query.answer()

    action, upload_id = query.data.split("_", 1)
    
    if upload_id not in pending_uploads:
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n⚠️ Bu video oturumu zaman aşımına uğramış veya silinmiş.")
        return

    data = pending_uploads[upload_id]
    chat_id = data["chat_id"]
    content = data["content"]
    final_path = data["path"]
    publish_at = data["publish_at"]
    model_name = data["model"]

    if action == "reject":
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ **VİDEO İPTAL EDİLDİ VE SİLİNDİ.**")
        cleanup_temp_files(final_path)
        pending_uploads.pop(upload_id, None)
        return

    if action == "approve":
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n📤 **Yükleme Onaylandı!** YouTube'a gönderiliyor...")
        
        try:
            # YouTube API üzerinden yükle
            if check_youtube_ready():
                youtube_result = upload_video(
                    video_path=final_path,
                    title=content["title"],
                    description=content["description"],
                    tags=content["tags"],
                    category_id="28",
                    privacy="public",
                    publish_at=publish_at,
                )

                if youtube_result:
                    msg_tail = f"⏰ Yayın Takvimi: {publish_at}" if publish_at else f"📺 Link: {youtube_result['url']}"
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"🎉 **YouTube'a Başarıyla Yüklendi!**\n\n"
                            f"{msg_tail}\n"
                            f"📝 {content['title']}\n"
                        ),
                        parse_mode="Markdown"
                    )
                    await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ **YÜKLENDİ: {youtube_result['url']}**")
                else:
                    await context.bot.send_message(chat_id=chat_id, text="⚠️ YouTube'a yükleme sırasında hata oluştu. Tarayıcı izinlerini kontrol edin.")
            else:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Yükleme yapılamadı. `client_secrets.json` bulunamadı veya yetki verilmemiş.")
                
        except Exception as e:
            logger.error(f"Approval upload error: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Yükleme çöktü: {str(e)[:100]}")
        finally:
            cleanup_temp_files(final_path)
            pending_uploads.pop(upload_id, None)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start — Hoş geldin mesajı."""
    total = get_total_topic_count()
    welcome = (
        "🚢 **Maritime Shorts Bot**\n\n"
        f"Generate cinematic YouTube Shorts about maritime topics!\n"
        f"📚 {total} topics across 12 categories\n\n"
        "**Commands:**\n"
        "/generate — Random maritime video\n"
        "/generate [idea] — Custom topic\n"
        "/topics — List all categories\n"
        "/credits — Check Kie AI balance\n"
        "/batch [N] — Generate N videos (max 5)\n\n"
        "Just type /generate to get started! 🎬"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def cmd_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/generate [optional topic] — Video üret."""
    chat_id = update.effective_chat.id

    if chat_id in active_generations:
        await update.message.reply_text(
            "⏳ A video is already being generated! Please wait."
        )
        return

    # Kullanıcı özel konu yazdı mı?
    custom_idea = None
    if context.args:
        custom_idea = " ".join(context.args)

    active_generations.add(chat_id)
    try:
        await full_pipeline(
            chat_id=chat_id,
            context=context,
            custom_idea=custom_idea,
        )
    finally:
        active_generations.discard(chat_id)


async def cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/topics — Konu kategorilerini listele."""
    categories = get_all_categories()
    lines = ["🚢 **Maritime Topic Categories:**\n"]
    for cat in categories:
        lines.append(f"  {cat['label']} — {cat['count']} topics")
    lines.append(f"\n📚 Total: {get_total_topic_count()} topics")
    lines.append("\nUse `/generate` for a random topic!")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/credits — Kie AI kredi bakiyesini göster."""
    await update.message.reply_text("💰 Checking Kie AI balance...")
    result = await check_credits(KIE_API_KEY)
    if result:
        await update.message.reply_text(
            f"💰 **Kie AI Credit Info:**\n"
            f"```\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("❌ Could not fetch credit info.")


async def cmd_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/batch [N] — N adet video üret."""
    chat_id = update.effective_chat.id

    if chat_id in active_generations:
        await update.message.reply_text("⏳ A generation is already running!")
        return

    count = 1
    if context.args:
        try:
            count = min(int(context.args[0]), 5)  # Max 5
        except ValueError:
            count = 1

    await update.message.reply_text(
        f"🚀 Starting batch generation: {count} videos\n"
        f"This will take approximately {count * 5} minutes."
    )

    active_generations.add(chat_id)
    success_count = 0
    try:
        for i in range(count):
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"\n━━━━━━━━━━━━━━━━━━━━\n📹 Video {i+1}/{count}\n━━━━━━━━━━━━━━━━━━━━",
            )
            result = await full_pipeline(
                chat_id=chat_id,
                context=context,
            )
            if result:
                success_count += 1

            # Videolar arası bekleme (rate limit)
            if i < count - 1:
                await asyncio.sleep(5)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"\n🏁 **Batch Complete!**\n✅ {success_count}/{count} videos generated successfully.",
            parse_mode="Markdown",
        )
    finally:
        active_generations.discard(chat_id)


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/model [veo|seedance] — Tercih edilen modeli değiştir."""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/model veo` or `/model seedance`\n\n"
            "**Veo 3.1** — Premium cinematic quality (more expensive)\n"
            "**Seedance 2.0** — Good quality, more affordable",
            parse_mode="Markdown",
        )
        return

    model = context.args[0].lower()
    if model in ("veo", "seedance"):
        context.user_data["prefer_model"] = model
        await update.message.reply_text(f"✅ Preferred model set to: **{model.title()}**", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Invalid model. Use `veo` or `seedance`.", parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Serbest metin mesajlarını işle — konu olarak al."""
    chat_id = update.effective_chat.id
    user_text = update.message.text
    if not user_text:
        return

    if chat_id in active_generations:
        await update.message.reply_text("⏳ Video is being generated, please wait...")
        return

    # Serbest metin → /generate [topic] gibi davran
    await update.message.reply_text(
        f"🎬 Great idea! Generating a maritime video about: _{user_text}_",
        parse_mode="Markdown",
    )

    active_generations.add(chat_id)
    try:
        await full_pipeline(
            chat_id=chat_id,
            context=context,
            custom_idea=user_text,
        )
    finally:
        active_generations.discard(chat_id)


# ══════════════════════════════════════════════════════════════════════════════
#  Error Handler
# ══════════════════════════════════════════════════════════════════════════════

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler — geçici hataları bastır."""
    error = context.error
    error_name = type(error).__name__

    if "Conflict" in error_name or "terminated by other getUpdates" in str(error):
        logger.info(f"ℹ️ Conflict (deploy transition): {error}")
        return

    if error_name in ("NetworkError", "TimedOut", "RetryAfter"):
        logger.warning(f"⚠️ Temporary network error ({error_name}): {error}")
        return

    logger.error(f"❌ Bot error ({error_name}): {error}", exc_info=context.error)


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    logger.info("🚢 Maritime Shorts Bot starting...")
    logger.info(f"   Total topics: {get_total_topic_count()}")
    logger.info(f"   YouTube ready: {check_youtube_ready()}")
    logger.info(f"   ADMIN_CHAT_ID: {ADMIN_CHAT_ID}")

    try:
        from telegram.ext import Defaults
        berlin_tz = pytz.timezone('Europe/Berlin')
        defaults = Defaults(tzinfo=berlin_tz)
        
        app = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .defaults(defaults)
            .concurrent_updates(True)
            .read_timeout(30)
            .write_timeout(30)
            .connect_timeout(30)
            .pool_timeout(30)
            .build()
        )

        # ── Daily Job Configuration ──────────────────────────────
        # Her gün 00:05 Berlin saatinde video üret → 03:05'te yayınla
        # YouTube'a 3 saat analiz süresi verir
        job_time = time(hour=0, minute=5)
        app.job_queue.run_daily(automatic_daily_video, time=job_time, name='daily_automation')
        logger.info(f"⏰ Daily automation scheduled at 00:05 Europe/Berlin (Publish at 03:05 Berlin)")

        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("generate", cmd_generate))
        app.add_handler(CommandHandler("topics", cmd_topics))
        app.add_handler(CommandHandler("credits", cmd_credits))
        app.add_handler(CommandHandler("batch", cmd_batch))
        app.add_handler(CommandHandler("model", cmd_model))
        app.add_handler(CallbackQueryHandler(handle_approval, pattern="^(approve|reject)_"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_error_handler(error_handler)

        logger.info("✅ Handlers registered, starting polling...")

        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"],
            stop_signals=None,
        )
    except Exception as e:
        logger.critical(f"❌ Bot startup error: {e}", exc_info=True)
        ops.error("Bot startup failed", exception=e)
        ops.wait_for_logs()
        raise


if __name__ == "__main__":
    main()
