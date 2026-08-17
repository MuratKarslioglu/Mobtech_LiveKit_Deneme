"""Azure OpenAI STT/LLM/TTS deployment'ları için hızlı bir gecikme (latency)
ölçümü.

LiveKit odası veya mikrofon gerektirmez — `.env`'deki Azure deployment'larını
doğrudan çağırıp TTFT/toplam süreyi ölçer. V2 dokümanı bölüm 23'teki
benchmark senaryolarının ("Senaryo A: basit bilgi sorusu" vb.) hızlı, elle
tekrarlanabilir bir otomasyonudur; katman bazlı gecikmeyi görmek için
kullanılır, ses kalitesini veya konuşma tanıma doğruluğunu test etmez.

Kullanım:
    cd backend
    .venv/bin/python3.12 scripts/benchmark_providers.py
"""

from __future__ import annotations

import asyncio
import io
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from livekit import rtc  # noqa: E402
from livekit.agents import llm as llm_module  # noqa: E402

from app.config import settings  # noqa: E402
from app.providers.llm import build_llm  # noqa: E402
from app.providers.stt import build_stt  # noqa: E402
from app.providers.tts import build_tts  # noqa: E402

TEST_PROMPT = "Türkiye'nin başkenti neresi? Tek kelimeyle cevap ver."
TEST_TTS_TEXT = "Merhaba, bu bir gecikme testi."


def _fmt_ms(seconds: float | None) -> str:
    return "n/a" if seconds is None else f"{seconds * 1000:.0f} ms"


async def _benchmark_llm() -> None:
    print(f"\n[LLM] deployment={settings.azure_openai_llm_deployment}")
    try:
        instance = build_llm(settings)
        ctx = llm_module.ChatContext.empty()
        ctx.add_message(role="user", content=TEST_PROMPT)

        t0 = time.monotonic()
        stream = instance.chat(chat_ctx=ctx)
        first_token_t: float | None = None
        text = ""
        async for chunk in stream:
            if chunk.delta and chunk.delta.content:
                if first_token_t is None:
                    first_token_t = time.monotonic()
                text += chunk.delta.content
        t1 = time.monotonic()
        await stream.aclose()

        print(f"  cevap: {text.strip()!r}")
        print(f"  TTFT (ilk token): {_fmt_ms(first_token_t - t0 if first_token_t else None)}")
        print(f"  toplam süre: {_fmt_ms(t1 - t0)}")
    except Exception as exc:  # noqa: BLE001 - benchmark script'i, tek katman başarısız olursa diğerlerini engellemesin
        print(f"  HATA: {type(exc).__name__}: {exc}")


async def _benchmark_stt() -> None:
    print(f"\n[STT] deployment={settings.azure_openai_stt_deployment}")
    try:
        instance = build_stt(settings)

        # 1 saniyelik sessiz mono 16kHz ses — gerçek konuşma değil, yalnızca
        # STT çağrısının uçtan uca (network + model) süresini ölçmek için.
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"\x00\x00" * 16000)
        buf.seek(0)
        frame = rtc.AudioFrame(
            data=buf.getvalue()[44:],
            sample_rate=16000,
            num_channels=1,
            samples_per_channel=16000,
        )

        t0 = time.monotonic()
        await instance.recognize(buffer=[frame])
        t1 = time.monotonic()

        print(f"  toplam süre: {_fmt_ms(t1 - t0)}")
    except Exception as exc:  # noqa: BLE001
        print(f"  HATA: {type(exc).__name__}: {exc}")


async def _benchmark_tts() -> None:
    print(f"\n[TTS] deployment={settings.azure_openai_tts_deployment}")
    try:
        instance = build_tts(settings)
        t0 = time.monotonic()
        stream = instance.synthesize(TEST_TTS_TEXT)
        first_audio_t: float | None = None
        total_bytes = 0
        async for ev in stream:
            if first_audio_t is None:
                first_audio_t = time.monotonic()
            total_bytes += len(ev.frame.data)
        t1 = time.monotonic()
        await stream.aclose()

        print(f"  TTFA (ilk ses byte'ı): {_fmt_ms(first_audio_t - t0 if first_audio_t else None)}")
        print(f"  toplam süre: {_fmt_ms(t1 - t0)} ({total_bytes} byte)")
    except Exception as exc:  # noqa: BLE001
        print(f"  HATA: {type(exc).__name__}: {exc}")


async def main() -> None:
    print("=== Provider Latency Benchmark ===")
    await _benchmark_llm()
    await _benchmark_stt()
    await _benchmark_tts()


if __name__ == "__main__":
    asyncio.run(main())
