"""`VoiceAgent.stt_node`'daki halüsinasyon/self-echo filtresini doğrulayan
testler. `Agent.default.stt_node`'u sahte final transkript event'leri
üreten bir async generator ile değiştirip gerçek bir STT/LiveKit bağlantısı
açmadan filtre mantığını izole test eder.
"""

import asyncio
import time
from collections.abc import AsyncIterator

from livekit.agents import Agent
from livekit.agents import llm as llm_module
from livekit.agents import stt as stt_module

from app.agent import VoiceAgent
from app.orchestration.cancellation_manager import CancellationManager
from app.orchestration.interim_response_manager import InterimResponseManager
from app.orchestration.response_orchestrator import ResponseOrchestrator


async def _empty_audio():
    return
    yield  # pragma: no cover - async generator olması için gerekli


def _final_event(text: str) -> stt_module.SpeechEvent:
    return stt_module.SpeechEvent(
        type=stt_module.SpeechEventType.FINAL_TRANSCRIPT,
        alternatives=[stt_module.SpeechData(language="tr-TR", text=text)],
    )


def _make_agent(
    *, last_assistant_reply: str | None, assistant_reply_age_s: float = 0.0
) -> VoiceAgent:
    chat_ctx = llm_module.ChatContext.empty()
    if last_assistant_reply is not None:
        chat_ctx.add_message(
            role="assistant",
            content=last_assistant_reply,
            created_at=time.time() - assistant_reply_age_s,
        )

    orchestrator = ResponseOrchestrator(
        interim_manager=InterimResponseManager(threshold_s=1.0, speak=lambda _msg: None),
        cancellation_manager=CancellationManager(),
    )
    return VoiceAgent(instructions="test", orchestrator=orchestrator, chat_ctx=chat_ctx)


async def _collect_texts(agent: VoiceAgent, events: list[stt_module.SpeechEvent]) -> list[str]:
    async def fake_stt_node(_agent, _audio, _model_settings) -> AsyncIterator[stt_module.SpeechEvent]:
        for event in events:
            yield event

    original = Agent.default.stt_node
    Agent.default.stt_node = fake_stt_node
    try:
        out: list[str] = []
        async for event in agent.stt_node(_empty_audio(), model_settings=None):
            if event.alternatives:
                out.append(event.alternatives[0].text)
            else:
                out.append("")
        return out
    finally:
        Agent.default.stt_node = original


def test_single_word_transcript_passes_through_when_assistant_has_not_spoken():
    async def scenario():
        # Asistan hiç konuşmadıysa (örn. konuşmanın en başı) TTS sızıntısı
        # ihtimali yok — "Evet" gibi gerçek kısa bir cevap elenmemeli.
        agent = _make_agent(last_assistant_reply=None)
        out = await _collect_texts(agent, [_final_event("Evet")])
        assert out == ["Evet"]

    asyncio.run(scenario())


def test_single_word_transcript_is_dropped_right_after_assistant_spoke():
    async def scenario():
        # Asistan az önce konuştuysa (ECHO_RECENCY_WINDOW_S içinde), kısa bir
        # transkript TTS sızıntısı/halüsinasyon olabilir — bu durumda elenir.
        agent = _make_agent(last_assistant_reply="Nasıl yardımcı olabilirim?")
        out = await _collect_texts(agent, [_final_event("Evet")])
        assert out == [""]

    asyncio.run(scenario())


def test_single_word_transcript_passes_through_after_recency_window_expires():
    async def scenario():
        # Asistan konuştu ama ECHO_RECENCY_WINDOW_S (8s) çoktan geçti —
        # artık TTS sızıntısı riski yok, kısa cevap geçmeli.
        agent = _make_agent(
            last_assistant_reply="Nasıl yardımcı olabilirim?", assistant_reply_age_s=30.0
        )
        out = await _collect_texts(agent, [_final_event("Evet")])
        assert out == ["Evet"]

    asyncio.run(scenario())


def test_genuine_multi_word_transcript_passes_through():
    async def scenario():
        agent = _make_agent(
            last_assistant_reply="İyiyim teşekkür ederim, nasıl yardımcı olabilirim?"
        )
        out = await _collect_texts(agent, [_final_event("Bugün İstanbul'da hava nasıl?")])
        assert out == ["Bugün İstanbul'da hava nasıl?"]

    asyncio.run(scenario())


def test_self_echo_transcript_is_dropped():
    async def scenario():
        agent = _make_agent(
            last_assistant_reply="İyiyim teşekkür ederim, nasıl yardımcı olabilirim?"
        )
        # Asistanın az önce söylediği cümlenin bir parçası mikrofona sızmış gibi.
        out = await _collect_texts(agent, [_final_event("teşekkür ederim nasıl yardımcı")])
        assert out == [""]

    asyncio.run(scenario())


def test_stale_assistant_reply_does_not_trigger_echo_guard():
    async def scenario():
        # Asistan 30 saniye önce konuştu (ECHO_RECENCY_WINDOW_S=8'i aşıyor).
        # Kullanıcının şimdi söylediği, o eski cevapla örtüşen bir cümle
        # olsa bile bu artık "echo" sayılmamalı — gerçek/güncel bir cevap
        # olabilir (örn. ortak bir nezaket kalıbının tesadüfi tekrarı).
        agent = _make_agent(
            last_assistant_reply="İyiyim teşekkür ederim, nasıl yardımcı olabilirim?",
            assistant_reply_age_s=30.0,
        )
        out = await _collect_texts(agent, [_final_event("teşekkür ederim nasıl yardımcı")])
        assert out == ["teşekkür ederim nasıl yardımcı"]

    asyncio.run(scenario())


def test_no_prior_assistant_message_does_not_false_positive():
    async def scenario():
        agent = _make_agent(last_assistant_reply=None)
        out = await _collect_texts(agent, [_final_event("Merhaba, nasılsın?")])
        assert out == ["Merhaba, nasılsın?"]

    asyncio.run(scenario())
