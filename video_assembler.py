"""
Video Assembler — FFmpeg ile video + ses birleştirme.
Shorts formatında çıktı üretir (9:16, H.264, AAC).
"""

import os
import logging
import tempfile
import asyncio

logger = logging.getLogger(__name__)


async def assemble_video(
    video_path: str,
    audio_path: str | None = None,
    output_path: str | None = None,
    progress_callback=None,
) -> str | None:
    """
    Video ve ses dosyasını birleştir.

    Args:
        video_path: Video dosya yolu (.mp4)
        audio_path: Ses dosya yolu (.mp3/.wav), None ise video olduğu gibi döner
        output_path: Çıktı dosya yolu, None ise geçici dosya oluşturulur
        progress_callback: async callable(message: str)

    Returns:
        str: Birleştirilmiş videonun dosya yolu
    """
    if not video_path or not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return None

    # Ses yoksa videoyu doğrudan döndür
    if not audio_path or not os.path.exists(audio_path):
        logger.info("No audio file, returning video as-is")
        return video_path

    if progress_callback:
        await progress_callback("🔧 Merging video + voiceover...")

    if not output_path:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        output_path = tmp.name
        tmp.close()

    # ══════════════════════════════════════════════════════════════════════
    #  FFmpeg komutu:
    #  - Video'nun orijinal ses akışını kaldır (varsa)
    #  - Voiceover'ı video üstüne ekle
    #  - Video codec: copy (yeniden encode etme — hızlı)
    #  - Audio codec: AAC
    #  - -shortest: kısa olanın süresine kes
    # ══════════════════════════════════════════════════════════════════════

    cmd = [
        "ffmpeg",
        "-y",                    # Üzerine yaz
        "-i", video_path,        # Video
        "-i", audio_path,        # Ses (voiceover)
        "-c:v", "copy",          # Video codec: copy (hızlı)
        "-c:a", "aac",           # Audio codec: AAC
        "-b:a", "192k",          # Audio bitrate
        "-map", "0:v:0",         # İlk input'un video akışı
        "-map", "1:a:0",         # İkinci input'un ses akışı
        "-shortest",             # Kısa olanın süresine kes
        "-movflags", "+faststart",  # Web streaming uyumu
        output_path,
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()[:500]}")
            return None

        output_size = os.path.getsize(output_path)
        logger.info(f"Video assembled: {output_path} ({output_size} bytes)")
        return output_path

    except FileNotFoundError:
        logger.error("FFmpeg not found! Install FFmpeg: https://ffmpeg.org/download.html")
        return None
    except Exception as e:
        logger.error(f"Assembly error: {e}")
        return None


async def _has_audio_stream(video_path: str) -> bool:
    """ffprobe ile video dosyasında ses akışı olup olmadığını kontrol et."""
    try:
        process = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            video_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        has_audio = b"audio" in stdout
        logger.info(f"Audio probe: {video_path} → {'has audio' if has_audio else 'NO audio'}")
        return has_audio
    except FileNotFoundError:
        logger.warning("ffprobe not found, assuming video has audio")
        return True  # Güvenli tarafta kal, mix denensin
    except Exception as e:
        logger.warning(f"Audio probe error: {e}, assuming video has audio")
        return True


async def assemble_with_mixed_audio(
    video_path: str,
    voiceover_path: str,
    output_path: str | None = None,
    voice_volume: float = 1.0,
    bg_volume: float = 0.15,
    progress_callback=None,
) -> str | None:
    """
    Video'nun orijinal sesini (ambient) düşük sesle koruyup,
    voiceover'ı yüksek sesle ekle.

    Args:
        video_path: Video dosya yolu
        voiceover_path: Voiceover ses dosyası
        output_path: Çıktı dosya yolu
        voice_volume: Voiceover ses seviyesi (1.0 = normal)
        bg_volume: Arka plan ses seviyesi (0.15 = %15)
        progress_callback: async callable(message: str)
    """
    if not video_path or not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return None

    if not voiceover_path or not os.path.exists(voiceover_path):
        logger.info("No voiceover file, returning video as-is")
        return video_path

    if not output_path:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        output_path = tmp.name
        tmp.close()

    # ── Ses akışı kontrolü ────────────────────────────────────────────────
    # Veo 3.1 / Seedance videoları çoğu zaman ses akışı OLMADAN gelir.
    # Bu durumda mix yerine basit birleştirme kullan.
    has_audio = await _has_audio_stream(video_path)

    if not has_audio:
        logger.info("Video has no audio stream → falling back to simple voiceover merge")
        if progress_callback:
            await progress_callback("🔧 Adding voiceover to video (no ambient audio)...")
        return await assemble_video(video_path, voiceover_path, output_path, progress_callback)

    if progress_callback:
        await progress_callback("🔧 Mixing video ambient + voiceover...")

    # FFmpeg: 2 ses akışını mix et
    filter_complex = (
        f"[0:a]volume={bg_volume}[bg];"
        f"[1:a]volume={voice_volume}[vo];"
        f"[bg][vo]amix=inputs=2:duration=shortest[aout]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-i", voiceover_path,
        "-c:v", "copy",
        "-filter_complex", filter_complex,
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            stderr_text = stderr.decode(errors="replace")
            # Video'nun sesi yoksa veya stream eşleşmesi başarısızsa basit birleştirmeye düş
            no_audio_indicators = [
                "does not contain any stream",
                "matches no streams",
                "Invalid stream specifier",
                "Stream specifier",
                "No such filter",
                "Cannot find a matching stream",
            ]
            if any(indicator in stderr_text for indicator in no_audio_indicators):
                logger.info(f"FFmpeg mix failed (no audio stream detected), falling back to simple merge")
                return await assemble_video(video_path, voiceover_path, output_path, progress_callback)

            logger.error(f"FFmpeg mix error: {stderr_text[:500]}")
            # Son çare: basit birleştirmeyi dene (mix başarısız olduysa en azından voiceover ekle)
            logger.info("Attempting simple merge as last resort...")
            fallback_result = await assemble_video(video_path, voiceover_path, output_path, progress_callback)
            if fallback_result:
                return fallback_result
            return None

        output_size = os.path.getsize(output_path)
        logger.info(f"Mixed video assembled: {output_path} ({output_size} bytes)")
        return output_path

    except FileNotFoundError:
        logger.error("FFmpeg not found!")
        return None
    except Exception as e:
        logger.error(f"Mix assembly error: {e}")
        # Son çare fallback
        try:
            logger.info("Attempting simple merge after exception...")
            return await assemble_video(video_path, voiceover_path, output_path, progress_callback)
        except Exception as e2:
            logger.error(f"Simple merge also failed: {e2}")
            return None


def cleanup_temp_files(*paths: str):
    """Geçici dosyaları temizle."""
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
                logger.info(f"Cleaned up: {path}")
            except Exception as e:
                logger.warning(f"Cleanup failed for {path}: {e}")
