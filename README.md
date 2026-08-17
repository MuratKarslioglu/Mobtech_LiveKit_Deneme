# Türkçe Sesli Asistan (LiveKit Voice Agent)

Gerçek zamanlı, Türkçe konuşabilen bir sesli yapay zeka asistanı. LiveKit
üzerinden mikrofon sesini alır, Azure OpenAI ile yazıya çevirir, yine Azure
OpenAI ile cevap üretir ve sese dönüştürüp kullanıcıya geri gönderir.
Barge-in (konuşurken araya girme), çoklu turn konuşma hafızası, tool/function
calling ve uzun süren işlemlerde ara ("interim") sesli bildirim destekler.

## Project Overview

Pipeline bilinçli olarak ayrık tutulmuştur (tek modelli speech-to-speech
kullanılmamıştır) ki her aşama (STT/LLM/TTS) ayrı ayrı gözlemlenebilsin ve
gerektiğinde tek başına değiştirilebilsin:

```
STT (Azure OpenAI transcribe) → LLM (Azure OpenAI chat) → TTS (Azure OpenAI)
```

Üçü de **tek bir Azure OpenAI / Azure AI Foundry kaynağı** altında ayrı
deployment'lar olarak barınıyor — aynı endpoint/API key'i paylaşırlar.

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
               │    STT     │  Azure OpenAI transcribe deployment (örn. gpt-4o-mini-transcribe)
               └─────┬──────┘
                     │ metin
                     ▼
               ┌────────────┐
               │    LLM     │  Azure OpenAI chat deployment
               └─────┬──────┘
                     │ cevap metni (TextChunkBuffer ile parçalara bölünür)
                     ▼
               ┌────────────┐
               │    TTS     │  Azure OpenAI tts deployment
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

Bir `ResponseOrchestrator` katmanı, LLM/tool işlemi konfigüre edilen
eşikten (`INTERIM_RESPONSE_THRESHOLD_MS`) uzun sürerse kullanıcıya kısa bir
ara mesaj ("Bir saniye, düşünüyorum." veya tool'a özel bir mesaj, örn.
"Hesaplamayı yapıyorum.") söyletir; kullanıcı araya girerse (veya asistanın
turu zaten bitmişse) bunu ve bekleyen görevleri `CancellationManager` ile
iptal eder.

Asistanın kendi TTS çıktısının mikrofona sızıp STT'de "hayalet" bir tur
başlatmasına karşı iki katmanlı bir önlem var: (1) LiveKit'in BVC (Background
Voice Cancellation) ses filtresi, konuşmacı-dışı sesleri ses seviyesinde
bastırır; (2) `VoiceAgent.stt_node`, kısa (tek kelime) ve asistanın az önce
söylediğiyle yüksek oranda örtüşen ("self-echo") final transkriptleri
metin seviyesinde eler.

## Technology Stack

| Katman | Teknoloji |
| --- | --- |
| Realtime / orchestration | LiveKit Agents 1.x, LiveKit Cloud |
| VAD | Silero (yerel) |
| Echo/gürültü bastırma | LiveKit BVC (`livekit-plugins-noise-cancellation`) |
| STT | Azure OpenAI transcribe deployment (`livekit-plugins-openai`, `openai.STT.with_azure`) |
| LLM | Azure OpenAI chat deployment (`openai.LLM.with_azure`, `reasoning_effort="minimal"`) |
| TTS | Azure OpenAI tts deployment (`openai.TTS.with_azure`) |
| Backend dili | Python 3.12 |
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS + `@livekit/components-react` |

## Requirements

- Python 3.11 veya 3.12 (3.13+ paket uyumluluğu garanti değil)
- Node.js 20+ ve npm (frontend için)
- Ücretsiz bir [LiveKit Cloud](https://cloud.livekit.io) projesi
- Bir Azure OpenAI / Azure AI Foundry kaynağı — chat, transcribe ve tts için
  üç ayrı deployment (bkz. [Azure OpenAI Setup](#azure-openai-setup))

## Installation

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

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

# Application
APP_LANGUAGE=tr
LOG_LEVEL=INFO

# Azure OpenAI / Azure AI Foundry — tek bir kaynak, üç ayrı deployment
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_LLM_DEPLOYMENT=
AZURE_OPENAI_STT_DEPLOYMENT=
AZURE_OPENAI_TTS_DEPLOYMENT=

# Bir tool/LLM işlemi bu süreden (ms) uzun sürerse ara mesaj söylenir
INTERIM_RESPONSE_THRESHOLD_MS=2500
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

## Azure OpenAI Setup

Bu proje, LLM + STT + TTS için **tek bir** Azure OpenAI / Azure AI Foundry
kaynağı kullanır (üç ayrı deployment, aynı endpoint/key):

1. Azure AI Foundry portalında kaynağın **endpoint**'ini (örn.
   `https://<kaynak-adı>.services.ai.azure.com`) ve **API key**'ini al.
2. "Deployments" sekmesinden üç deployment'ın tam adını not et:
   - Chat/LLM modeli (örn. `gpt-5-mini`, `gpt-4o-mini`)
   - Transcribe/STT modeli (örn. `gpt-4o-mini-transcribe`)
   - TTS modeli (örn. `tts-1`, `tts-1-hd`)
3. Bu bilgileri `backend/.env`'deki `AZURE_OPENAI_*` alanlarına yaz.

**Bilinen bir gotcha:** `AZURE_OPENAI_API_VERSION`'ın `audio/speech` (TTS)
route'unu desteklemesi gerekiyor — klasik GA sürümleri (örn. `2024-10-21`)
`404 Resource not found` verebilir; `2024-08-01-preview` gibi bir preview
sürümü hem chat hem transcribe hem TTS için çalışıyor (bu proje bunu
varsayılan olarak kullanıyor). TTS deployment'ının izin verdiği ses adları
da kısıtlı olabilir (`400 invalid voice` hatası verirse Azure portalında
deployment'ın desteklediği sesleri kontrol et).

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

Testler gerçek bir LiveKit/Azure bağlantısı açmaz; config yükleme ve
provider/agent kurulumunun (wiring) hatasız çalıştığını doğrulayan hızlı
smoke test'lerdir.

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agent.py                   # LiveKit entrypoint, event/log kablolaması, VoiceAgent
│   │   ├── config.py                  # .env yükleme + doğrulama
│   │   ├── providers/
│   │   │   ├── stt.py                 # Azure OpenAI transcribe → LiveKit STT
│   │   │   ├── llm.py                 # Azure OpenAI chat → LiveKit LLM
│   │   │   └── tts.py                 # Azure OpenAI tts → LiveKit TTS
│   │   ├── orchestration/
│   │   │   ├── response_orchestrator.py     # Turn lifecycle koordinasyonu
│   │   │   ├── interim_response_manager.py  # "Bir saniye, düşünüyorum" zamanlayıcısı
│   │   │   └── cancellation_manager.py      # Barge-in'de aktif görevleri iptal
│   │   ├── streaming/
│   │   │   └── text_chunk_buffer.py   # LLM çıktısını TTS için cümle parçalarına böler
│   │   ├── tools/
│   │   │   ├── registry.py            # Tool kayıt/keşif
│   │   │   └── math_tools.py          # add_numbers örnek tool'u
│   │   ├── models/
│   │   │   └── tool_config.py         # Tool metadata (interim mesajı vb.)
│   │   └── prompts/
│   │       └── system.py              # Sistem promptu
│   ├── scripts/
│   │   └── benchmark_providers.py     # Mikrofonsuz, hızlı gecikme ölçümü
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

- **Persistent hafıza yok** — konuşma geçmişi sadece o oturum (LiveKit session)
  boyunca tutuluyor, kapatılınca sıfırlanıyor.
- **STT halüsinasyonu riski** — Azure OpenAI'ın transcribe modeli (Whisper
  ailesi gibi) üretken bir modeldir; ortam gürültüsünü veya asistanın kendi
  TTS çıktısının mikrofona sızmasını konuşma sanıp var olmayan bir metin
  üretebilir ("self-echo"). Bunu azaltmak için iki katmanlı bir önlem var: (1)
  LiveKit'in BVC ses filtresi konuşmacı-dışı sesleri ses seviyesinde bastırır,
  (2) `VoiceAgent.stt_node`'daki word-count + self-echo-benzerliği filtresi
  (`ECHO_SIMILARITY_THRESHOLD`, `ECHO_RECENCY_WINDOW_S`, `MIN_TRANSCRIPT_WORDS`,
  bkz. `app/agent.py`) şüpheli transkriptleri metin seviyesinde eler — self-echo
  kontrolü yalnızca asistan son birkaç saniye içinde konuştuysa uygulanır, yoksa
  gerçek/güncel bir kullanıcı cevabı yanlışlıkla elenmesin diye. VAD
  `activation_threshold` bilinçli olarak kütüphane varsayılanında (0.5)
  bırakıldı — daha yüksek bir eşik gerçek konuşmayı da kaçırma riskini
  artırır. Risk tamamen sıfır değildir; hâlâ yaşanıyorsa eşik değerleri
  gerçek kullanım verisine göre ayarlanabilir.
- **Tek kelimelik cevaplar kaybedilebilir** — `MIN_TRANSCRIPT_WORDS=2` filtresi
  ("Evet", "Tamam", "Dur" gibi tek kelimelik gerçek cevapları da) şüpheli kısa
  transkript sayıp eler; bu, halüsinasyon/self-echo yanlış tetiklenmesini
  önlemek için bilinçli bir ödünleşim. "Sistem beni duymadı" hissi yaşarsan,
  söylediğin şeyin tek kelimeden ibaret olup olmadığını kontrol et — backend
  logunda `[STT] şüpheli kısa transkript ... göz ardı edildi` satırı bunu
  doğrular.
- **Ses/şive tutarlılığı** — Azure OpenAI TTS sesleri (nova, shimmer, echo,
  onyx, fable, alloy) genel amaçlı, Türkçeye özel eğitilmemiş sesler; telaffuz
  bazen doğal olmayabilir. Deployment'ın izin verdiği sesler arasında
  denenip en iyi sonuç veren seçilebilir (`app/providers/tts.py`).
- **`dev` modu deprecated uyarısı veriyor** — LiveKit uzun vadede `lk agent dev`
  (ayrı bir CLI aracı) öneriyor; `python -m app.agent dev` hâlâ çalışıyor ve
  bu proje kapsamında bilinçli olarak tercih edildi (ekstra araç kurulumu
  gerektirmiyor).
- **Interim mesaj sıralaması (LiveKit SDK sınırlaması)** — `session.say()`
  ile tetiklenen "Bir saniye, düşünüyorum." mesajı, asıl LLM cevabıyla aynı
  önceliğe sahip tek bir FIFO konuşma kuyruğuna giriyor; asıl cevabın
  SpeechHandle'ı kullanıcının turu onaylandığı anda (LLM ilk token'ı
  üretmeden önce) kuyruğa zaten girdiği için interim mesajı ne zaman
  tetiklenirse tetiklensin kuyrukta HER ZAMAN asıl cevabın arkasına düşer.
  LiveKit'in genel `say()` API'si bir öncelik parametresi dışarı açmıyor, bu
  yüzden bu davranış kod tarafında düzeltilemiyor — tek pratik önlem,
  `INTERIM_RESPONSE_THRESHOLD_MS`'i tipik LLM TTFT'sinin belirgin üstünde
  tutarak (varsayılan 2500ms) mesajın neredeyse hiç tetiklenmemesini
  sağlamak (bkz. `app/config.py`).

## Deployment

Geliştirme sırasında `python -m app.agent dev` yeterli. Production için
LiveKit'in kendi CLI'ı (`lk`) kurulup:

```bash
lk agent create   # ilk kurulumda, proje ile agent'ı ilişkilendirir
lk agent deploy   # her deploy'da
```

kullanılır. Detaylar için [LiveKit Cloud Agents dokümantasyonu](https://docs.livekit.io/agents/ops/deployment/).
Bu depo kapsamında ayrı bir HTTP health-check endpoint'i eklenmedi — LiveKit
worker zaten kendi bağlantı/registration durumunu loglar, ayrı bir web
sunucusu değildir.

## Benchmark

```bash
cd backend
python scripts/benchmark_providers.py
```

`.env`'deki Azure deployment'larını, gerçek bir LiveKit odası/mikrofon
açmadan doğrudan çağırıp TTFT (ilk token/ses byte'ı) ve toplam süreyi ölçer.
Uçtan uca (mikrofon → kulak) gerçek deneyimi karşılaştırmak için aşağıdaki
senaryoları `python -m app.agent console` ile elle tekrarlayın:

| Senaryo | Açıklama |
| --- | --- |
| A | Basit bilgi sorusu ("Türkiye'nin başkenti neresi?") |
| B | `add_numbers` tool'unu tetikleyen bir istek ("125 ile 348'i topla") |
| C | Uzun sürmesi beklenen bir işlem (interim mesajın tetiklenip tetiklenmediğini gözlemleyin) |
| D | Asistan konuşurken araya girme (barge-in) |
| E | Art arda hızlı konuşma turları |

## Future Improvements

- Next.js frontend'e latency göstergesi eklemek (şu an sadece backend
  terminalinde `[LATENCY]` logu var, arayüze taşınmadı).
- Gerçek streaming STT (kelime kelime canlı transkript) — şu an Azure OpenAI
  transcribe deployment'ı turn-bazlı çalışıyor. Bunun için ayrı bir Azure AI
  Speech kaynağına (`livekit-plugins-azure`, gerçek partial/final transcript
  destekli) geçiş değerlendirilebilir; bu depoda bilinçli olarak ertelendi
  çünkü ek bir Azure kaynağı/kimlik bilgisi gerektiriyor.
- Provider fallback (örn. ikinci bir Azure deployment'a otomatik geçiş) —
  bilinçli olarak kapsam dışı bırakıldı, tek kaynağa odaklanmak tercih edildi.
- `Agent.llm_node`'un LLM/TTS task'larını tam olarak sarmalayıp
  `CancellationManager`'a `track()` etmesi (V2 dokümanı Faz 4) — şu an
  barge-in tamamen LiveKit SDK'sının kendi interruption mekanizmasına
  dayanıyor, `CancellationManager` yalnızca interim zamanlayıcıyı izliyor.
