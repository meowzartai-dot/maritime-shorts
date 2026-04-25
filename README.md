# 🚢 Maritime Shorts — YouTube Shorts Otomasyon

**Durum:** 🔧 Geliştirme Aşamasında  
**Platform:** Telegram Bot + YouTube API  
**Konu:** Denizcilik (Maritime)  
**Dil:** İngilizce (başlık, açıklama, seslendirme)

---

## Açıklama

Denizcilik temalı YouTube Shorts videoları üreten, seslendiren ve otomatik yükleyen uçtan uca otomasyon sistemi.

### Pipeline Akışı

```
1. [GPT-4.1]      → Denizcilik konulu video fikri + İngilizce başlık/açıklama üret
2. [Veo 3.1]      → 9:16 sinematik AI video üret (yedek: Seedance 2.0)
3. [ElevenLabs]   → İngilizce profesyonel voiceover üret
4. [FFmpeg]        → Video + ses birleştir (ambient + voiceover mix)
5. [YouTube API]   → Otomatik yükle (public/unlisted)
6. [Telegram]      → Sonucu bildir + videoyu gönder
```

## Kullanılan Servisler

| Servis | Kullanım |
|--------|----------|
| **Telegram Bot API** | Komut arayüzü (polling) |
| **OpenAI GPT-4.1** | İçerik fikri + prompt üretimi |
| **Kie AI / Veo 3.1** | Birincil AI video üretimi |
| **Kie AI / Seedance 2.0** | Yedek AI video üretimi |
| **Kie AI / ElevenLabs** | İngilizce TTS seslendirme |
| **FFmpeg** | Video + ses birleştirme |
| **YouTube Data API v3** | Otomatik video yükleme |

## Konu Havuzu

| Kategori | Konu Sayısı |
|----------|-------------|
| 🚢 Mega Ships & Cargo | 10 |
| 🌊 Ocean Storms & Waves | 10 |
| 🏗️ Lighthouses & Navigation | 8 |
| 🐋 Marine Life & Ships | 8 |
| 🔨 Shipbuilding & Engineering | 8 |
| ⛽ Offshore & Oil Rigs | 8 |
| 🏴‍☠️ Maritime History | 8 |
| 🧊 Icebreakers & Polar Seas | 7 |
| 🎣 Commercial Fishing | 7 |
| 🏗️ Ports & Maritime Operations | 7 |
| 🔱 Submarines & Underwater | 7 |
| 🌅 Ocean Scenery & Nature | 7 |
| **TOPLAM** | **95+** |

## Telegram Komutları

| Komut | İşlev |
|-------|-------|
| `/start` | Hoş geldin + komut listesi |
| `/generate` | Rastgele denizcilik videosu üret |
| `/generate [konu]` | Belirli konuda video üret |
| `/batch [N]` | N adet video üret (max 5) |
| `/topics` | Tüm konu kategorilerini listele |
| `/credits` | Kie AI kredi bakiyesini göster |
| `/model [veo\|seedance]` | Tercih edilen modeli değiştir |

## Çalıştırma

```bash
# 1. Bağımlılıkları yükle
pip install -r requirements.txt

# 2. FFmpeg yükle (Windows)
# https://ffmpeg.org/download.html → PATH'e ekle

# 3. config.env'i doldur
# TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, KIE_API_KEY

# 4. YouTube OAuth (opsiyonel)
# Google Cloud Console → YouTube Data API v3 → OAuth 2.0 → client_secrets.json indir

# 5. Botu başlat
python bot.py
```

## Dosya Yapısı

| Dosya | Açıklama |
|-------|---------|
| `bot.py` | Ana bot + pipeline orchestrator |
| `content_engine.py` | GPT-4.1 ile İngilizce içerik üretimi |
| `video_producer.py` | Kie AI video üretim (Veo 3.1 + Seedance fallback) |
| `voice_producer.py` | ElevenLabs İngilizce voiceover |
| `video_assembler.py` | FFmpeg video + ses birleştirme |
| `youtube_uploader.py` | YouTube Data API v3 otomatik yükleme |
| `maritime_topics.py` | 95+ denizcilik konu havuzu |
| `ops_logger.py` | Operasyon loglama |
| `config.env` | API anahtarları (git'te yok) |

## Environment Variables

| Değişken | Açıklama |
|----------|----------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot tokeni |
| `OPENAI_API_KEY` | OpenAI API anahtarı |
| `KIE_API_KEY` | Kie AI API anahtarı (video + ses) |
| `ADMIN_CHAT_ID` | Admin Telegram chat ID |

## YouTube API Kurulumu

1. [Google Cloud Console](https://console.cloud.google.com) → Yeni proje oluştur
2. YouTube Data API v3'ü etkinleştir
3. OAuth consent screen yapılandır
4. OAuth 2.0 Client ID oluştur (Desktop app)
5. `client_secrets.json` indir → proje klasörüne koy
6. İlk çalıştırmada tarayıcıda yetkilendirme yap → `token.json` otomatik oluşur

> ⚠️ YouTube API günlük 10.000 birim kota sınırı vardır. Her video yükleme ~1.600 birim tüketir (~6 video/gün).
