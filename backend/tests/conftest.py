"""Test ortamı için varsayılan (sahte) ortam değişkenleri.

`app.config` modülü import edildiği anda `load_settings()`'i çalıştırıp
zorunlu değişkenleri kontrol ediyor (bkz. app/config.py). Bu dosya, testler
toplanmadan (collection) önce çalışarak gerçek bir `.env` dosyası olmasa
bile (örn. CI ortamında) bu kontrolün geçmesini sağlıyor. Gerçek bir `.env`
zaten varsa `setdefault` onu ezmiyor.
"""

import os

os.environ.setdefault("LIVEKIT_URL", "wss://example.livekit.cloud")
os.environ.setdefault("LIVEKIT_API_KEY", "test-key")
os.environ.setdefault("LIVEKIT_API_SECRET", "test-secret")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test-key")
os.environ.setdefault("AZURE_OPENAI_LLM_DEPLOYMENT", "gpt-5-mini")
os.environ.setdefault("AZURE_OPENAI_STT_DEPLOYMENT", "gpt-4o-mini-transcribe")
os.environ.setdefault("AZURE_OPENAI_TTS_DEPLOYMENT", "tts")
