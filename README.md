# Türkçe Sesli Asistan (LiveKit Voice Agent)

Gerçek zamanlı, Türkçe konuşabilen bir sesli yapay zeka asistanı. LiveKit üzerinden
mikrofon sesini alır, yerel olarak (Faster-Whisper) yazıya çevirir, Google Gemini ile
cevap üretir, Gemini TTS ile sese dönüştürür ve kullanıcıya geri gönderir. Barge-in
(konuşurken araya girme) ve çoklu turn konuşma hafızası destekler.

## Project Overview

Pipeline bilinçli olarak ayrık tutulmuştur (Gemini Live gibi tek modelli
speech-to-speech kullanılmamıştır) ki her aşama (STT/LLM/TTS) ayrı ayrı
gözlemlenebilsin ve gerektiğinde tek başına değiştirilebilsin:

```
STT (Faster-Whisper, yerel) → LLM (Gemini) → TTS (Gemini TTS)
```

Proje iki parçadan oluşur:

- **Backend** (`backend/`) — Python, LiveKit Agents ile çalışan asistanın kendisi.
- **Frontend** (`frontend/`) — Next.js tabanlı, tarayıcıdan mikrofonla bağlanılan sohbet arayüzü.

## Architecture

```
                    USER
                     │ mikrofon
                     ▼
               ┌────────────┐
               │  LiveKit   │  WebRTC (ses taşıma, turn/interruption yönetimi)
               │   WebRTC   │
               └─────┬──────┘
                     │
                     ▼
               ┌────────────┐
               │    VAD     │  Silero — konuşma başlangıç/bitişini yerel olarak tespit eder
               └─────┬──────┘
                     │
                     ▼
               ┌────────────┐
               │    STT     │  Faster-Whisper (large-v3-turbo) — yerel, ücretsiz
               └─────┬──────┘
                     │ metin
                     ▼
               ┌────────────┐
               │    LLM     │  Google Gemini (Developer API)
               └─────┬──────┘
                     │ cevap metni
                     ▼
               ┌────────────┐
               │    TTS     │  Gemini TTS
               └─────┬──────┘
                     │ ses
                     ▼
               ┌────────────┐
               │  LiveKit   │
               └─────┬──────┘
                     │
                     ▼
                    USER
```

LiveKit burada LLM/STT/TTS değildir — sadece gerçek zamanlı iletişim ve
orchestration (oturum yönetimi, turn handling, interruption) katmanıdır.

## Technology Stack

| Katman | Teknoloji |
| --- | --- |
| Realtime / orchestration | LiveKit Agents 1.x, LiveKit Cloud |
| VAD | Silero (yerel) |
| STT | Faster-Whisper (yerel, `backend/app/providers/local_whisper_stt.py` içindeki özel adaptör) |
| LLM | Google Gemini Developer API (`livekit-plugins-google`) |
| TTS | Gemini TTS (`google.beta.GeminiTTS`) |
| Backend dili | Python 3.12 |
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS + `@livekit/components-react` |

## Requirements

- Python 3.11 veya 3.12 (3.13+ paket uyumluluğu garanti değil)
- Node.js 20+ ve npm (frontend için)
- Ücretsiz bir [LiveKit Cloud](https://cloud.livekit.io) projesi
- Ücretsiz bir [Google AI Studio](https://aistudio.google.com/apikey) API key'i
- macOS/Linux/Windows — CUDA yoksa (örn. Apple Silicon) otomatik CPU'ya düşer

## Installation

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

İlk çalıştırmada Faster-Whisper modeli (`large-v3-turbo`, ~1.5GB) otomatik indirilir.

### Frontend

```bash
cd frontend
npm install
```

## Environment Variables

`backend/.env` (backend için) ve `frontend/.env.local` (frontend için)
oluşturulmalı — ikisi de aynı LiveKit bilgilerini kullanır.

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

`backend/.env` içeriği:

```env
# LiveKit
LIVEKIT_URL=wss://senin-projen.livekit.cloud
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=

# Google Gemini API
GOOGLE_API_KEY=

# Application
APP_LANGUAGE=tr
LOG_LEVEL=INFO

# Faster-Whisper (STT)
WHISPER_MODEL=large-v3-turbo
WHISPER_DEVICE=auto

# Gemini model isimleri (kod içine hardcode edilmez)
GEMINI_LLM_MODEL=gemini-3.5-flash-lite
GEMINI_TTS_MODEL=gemini-2.5-flash-preview-tts
```

`frontend/.env.local` sadece LiveKit değerlerini içerir (aynı üç satır).

Gerçek secret değerleri **hiçbir zaman** git'e commit edilmemelidir — `.gitignore`
hem `.env` hem `frontend/.env*.local` dosyalarını dışlıyor.

## LiveKit Setup

1. [cloud.livekit.io](https://cloud.livekit.io) üzerinde ücretsiz hesap oluştur.
2. Otomatik oluşan projeyi kullan (ya da yeni proje aç).
3. **Settings → API Keys**'ten bir `API Key` / `API Secret` çifti al.
4. **Settings → Project**'ten `wss://...livekit.cloud` formatındaki Project URL'i al.
5. Bu üç değeri `backend/.env` ve `frontend/.env.local`'a yaz.

Free tier bu proje için yeterlidir, kredi kartı gerekmez.

## Google AI Studio Setup

1. [aistudio.google.com/apikey](https://aistudio.google.com/apikey) adresine git.
2. **Create API key** → "Create API key in new project".
3. Oluşan key'i `backend/.env`'deki `GOOGLE_API_KEY`'e yaz.

Bu key varsayılan olarak **free tier**'dadır; sen manuel olarak billing açmadıkça
ücretli plana geçmez.

## Running Locally

İki terminal gerekir:

**Terminal 1 — backend:**

```bash
cd backend
source .venv/bin/activate
python -m app.agent dev
```

`registered worker` log satırını görürsen backend hazırdır. (Alternatif:
`python -m app.agent console` — tarayıcı/frontend olmadan doğrudan terminalden,
bilgisayarının mikrofon/hoparlörüyle test etmek için.)

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

Tarayıcıda **http://localhost:3000** aç, "Bağlan"a bas, mikrofon iznini onayla.

## Testing

```bash
cd backend
python -m pytest
```

Testler gerçek bir LiveKit/Gemini bağlantısı açmaz; config yükleme, cihaz
seçim mantığı (`WHISPER_DEVICE=auto` çözümlemesi) ve provider/agent
kurulumunun (wiring) hatasız çalıştığını doğrulayan hızlı smoke test'lerdir.

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agent.py                   # LiveKit entrypoint, event/log kablolaması
│   │   ├── config.py                  # .env yükleme + doğrulama
│   │   ├── providers/
│   │   │   ├── local_whisper_stt.py   # Faster-Whisper → LiveKit STT adaptörü
│   │   │   ├── llm.py                 # Gemini LLM fabrikası
│   │   │   └── tts.py                 # Gemini TTS fabrikası
│   │   └── prompts/
│   │       └── system.py              # Sistem promptu
│   ├── tests/                         # Smoke test'ler
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.tsx                   # Sohbet arayüzü
│   │   └── api/token/route.ts         # LiveKit token endpoint'i
│   └── .env.local.example
└── README.md
```

## Known Limitations

- **Gemini free-tier hız sınırları** — özellikle TTS modeli dakikada birkaç
  istekle sınırlı olabiliyor; art arda çok hızlı test edilirse `429` hataları
  görülebilir (uygulama çökmez, sadece o turda ses üretilemez, LLM cevabı yine de
  görünür).
- **STT streaming değil** — Faster-Whisper konuşma bitince tüm turu tek seferde
  işliyor; kelime kelime canlı transkript yok (spec'in bilinçli tercihi, bkz. görev
  tanımı bölüm 16).
- **Persistent hafıza yok** — konuşma geçmişi sadece o oturum (LiveKit session)
  boyunca tutuluyor, kapatılınca sıfırlanıyor.
- **`dev` modu deprecated uyarısı veriyor** — LiveKit uzun vadede `lk agent dev`
  (ayrı bir CLI aracı) öneriyor; `python -m app.agent dev` hâlâ çalışıyor ve
  bu proje kapsamında bilinçli olarak tercih edildi (ekstra araç kurulumu
  gerektirmiyor).

## Future Improvements

- Next.js frontend'e latency göstergesi eklemek (şu an sadece backend
  terminalinde `[LATENCY]` logu var, arayüze taşınmadı).
- `lk agent dev`/production deployment'a geçiş.
- LLM/STT/TTS için fallback provider'lar (spec'in öngördüğü, ama MVP'de
  zorunlu tutulmayan provider-değiştirilebilirlik).
- Gerçek streaming STT (kelime kelime canlı transkript).
