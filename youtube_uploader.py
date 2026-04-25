"""
YouTube Uploader — YouTube Data API v3 ile otomatik video yükleme.
OAuth 2.0 ile kimlik doğrulama yapar.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# YouTube API scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# Dosya yolları
_BASE_DIR = Path(__file__).parent
CLIENT_SECRETS_FILE = _BASE_DIR / "client_secrets.json"
TOKEN_FILE = _BASE_DIR / "token.json"


def get_authenticated_service():
    """
    YouTube API servisi oluştur.
    İlk çalıştırmada OAuth tarayıcı açar, sonrası token.json kullanır.
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None

    # Mevcut token dosyasını kontrol et
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Token yoksa veya geçersizse yeniden yetkilendirme
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("YouTube token refreshed")
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}, re-authenticating...")
                creds = None

        if not creds:
            if not CLIENT_SECRETS_FILE.exists():
                raise FileNotFoundError(
                    f"❌ client_secrets.json bulunamadı!\n"
                    f"   Google Cloud Console'dan OAuth 2.0 credentials indirin:\n"
                    f"   1. https://console.cloud.google.com → APIs & Services → Credentials\n"
                    f"   2. YouTube Data API v3'ü etkinleştirin\n"
                    f"   3. OAuth 2.0 Client ID oluşturun (Desktop app)\n"
                    f"   4. JSON indirip '{CLIENT_SECRETS_FILE}' olarak kaydedin"
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRETS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=8080)
            logger.info("YouTube OAuth completed")

        # Token'ı kaydet
        TOKEN_FILE.write_text(creds.to_json())

    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] | None = None,
    category_id: str = "28",  # Science & Technology
    privacy: str = "public",
    publish_at: str | None = None,
) -> dict | None:
    """
    YouTube'a video yükle.

    Args:
        video_path: Video dosya yolu (.mp4)
        title: Video başlığı (max 100 karakter)
        description: Video açıklaması
        tags: Etiketler listesi
        category_id: YouTube kategori ID
            - "22" = People & Blogs
            - "28" = Science & Technology
            - "19" = Travel & Events
        privacy: "public", "unlisted", "private"

    Returns:
        dict: {"video_id": str, "url": str} veya None
    """
    from googleapiclient.http import MediaFileUpload

    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return None

    try:
        youtube = get_authenticated_service()

        # Başlık uzunluğunu kontrol et (YouTube max 100 karakter)
        if len(title) > 100:
            title = title[:97] + "..."

        status_dict = {
            "privacyStatus": "private" if publish_at else privacy,
            "selfDeclaredMadeForKids": False,
        }
        if publish_at:
            status_dict["publishAt"] = publish_at

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags or ["maritime", "ocean", "ships", "nautical", "marine"],
                "categoryId": category_id,
            },
            "status": status_dict,
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
        )

        logger.info(f"Uploading to YouTube: {title}")

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Upload progress: {int(status.progress() * 100)}%")

        video_id = response["id"]
        video_url = f"https://youtube.com/shorts/{video_id}"

        logger.info(f"✅ Uploaded to YouTube: {video_url}")

        return {
            "video_id": video_id,
            "url": video_url,
            "title": title,
        }

    except Exception as e:
        logger.error(f"YouTube upload error: {e}")
        return None


def check_youtube_ready() -> bool:
    """YouTube API'nin hazır olup olmadığını kontrol et (client_secrets var mı?)."""
    return CLIENT_SECRETS_FILE.exists()

if __name__ == '__main__':
    print('YouTube API baglantisi test ediliyor...')
    get_authenticated_service()
    print('Baglanti basarili! token.json olusturuldu.')
