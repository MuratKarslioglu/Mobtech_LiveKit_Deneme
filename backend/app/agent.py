import logging

from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, JobContext
from livekit.agents.llm import ChatMessage
from livekit.plugins import silero

from .config import settings
from .prompts.system import SYSTEM_PROMPT
from .providers.llm import build_llm
from .providers.local_whisper_stt import build_stt
from .providers.tts import build_tts

logger = logging.getLogger("voice-agent")
logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

# Render işini LiveKit CLI'ın kendi log sistemine bırakıyoruz (kendi handler'ımızı
# kurmuyoruz ki mesajlar iki kere basılmasın). Üçüncü parti kütüphanelerin kendi
# iç loglarını (HTTP client detayları, model çıkarım detayları) kaynağında
# susturuyoruz; bize gereken her şey zaten kendi [STT]/[LLM]/[TTS]/[LATENCY]/
# [ERROR] loglarımızdan geçiyor. livekit.agents'ı bilerek susturmuyoruz —
# worker/registered gibi bağlantı durumu mesajları hata ayıklarken değerli.
for _noisy in ("google_genai", "httpx", "faster_whisper"):
    logging.getLogger(_noisy).setLevel(logging.ERROR)


def _fmt_latency(seconds: float | None) -> str:
    if seconds is None:
        return "n/a"
    return f"{seconds * 1000:.0f} ms"


server = AgentServer()


@server.rtc_session(agent_name="tr-voice-agent")
async def entrypoint(ctx: JobContext) -> None:
    vad = silero.VAD.load()

    session = AgentSession(
        vad=vad,
        stt=build_stt(settings, vad),
        llm=build_llm(settings),
        tts=build_tts(settings),
    )

    @session.on("user_state_changed")
    def _on_user_state_changed(ev) -> None:
        if ev.new_state == "speaking":
            logger.info("[INFO] User started speaking")
        elif ev.old_state == "speaking":
            logger.info("[INFO] User stopped speaking")

    @session.on("user_input_transcribed")
    def _on_transcript(ev) -> None:
        if ev.is_final and ev.transcript.strip():
            logger.info("[STT] %s", ev.transcript)

    last_stt_delay_s: float | None = None

    @session.on("conversation_item_added")
    def _on_conversation_item(ev) -> None:
        nonlocal last_stt_delay_s
        item = ev.item
        if not isinstance(item, ChatMessage):
            return

        if item.role == "user":
            last_stt_delay_s = item.metrics.get("transcription_delay")
            return

        if item.role == "assistant" and item.text_content:
            logger.info("[LLM] %s", item.text_content)
            if item.interrupted:
                logger.info("[INFO] Agent interrupted")

            logger.info(
                "[LATENCY]\nSTT  : %s\nLLM  : %s\nTTS  : %s\nTOTAL: %s",
                _fmt_latency(last_stt_delay_s),
                _fmt_latency(item.metrics.get("llm_node_ttft")),
                _fmt_latency(item.metrics.get("tts_node_ttfb")),
                _fmt_latency(item.metrics.get("e2e_latency")),
            )

    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev) -> None:
        if ev.new_state == "speaking":
            logger.info("[TTS] Generating speech...")
            logger.info("[INFO] Agent speaking")

    @session.on("error")
    def _on_error(ev) -> None:
        layer = ev.error.type.replace("_error", "").upper()
        logger.error("[ERROR][%s] %s", layer, ev.error.error)

    await session.start(
        agent=Agent(instructions=SYSTEM_PROMPT),
        room=ctx.room,
    )
    await ctx.connect()
    logger.info("[INFO] LiveKit connected (room=%s)", ctx.room.name)


if __name__ == "__main__":
    agents.cli.run_app(server)
