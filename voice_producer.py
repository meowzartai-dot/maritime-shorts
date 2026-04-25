"""
Voice Producer — ElevenLabs TTS ile İngilizce seslendirme üretimi.
Kie AI wrapper üzerinden çalışır (ayrı ElevenLabs key'e gerek yok).
"""

import json
import asyncio
import logging
import tempfile

import httpx

logger = logging.getLogger(__name__)

CREATE_URL = "https://api.kie.ai/api/v1/jobs/createTask"
POLL_URL = "https://api.kie.ai/api/v1/jobs/recordInfo"

# Denizcilik belgeseli için ideal sesler
VOICES = {
    "daniel": {"name": "Daniel", "desc": "Male, professional narrator — documentary style"},
    "callum": {"name": "Callum", "desc": "Male, deep authoritative — cinematic epic"},
    "charlie": {"name": "Charlie", "desc": "Male, natural warm — educational content"},
    "rachel": {"name": "Rachel", "desc": "Female, warm engaging — storytelling"},
    "liam": {"name": "Liam", "desc": "Male, young dynamic — energetic content"},
}

DEFAULT_VOICE = "Daniel"


def _auth_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


async def produce_voice(
    api_key: str,
    text: str,
    voice: str = DEFAULT_VOICE,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    speed: float = 1.0,
    progress_callback=None,
) -> dict:
    """
    ElevenLabs ile İngilizce seslendirme üret.

    Args:
        api_key: Kie AI API key
        text: İngilizce voiceover metni
        voice: Ses ismi (Daniel, Callum, Charlie, Rachel, Liam)
        stability: 0.0-1.0, yüksek = tutarlı
        similarity_boost: 0.0-1.0, sese benzerlik
        speed: konuşma hızı
        progress_callback: async callable(message: str)

    Returns:
        dict: {"url": str, "path": str | None}
    """
    if progress_callback:
        await progress_callback("🎙️ Generating English voiceover...")

    # ── Görev oluştur ────────────────────────────────────────────────────
    payload = {
        "model": "elevenlabs/text-to-speech-multilingual-v2",
        "input": {
            "text": text,
            "voice": voice,
            "stability": stability,
            "similarity_boost": similarity_boost,
            "speed": speed,
        },
    }

    task_id = None
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                CREATE_URL,
                headers=_auth_headers(api_key),
                json=payload,
            )
            logger.info(f"ElevenLabs submit status: {resp.status_code}")
            body = resp.json()
            resp.raise_for_status()

            task_id = body.get("data", {}).get("taskId")
            if task_id:
                logger.info(f"ElevenLabs taskId: {task_id}")
            else:
                logger.error(f"ElevenLabs taskId not found: {body}")
                return {"url": None, "path": None}

        except Exception as e:
            logger.error(f"ElevenLabs submit error: {e}")
            return {"url": None, "path": None}

    # ── Sonucu poll et ───────────────────────────────────────────────────
    audio_url = None
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(30):  # ~5 dakika max
            await asyncio.sleep(10)
            try:
                resp = await client.get(
                    f"{POLL_URL}?taskId={task_id}",
                    headers=_auth_headers(api_key),
                )

                if resp.status_code != 200:
                    continue

                body = resp.json()
                data = body.get("data", {})
                state = data.get("state", "")
                logger.info(f"ElevenLabs poll [{attempt+1}/30] state={state}")

                if state == "success":
                    result_json = data.get("resultJson")
                    if result_json:
                        try:
                            parsed = json.loads(result_json) if isinstance(result_json, str) else result_json
                            urls = parsed.get("resultUrls", [])
                            if urls:
                                audio_url = urls[0]
                                logger.info(f"ElevenLabs audio ready: {audio_url}")
                                break
                        except Exception:
                            pass

                    # resultUrls doğrudan
                    result_urls = data.get("resultUrls", [])
                    if result_urls:
                        audio_url = result_urls[0]
                        break

                    logger.error(f"ElevenLabs success but no URL: {data}")
                    break

                elif state in ("failed", "fail"):
                    fail_msg = data.get("failMsg", "Unknown error")
                    logger.error(f"ElevenLabs failed: {fail_msg}")
                    break

            except Exception as e:
                logger.error(f"ElevenLabs poll error: {e}")

    # ── İndir ────────────────────────────────────────────────────────────
    audio_path = None
    if audio_url:
        audio_path = await _download_audio(audio_url)

    return {"url": audio_url, "path": audio_path}


async def _download_audio(url: str) -> str | None:
    """Ses dosyasını indir."""
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            suffix = ".mp3" if "mp3" in url.lower() else ".wav"
            tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            tmp.write(resp.content)
            tmp.close()
            logger.info(f"Audio downloaded: {len(resp.content)} bytes → {tmp.name}")
            return tmp.name
        except Exception as e:
            logger.error(f"Audio download error: {e}")
            return None
