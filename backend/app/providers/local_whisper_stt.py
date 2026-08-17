from __future__ import annotations

import asyncio
import io
import logging
import platform
import shutil

from faster_whisper import WhisperModel
from livekit import rtc
from livekit.agents import stt, vad as vad_module
from livekit.agents.types import NOT_GIVEN, APIConnectOptions, NotGivenOr
from livekit.agents.utils import AudioBuffer

from ..config import Settings

logger = logging.getLogger("voice-agent.stt")


def _detect_cuda() -> bool:
    if platform.system() == "Darwin":
        # Apple Silicon / Intel Mac: CUDA yok, varsaymıyoruz.
        return False
    return shutil.which("nvidia-smi") is not None


def _resolve_device(device: str) -> tuple[str, str]:
    """WHISPER_DEVICE değerini (auto/cpu/cuda) gerçek (device, compute_type) çiftine çevirir."""
    resolved = _detect_cuda() if device == "auto" else (device == "cuda")
    if resolved:
        return "cuda", "float16"
    return "cpu", "int8"


class FasterWhisperSTT(stt.STT):
    """Faster-Whisper'ı LiveKit'in STT arayüzüne saran, tamamen yerel çalışan adaptör.

    Streaming değil: bir konuşma turu bitince (VAD tespit edince) tüm ses buffer'ı
    tek seferde Whisper'a gönderilir. StreamAdapter bu sınıfı VAD ile birleştirerek
    AgentSession'ın beklediği streaming arayüze uydurur.
    """

    def __init__(self, *, model_size: str, device: str, language: str) -> None:
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=False, interim_results=False)
        )
        resolved_device, compute_type = _resolve_device(device)
        logger.info(
            "Faster-Whisper modeli yükleniyor: model=%s device=%s compute_type=%s",
            model_size,
            resolved_device,
            compute_type,
        )
        self._model = WhisperModel(model_size, device=resolved_device, compute_type=compute_type)
        self._language = language

    @property
    def model(self) -> str:
        return "faster-whisper"

    @property
    def provider(self) -> str:
        return "local"

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        wav_bytes = rtc.combine_audio_frames(buffer).to_wav_bytes()

        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, self._transcribe, wav_bytes)

        if not text.strip():
            # Boş/algılanamayan konuşma: alternatives boş bırakılır ki AgentSession
            # bunu geçerli bir kullanıcı turu sayıp LLM'i boşuna çağırmasın.
            return stt.SpeechEvent(type=stt.SpeechEventType.FINAL_TRANSCRIPT, alternatives=[])

        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(language=self._language, text=text)],
        )

    def _transcribe(self, wav_bytes: bytes) -> str:
        segments, _ = self._model.transcribe(
            io.BytesIO(wav_bytes),
            language=self._language,
            beam_size=5,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()


def build_stt(settings: Settings, vad: vad_module.VAD) -> stt.STT:
    """Faster-Whisper'ı, verilen VAD ile birleştirip AgentSession'ın beklediği
    streaming STT arayüzüne uyduran hazır bir örnek döndürür."""
    whisper = FasterWhisperSTT(
        model_size=settings.whisper_model,
        device=settings.whisper_device,
        language=settings.app_language,
    )
    return stt.StreamAdapter(stt=whisper, vad=vad)
