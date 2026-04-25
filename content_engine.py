"""
Content Engine — GPT-4.1 ile denizcilik konulu İngilizce içerik üretimi.
Video fikri, başlık, açıklama, prompt ve voiceover metni üretir.
"""

import json
import logging
from openai import AsyncOpenAI

from maritime_topics import get_random_topic, get_topic_from_category

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
#  GPT System Prompt — Maritime Video Content Generator
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a professional maritime content creator for a YouTube channel focusing on viral short-form videos.
Your job is to generate compelling, cinematic video concepts about maritime/nautical topics.

RULES:
1. ALL output must be in ENGLISH.
2. Titles must be SHORT (max 70 chars) and curiosity-driven. DO NOT include #Shorts or any hashtags in the title.
3. Descriptions must be SEO-optimized. DO NOT use #shorts.
4. Provide EXACTLY 5 to 8 hyper-relevant maritime tags. No more, no less.
5. The FIRST 2 SECONDS of the video prompt MUST feature an explosive, visually striking hook (fast motion, massive scale, shocking element) to capture immediate attention and stop people from scrolling.
6. Voiceover text must start with an incredibly strong, curiosity-inducing hook. Total narration must be 15-25 words.
7. Keep everything factual and educational — no clickbait lies.
8. The video prompt should describe ONE clear scene with ONE main action. Avoid complex physical interactions.

VIDEO PROMPT GUIDELINES (CRITICAL):
- The opening hook is the most important part! Emphasize the visual shock value of the first 2 seconds.
- Describe a SINGLE cinematic moment, not a story with multiple beats.
- Specify camera angle (aerial drone, low-angle, POV, wide shot).
- Specify lighting and atmosphere (fog, spray, waves, wind, dark).
- Avoid complex physical interactions that AI struggles with.
- Focus on SCALE, ATMOSPHERE, and MOTION.

Respond in this exact JSON format:
{
  "title": "Short catchy title",
  "description": "SEO-optimized description with maritime keywords",
  "tags": ["maritime", "ocean", "tag3", "tag4", "tag5", "tag6"],
  "video_prompt": "Detailed cinematic video prompt starting with an explosive 2-second visual hook...",
  "voiceover_text": "Short dramatic narration (15-25 words) starting with a mind-blowing hook.",
  "category": "topic_category_key"
}"""


async def generate_content(
    openai_client: AsyncOpenAI,
    topic: dict | None = None,
    custom_idea: str | None = None,
    category: str | None = None,
) -> dict:
    """
    GPT-4.1 ile denizcilik konulu video içeriği üret.

    Args:
        openai_client: AsyncOpenAI client
        topic: Önceden seçilmiş konu dict'i (maritime_topics'ten)
        custom_idea: Kullanıcının kendi fikri
        category: Belirli kategori key'i

    Returns:
        Dict: title, description, tags, video_prompt, voiceover_text, category
    """
    # Konu belirleme
    if custom_idea:
        user_message = f"Create a YouTube Shorts video concept about this maritime topic: {custom_idea}"
    elif topic:
        user_message = (
            f"Create a YouTube Shorts video concept based on this idea:\n"
            f"Topic: {topic['idea']}\n"
            f"Category: {topic['label']}\n"
            f"Visual style hint: {topic['style']}"
        )
    elif category:
        selected = get_topic_from_category(category)
        user_message = (
            f"Create a YouTube Shorts video concept based on this idea:\n"
            f"Topic: {selected['idea']}\n"
            f"Category: {selected['label']}\n"
            f"Visual style hint: {selected['style']}"
        )
    else:
        selected = get_random_topic()
        user_message = (
            f"Create a YouTube Shorts video concept based on this idea:\n"
            f"Topic: {selected['idea']}\n"
            f"Category: {selected['label']}\n"
            f"Visual style hint: {selected['style']}"
        )

    logger.info(f"Generating content for: {user_message[:100]}...")

    response = await openai_client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    result = json.loads(response.choices[0].message.content)

    # Validate required fields
    required_fields = ["title", "description", "tags", "video_prompt", "voiceover_text"]
    for field in required_fields:
        if field not in result or not result[field]:
            raise ValueError(f"GPT response missing required field: {field}")

    # Remove any stray hashtags from the title
    result["title"] = result["title"].replace("#shorts", "").replace("#Shorts", "").replace("#SHORTS", "").strip()

    # Ensure tags are exactly 5-8
    tags = [t.strip().lower() for t in result["tags"] if t.strip()]
    
    # Try to clean out generic shorts tags if present
    blacklist = ["shorts", "short", "ytshorts", "youtubeshorts"]
    clean_tags = [t for t in tags if t not in blacklist]
    
    # Limit to 8 maximum
    result["tags"] = clean_tags[:8]
    
    # Ensure at least 5 tags by appending generic ones if it's too short
    base_fallbacks = ["maritime", "ocean", "ships", "nautical", "marine"]
    while len(result["tags"]) < 5:
        for backup in base_fallbacks:
            if backup not in result["tags"]:
                result["tags"].append(backup)
                break

    logger.info(f"Content generated: {result['title']}")
    return result
