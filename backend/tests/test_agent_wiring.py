"""Agent modülünün ve provider fabrikalarının hatasız kurulabildiğini doğrulayan
minimum "smoke test"ler. Gerçek bir LiveKit/Azure bağlantısı açmaz; sadece
importların ve nesne kurulumunun (wiring) bozulmadığını kontrol eder.
"""

from livekit.plugins import silero

from app.agent import VoiceAgent, entrypoint, server
from app.config import settings
from app.orchestration.cancellation_manager import CancellationManager
from app.orchestration.interim_response_manager import InterimResponseManager
from app.orchestration.response_orchestrator import ResponseOrchestrator
from app.providers.llm import build_llm
from app.providers.stt import build_stt
from app.providers.tts import build_tts


def test_agent_server_is_defined():
    assert server is not None
    assert callable(entrypoint)


def test_build_stt_wiring_succeeds():
    stt = build_stt(settings)
    assert stt.model == settings.azure_openai_stt_deployment


def test_build_llm_wiring_succeeds():
    llm = build_llm(settings)
    assert llm.model == settings.azure_openai_llm_deployment


def test_build_tts_wiring_succeeds():
    tts = build_tts(settings)
    assert tts.model == "tts-1"


def test_silero_vad_plugin_importable():
    # Modelin kendisini indirip yüklemeden, plugin'in en azından doğru
    # şekilde import edildiğini doğruluyoruz.
    assert hasattr(silero, "VAD")


def test_voice_agent_stores_injected_orchestrator():
    interim_manager = InterimResponseManager(threshold_s=1.0, speak=lambda _msg: None)
    cancellation_manager = CancellationManager()
    orchestrator = ResponseOrchestrator(
        interim_manager=interim_manager, cancellation_manager=cancellation_manager
    )

    agent = VoiceAgent(instructions="test", orchestrator=orchestrator)

    assert agent._orchestrator is orchestrator
