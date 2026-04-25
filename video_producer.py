"""
Video Producer — Kie AI üzerinden video üretimi.
Birincil: Veo 3.1 (sinematik, yüksek kalite)
Yedek: Seedance 2.0 (uygun fiyat)
"""

import json
import asyncio
import logging
import tempfile

import httpx

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
#  Veo 3.1 — Birincil Video Üretim Motoru
# ══════════════════════════════════════════════════════════════════════════════

VEO_GENERATE_URL = "https://api.kie.ai/api/v1/veo/generate"
VEO_POLL_URL = "https://api.kie.ai/api/v1/veo/record-info"

# ══════════════════════════════════════════════════════════════════════════════
#  Seedance 2.0 — Yedek Video Üretim Motoru
# ══════════════════════════════════════════════════════════════════════════════

SEEDANCE_CREATE_URL = "https://api.kie.ai/api/v1/jobs/createTask"
SEEDANCE_POLL_URL = "https://api.kie.ai/api/v1/jobs/recordInfo"


def _auth_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


# ── Veo 3.1 ─────────────────────────────────────────────────────────────────

async def veo_submit(api_key: str, prompt: str) -> str | None:
    """Veo 3.1'e video üretim isteği gönder. taskId döndürür."""
    payload = {
        "model": "veo3_fast",
        "prompt": prompt,
        "aspect_ratio": "9:16",
        "mode": "TEXT_2_VIDEO",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                VEO_GENERATE_URL,
                headers=_auth_headers(api_key),
                json=payload,
            )
            logger.info(f"Veo submit status: {resp.status_code}")
            body = resp.json()
            logger.info(f"Veo submit response: {json.dumps(body, ensure_ascii=False)[:500]}")
            resp.raise_for_status()

            # taskId'yi çıkar
            task_id = None
            if isinstance(body.get("data"), dict):
                task_id = body["data"].get("taskId")
            elif isinstance(body.get("data"), str):
                task_id = body["data"]

            if task_id:
                logger.info(f"Veo taskId: {task_id}")
            else:
                logger.error(f"Veo taskId bulunamadı: {body}")
            return task_id

        except Exception as e:
            logger.error(f"Veo submit error: {e}")
            return None


async def veo_poll(api_key: str, task_id: str, max_attempts: int = 60) -> str | None:
    """Veo 3.1 sonucunu poll et. Video URL döndürür."""
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(max_attempts):
            await asyncio.sleep(10)
            try:
                resp = await client.get(
                    f"{VEO_POLL_URL}?taskId={task_id}",
                    headers=_auth_headers(api_key),
                )

                if resp.status_code != 200:
                    logger.warning(f"Veo poll [{attempt+1}/{max_attempts}] status={resp.status_code}")
                    continue

                body = resp.json()
                data = body.get("data") or body
                
                # State kontrolü
                state = data.get("state", "")
                logger.info(f"Veo poll [{attempt+1}/{max_attempts}] state={state}")

                if state == "success" or data.get("successFlag") == 1:
                    # Video URL'i bul
                    video_url = data.get("video_url")
                    if not video_url:
                        # resultUrls dene
                        result_urls = data.get("resultUrls", [])
                        if not result_urls and "response" in data:
                            result_urls = data.get("response", {}).get("resultUrls", [])
                            
                        if result_urls:
                            video_url = result_urls[0]
                    if not video_url:
                        # resultJson parse et
                        result_json = data.get("resultJson")
                        if result_json:
                            try:
                                parsed = json.loads(result_json) if isinstance(result_json, str) else result_json
                                urls = parsed.get("resultUrls", [])
                                if urls:
                                    video_url = urls[0]
                            except Exception:
                                pass

                    if video_url:
                        logger.info(f"Veo video ready: {video_url}")
                        return video_url
                    else:
                        logger.error(f"Veo success but no URL found: {data}")
                        return None

                elif state in ("failed", "fail"):
                    fail_msg = data.get("failMsg", "Unknown error")
                    logger.error(f"Veo failed: {fail_msg}")
                    return None

                # processing / waiting → devam et

            except Exception as e:
                logger.error(f"Veo poll error: {e}")

    logger.warning("Veo timeout")
    return None


# ── Seedance 2.0 (Fallback) ────────────────────────────────────────────────

async def seedance_submit(api_key: str, prompt: str) -> str | None:
    """Seedance 2.0'a video üretim isteği gönder. taskId döndürür."""
    payload = {
        "model": "bytedance/seedance-2",
        "input": {
            "prompt": prompt,
            "resolution": "720p",
            "aspect_ratio": "9:16",
            "duration": 8,
            "generate_audio": True,
            "web_search": False,
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                SEEDANCE_CREATE_URL,
                headers=_auth_headers(api_key),
                json=payload,
            )
            logger.info(f"Seedance submit status: {resp.status_code}")
            body = resp.json()
            resp.raise_for_status()

            data_obj = body.get("data") or {}
            task_id = data_obj.get("taskId")
            if not task_id:
                task_id = body.get("taskId") # Top level fallback
                
            if task_id:
                logger.info(f"Seedance taskId: {task_id}")
            else:
                logger.error(f"Seedance taskId bulunamadı: {body}")
            return task_id

        except Exception as e:
            logger.error(f"Seedance submit error: {e}")
            return None


async def seedance_poll(api_key: str, task_id: str, max_attempts: int = 60) -> str | None:
    """Seedance 2.0 sonucunu poll et. Video URL döndürür."""
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(max_attempts):
            await asyncio.sleep(10)
            try:
                resp = await client.get(
                    f"{SEEDANCE_POLL_URL}?taskId={task_id}",
                    headers=_auth_headers(api_key),
                )

                if resp.status_code != 200:
                    logger.warning(f"Seedance poll [{attempt+1}/{max_attempts}] status={resp.status_code}")
                    continue

                body = resp.json()
                data = body.get("data", {})
                state = data.get("state", "")
                logger.info(f"Seedance poll [{attempt+1}/{max_attempts}] state={state}")

                if state == "success":
                    result_json = data.get("resultJson")
                    if result_json:
                        try:
                            parsed = json.loads(result_json) if isinstance(result_json, str) else result_json
                            urls = parsed.get("resultUrls", [])
                            if urls:
                                logger.info(f"Seedance video ready: {urls[0]}")
                                return urls[0]
                        except Exception:
                            pass
                    logger.error(f"Seedance success but no URL: {data}")
                    return None

                elif state in ("failed", "fail"):
                    fail_msg = data.get("failMsg", "Unknown error")
                    logger.error(f"Seedance failed: {fail_msg}")
                    return None

            except Exception as e:
                logger.error(f"Seedance poll error: {e}")

    logger.warning("Seedance timeout")
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  Unified Video Production — Veo → Seedance Fallback
# ══════════════════════════════════════════════════════════════════════════════

async def produce_video(
    api_key: str,
    prompt: str,
    prefer_model: str = "veo",
    progress_callback=None,
) -> dict:
    """
    Video üret: Veo 3.1 dene, başarısızsa Seedance 2.0'a fallback.

    Args:
        api_key: Kie AI API key
        prompt: İngilizce video prompt
        prefer_model: "veo" veya "seedance"
        progress_callback: async callable(message: str), ilerleme bildirimi

    Returns:
        dict: {"url": str, "model": str, "path": str | None}
    """
    video_url = None
    used_model = None

    # ── Birincil model ───────────────────────────────────────────────────
    if prefer_model == "veo":
        if progress_callback:
            await progress_callback("🎥 Generating video with Veo 3.1...")

        task_id = await veo_submit(api_key, prompt)
        if task_id:
            video_url = await veo_poll(api_key, task_id)
            if video_url:
                used_model = "Veo 3.1"

        # Fallback → Seedance
        if not video_url:
            logger.info("Veo failed, falling back to Seedance 2.0")
            if progress_callback:
                await progress_callback("⚡ Switching to Seedance 2.0...")

            task_id = await seedance_submit(api_key, prompt)
            if task_id:
                video_url = await seedance_poll(api_key, task_id)
                if video_url:
                    used_model = "Seedance 2.0"

    elif prefer_model == "seedance":
        if progress_callback:
            await progress_callback("🎥 Generating video with Seedance 2.0...")

        task_id = await seedance_submit(api_key, prompt)
        if task_id:
            video_url = await seedance_poll(api_key, task_id)
            if video_url:
                used_model = "Seedance 2.0"

        # Fallback → Veo
        if not video_url:
            logger.info("Seedance failed, falling back to Veo 3.1")
            if progress_callback:
                await progress_callback("⚡ Switching to Veo 3.1...")

            task_id = await veo_submit(api_key, prompt)
            if task_id:
                video_url = await veo_poll(api_key, task_id)
                if video_url:
                    used_model = "Veo 3.1"

    # ── Videoyu indir ────────────────────────────────────────────────────
    video_path = None
    if video_url:
        video_path = await _download_file(video_url, suffix=".mp4")

    return {
        "url": video_url,
        "model": used_model,
        "path": video_path,
    }


async def _download_file(url: str, suffix: str = ".mp4") -> str | None:
    """URL'den dosya indir, geçici dosya yolu döndür."""
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            tmp.write(resp.content)
            tmp.close()
            logger.info(f"Downloaded {len(resp.content)} bytes → {tmp.name}")
            return tmp.name
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None


async def check_credits(api_key: str) -> dict | None:
    """Kie AI kredi bakiyesini sorgula."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                "https://api.kie.ai/api/v1/chat/credit",
                headers=_auth_headers(api_key),
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Credit check error: {e}")
            return None
