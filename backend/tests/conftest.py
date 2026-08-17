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
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
