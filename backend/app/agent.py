import difflib
import logging
import re
import time
from collections.abc import AsyncIterable, AsyncIterator

from livekit import agents, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    ModelSettings,
    RoomInputOptions,
)
from livekit.agents import llm as llm_module
from livekit.agents import stt as stt_module
from livekit.agents.llm import ChatMessage, FunctionCall, FunctionCallOutput
from livekit.plugins import noise_cancellation, silero

from .config import settings
from .orchestration.cancellation_manager import CancellationManager
from .orchestration.interim_response_manager import InterimResponseManager
from .orchestration.response_orchestrator import ResponseOrchestrator
from .prompts.system import SYSTEM_PROMPT
from .providers.llm import build_llm
from .providers.stt import build_stt
from .providers.tts import build_tts
from .streaming.text_chunk_buffer import chunk_text_stream
from .tools.registry import all_tools

logger = logging.getLogger("voice-agent")
logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

# Kök neden: asistanın kendi TTS çıktısı (özellikle Bluetooth kulaklıklarda,
# ses gecikmesi echo-cancellation'ı bozabiliyor) mikrofona kalıntı olarak
# sızabiliyor; Azure'un transcribe modeli (gpt-4o-mini-transcribe) de,
# Whisper ailesi gibi üretken bir model olduğu için bu belirsiz/kısa ses
# parçasından tam cümlelik bir metin "uydurabiliyor" (bilinen bir
# halüsinasyon davranışı). Sonuç: kullanıcı hiç konuşmadan yeni bir tur
# başlıyor. Bunu VAD hassasiyetiyle değil, transkriptin içeriğiyle
# (kelime sayısıyla) engelliyoruz — bkz. VoiceAgent.stt_node. Gerçek tek
# kelimelik cevaplar ("Evet", "Dur") kaybedilebilir; bu bilinçli bir
# ödünleşim (yanlış tetiklenmeyi önlemek, tek kelimelik cevaptan önemli).
MIN_TRANSCRIPT_WORDS = 2

# Tek-kelime filtresi (yukarıdaki) yalnızca `word_count == 1` durumunu
# yakalıyor; asistanın kendi TTS çıktısının 2+ kelimelik bir parçası
# (örn. son cevabının bir kısmı) mikrofona sızıp aynen ya da neredeyse
# aynen transkript edilirse o filtreden kaçar ve gerçek bir LLM turu
# başlatır — kullanıcı hiçbir şey sormamışken "Bir saniye, düşünüyorum."
# duyulmasının kök nedeni budur. Burada final transkripti asistanın en son
# söylediği metinle kelime bazında karşılaştırıp yüksek örtüşme
# (self-echo) tespit ediyoruz. Eşik değeri, kısa ama meşru kullanıcı
# cevaplarını ("Evet, doğru." gibi) yanlışlıkla elemeyecek kadar yüksek
# tutuldu; tamamen farklı bir cümlede örtüşme oranı düşük kalır.
ECHO_SIMILARITY_THRESHOLD = 0.6

# Self-echo kontrolü yalnızca asistan YAKIN ZAMANDA konuştuysa uygulanır.
# Aksi halde, konuşmanın çok öncesinde asistanın söylediği bir ifadeyle
# (örn. ortak bir Türkçe nezaket kalıbı — "teşekkür ederim" gibi) tesadüfen
# örtüşen GERÇEK ve GÜNCEL bir kullanıcı cevabı yanlışlıkla echo sanılıp
# atılabilir ("sistem beni duymadı" hissi buradan gelebilir). 8 saniyelik
# pencere, tipik bir kısa asistan cevabının TTS ile seslendirilme süresine
# (birkaç saniye) makul bir pay bırakıyor.
ECHO_RECENCY_WINDOW_S = 8.0

# Render işini LiveKit CLI'ın kendi log sistemine bırakıyoruz (kendi handler'ımızı
# kurmuyoruz ki mesajlar iki kere basılmasın). Üçüncü parti kütüphanelerin kendi
# iç loglarını (HTTP client detayları, model çıkarım detayları) kaynağında
# susturuyoruz; bize gereken her şey zaten kendi [STT]/[LLM]/[TTS]/[TOOL]/
# [LATENCY]/[ERROR] loglarımızdan geçiyor. livekit.agents'ı bilerek susturmuyoruz —
# worker/registered gibi bağlantı durumu mesajları hata ayıklarken değerli.
for _noisy in ("httpx", "openai"):
    logging.getLogger(_noisy).setLevel(logging.ERROR)


def _fmt_latency(seconds: float | None) -> str:
    if seconds is None:
        return "n/a"
    return f"{seconds * 1000:.0f} ms"


def _last_assistant_message(chat_ctx: llm_module.ChatContext) -> tuple[str, float] | None:
    for message in reversed(chat_ctx.messages()):
        if message.role == "assistant" and message.text_content:
            return message.text_content, message.created_at
    return None


def _normalize_for_echo_match(text: str) -> str:
    # Noktalama (STT'nin ürettiği kesme/nokta/virgül asistanın orijinal
    # cevabındakiyle birebir örtüşmeyebilir) ve fazla boşluk, ardışık eşleşme
    # bloğunu gereksiz yere bölmesin diye normalize ediliyor.
    normalized = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _is_self_echo(text: str, chat_ctx: llm_module.ChatContext) -> bool:
    """Yeni transkript, asistanın az önce söylediği metnin bir alt-dizisiyle
    (ardışık karakter bloğuyla) büyük oranda örtüşüyor mu? Örtüşme oranı,
    yeni transkriptin (genelde kısa bir echo/halüsinasyon parçası) uzunluğuna
    göre normalize edilir — asistanın az önceki cevabı uzun bir cümle, echo
    ise onun küçük bir parçası olabileceğinden simetrik bir benzerlik oranı
    (`SequenceMatcher.ratio`) yanıltıcı biçimde düşük çıkabilir."""
    last_message = _last_assistant_message(chat_ctx)
    if last_message is None or not text:
        return False
    last_reply, last_reply_at = last_message
    if time.time() - last_reply_at > ECHO_RECENCY_WINDOW_S:
        return False
    needle = _normalize_for_echo_match(text)
    haystack = _normalize_for_echo_match(last_reply)
    if not needle:
        return False
    matcher = difflib.SequenceMatcher(a=needle, b=haystack)
    match = matcher.find_longest_match(0, len(needle), 0, len(haystack))
    overlap_ratio = match.size / len(needle)
    return overlap_ratio >= ECHO_SIMILARITY_THRESHOLD


class VoiceAgent(Agent):
    """LLM çıktısını TTS'e vermeden önce `TextChunkBuffer`'dan geçiren, ve
    LLM gerçekten çağrıldığında ara ("interim") mesaj zamanlayıcısını
    yöneten `Agent`.

    Varsayılan `tts_node`, streaming olmayan TTS'lerde genel amaçlı bir
    cümle tokenizer'ı (blingfire) kullanıyor. Burada onun yerine kendi
    Türkçe noktalama + minimum uzunluk kuralımızı (bkz.
    `streaming/text_chunk_buffer.py`, V2 dokümanı bölüm 6) uyguluyoruz;
    gerçek sentezi yine `Agent.default.tts_node`'a devrediyoruz.
    """

    def __init__(self, *, orchestrator: ResponseOrchestrator, **kwargs) -> None:
        super().__init__(**kwargs)
        self._orchestrator = orchestrator

    def llm_node(
        self,
        chat_ctx: llm_module.ChatContext,
        tools: list[llm_module.Tool],
        model_settings: ModelSettings,
    ) -> AsyncIterable[llm_module.ChatChunk | str]:
        """Zamanlayıcı, LLM'e tam soru (chat_ctx) verilip `.chat()` çağrısı
        gerçekten başladığı anda başlar — `agent_state_changed`'daki genel
        "thinking" durumunun aksine, hayalet bir tur (STT halüsinasyonu
        `VoiceAgent.stt_node` tarafından filtrelenip LLM'e hiç ulaşmadıysa)
        bu zamanlayıcıyı asla tetiklemez. İlk cevap chunk'ı gelir gelmez
        iptal edilir — "son chunk"ı (generation bitişini) beklemek ara
        mesajın amacını ortadan kaldırır."""

        async def _timed() -> AsyncIterator[llm_module.ChatChunk | str]:
            self._orchestrator.start_interim_timer()
            first_chunk = True
            async for chunk in Agent.default.llm_node(self, chat_ctx, tools, model_settings):
                if first_chunk:
                    self._orchestrator.process_request()
                    first_chunk = False
                yield chunk

        return _timed()

    def tts_node(
        self, text: AsyncIterable[str], model_settings: ModelSettings
    ) -> AsyncIterable[rtc.AudioFrame]:
        return Agent.default.tts_node(self, chunk_text_stream(text), model_settings)

    def stt_node(
        self, audio: AsyncIterable[rtc.AudioFrame], model_settings: ModelSettings
    ) -> AsyncIterable[stt_module.SpeechEvent]:
        """`MIN_TRANSCRIPT_WORDS`'ten az kelime içeren VEYA asistanın az önce
        söylediği metinle yüksek oranda örtüşen final transkriptleri
        boşaltır — bunlar genelde gerçek konuşma değil, asistanın kendi
        sesinin mikrofona sızmasından (echo) veya ortam gürültüsünden
        STT'nin ürettiği halüsinasyonlardır. Bu sayede kullanıcı hiç
        konuşmadığında sahte bir tur başlayıp asistanın gereksiz yere
        cevap vermeye çalışması engellenir."""

        async def _filtered() -> AsyncIterator[stt_module.SpeechEvent]:
            async for event in Agent.default.stt_node(self, audio, model_settings):
                if event.type == stt_module.SpeechEventType.FINAL_TRANSCRIPT and event.alternatives:
                    text = event.alternatives[0].text.strip()
                    word_count = len(text.split())
                    drop_reason: str | None = None
                    if 0 < word_count < MIN_TRANSCRIPT_WORDS:
                        drop_reason = f"şüpheli kısa transkript ({word_count} kelime)"
                    elif word_count >= MIN_TRANSCRIPT_WORDS and _is_self_echo(text, self.chat_ctx):
                        drop_reason = "olası self-echo"
                    if drop_reason:
                        logger.warning("[STT] %s göz ardı edildi: %r", drop_reason, text)
                        event = stt_module.SpeechEvent(
                            type=stt_module.SpeechEventType.FINAL_TRANSCRIPT,
                            alternatives=[],
                        )
                yield event

        return _filtered()


server = AgentServer()


@server.rtc_session(agent_name="tr-voice-agent")
async def entrypoint(ctx: JobContext) -> None:
    # VAD hassasiyeti bilinçli olarak varsayılanında bırakılıyor —
    # "kullanıcı konuşuyor mu" kararı dinleme aşamasında (mikrofon
    # hassasiyetiyle) değil, düşünme aşamasına geçmeden hemen önce, STT'nin
    # gerçekte ne yazdığına bakılarak veriliyor (bkz. VoiceAgent.stt_node).
    vad = silero.VAD.load()

    session = AgentSession(
        vad=vad,
        stt=build_stt(settings),
        llm=build_llm(settings),
        tts=build_tts(settings),
        # Asistan konuşurken (asıl "interruption" senaryosu) da aynı
        # mantık: en az MIN_TRANSCRIPT_WORDS kelime içermeyen bir "araya
        # girme" gerçek sayılmaz — SDK'nın kendi resmi mekanizması,
        # VoiceAgent.stt_node'daki genel filtreyi tamamlıyor.
        turn_handling={"interruption": {"min_words": MIN_TRANSCRIPT_WORDS}},
    )

    def _speak_interim(message: str) -> None:
        logger.info("[INTERIM] triggered=true message=%r", message)
        session.say(message, allow_interruptions=True)

    interim_manager = InterimResponseManager(
        threshold_s=settings.interim_response_threshold_ms / 1000,
        speak=_speak_interim,
    )
    cancellation_manager = CancellationManager()
    orchestrator = ResponseOrchestrator(
        interim_manager=interim_manager, cancellation_manager=cancellation_manager
    )

    @session.on("user_state_changed")
    def _on_user_state_changed(ev) -> None:
        if ev.new_state == "speaking":
            logger.info("[INFO] User started speaking")
            # Kullanıcı, asistanın turu hâlâ aktifken (örn. bekleyen bir
            # interim zamanlayıcı varken) tekrar konuşmaya başlarsa, bunu
            # SDK'nın kendi interruption mekanizmasından bağımsız olarak
            # hemen orchestrator'a bildiriyoruz — henüz söylenmemiş bir
            # "düşünüyorum" mesajının barge-in'de gecikmeden iptal edilmesi
            # için.
            if orchestrator.turn_active:
                orchestrator.cancel_current_response()
        elif ev.old_state == "speaking":
            logger.info("[INFO] User stopped speaking")

    @session.on("user_input_transcribed")
    def _on_transcript(ev) -> None:
        if ev.is_final and ev.transcript.strip():
            logger.info("[STT] %s", ev.transcript)

    last_stt_delay_s: float | None = None
    pending_tool_calls: dict[str, float] = {}

    @session.on("conversation_item_added")
    def _on_conversation_item(ev) -> None:
        nonlocal last_stt_delay_s
        item = ev.item

        if isinstance(item, FunctionCall):
            pending_tool_calls[item.call_id] = item.created_at
            orchestrator.execute_tool(item.name)
            return

        if isinstance(item, FunctionCallOutput):
            started_at = pending_tool_calls.pop(item.call_id, None)
            duration = _fmt_latency(
                item.created_at - started_at if started_at is not None else None
            )
            status = "error" if item.is_error else "ok"
            logger.info(
                "[TOOL] name=%s duration=%s status=%s", item.name, duration, status
            )
            orchestrator.process_request()
            return

        if not isinstance(item, ChatMessage):
            return

        if item.role == "user":
            last_stt_delay_s = item.metrics.get("transcription_delay")
            orchestrator.start_turn()
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
            orchestrator.finish_turn()

    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev) -> None:
        if ev.new_state == "thinking":
            logger.info("[INFO] Agent thinking")
        elif ev.new_state == "speaking":
            logger.info("[TTS] Generating speech...")
            logger.info("[INFO] Agent speaking")

    @session.on("error")
    def _on_error(ev) -> None:
        layer = (ev.error.type or "unknown").replace("_error", "").upper()
        logger.error("[ERROR][%s] %s", layer, ev.error.error)

    await session.start(
        agent=VoiceAgent(
            instructions=SYSTEM_PROMPT, tools=all_tools(), orchestrator=orchestrator
        ),
        room=ctx.room,
        # BVC (Background Voice Cancellation): mikrofona sızan konuşmacı-dışı
        # sesleri (asistanın kendi hoparlör/kulaklık çıktısı dahil) ses
        # seviyesinde bastırır — VoiceAgent.stt_node'daki metin-seviyesi echo
        # filtresini (word-count + self-echo benzerliği) tamamlayan, kök
        # nedene daha yakın bir önlem.
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )
    await ctx.connect()
    logger.info("[INFO] LiveKit connected (room=%s)", ctx.room.name)


if __name__ == "__main__":
    agents.cli.run_app(server)
