from __future__ import annotations

from ..tools.registry import tool_config
from .cancellation_manager import CancellationManager
from .interim_response_manager import DEFAULT_INTERIM_MESSAGE, InterimResponseManager


class ResponseOrchestrator:
    """Turn lifecycle koordinasyonu: `agent.py`'deki `VoiceAgent.llm_node`,
    `conversation_item_added` (FunctionCall/Output) ve `user_state_changed`
    (barge-in) event'lerini `InterimResponseManager`/`CancellationManager`'a
    yönlendirir.

    LiveKit'in `AgentSession`'ı LLM/TTS generation task'larını kendi içinde
    yönettiği için `CancellationManager` şu an yalnızca interim zamanlayıcıyı
    izliyor; gerçek generation/TTS cancellation ileriki bir aşamaya bırakıldı.
    """

    def __init__(
        self,
        *,
        interim_manager: InterimResponseManager,
        cancellation_manager: CancellationManager,
    ) -> None:
        self._interim = interim_manager
        self._cancellation = cancellation_manager
        self._turn_active = False

    def start_turn(self) -> None:
        """Kullanıcının final transcript'i alındığında çağrılır."""
        self._turn_active = True

    def start_interim_timer(self, *, tool_name: str | None = None) -> None:
        """Uzun sürebilecek bir işlem (tool çağrısı ya da LLM cevabı)
        başladığında çağrılır. `tool_name` verilirse ilgili `ToolConfig`'in
        `interim_message`'ı, verilmezse genel bir mesaj kullanılır."""
        message = DEFAULT_INTERIM_MESSAGE
        if tool_name is not None:
            config = tool_config(tool_name)
            if config is not None:
                message = config.interim_message
        self._interim.start(message)

    def execute_tool(self, name: str) -> None:
        """Bir tool çağrısı başladığında (`FunctionCall` event'i) çağrılır."""
        self.start_interim_timer(tool_name=name)

    def process_request(self) -> None:
        """Gerçek cevap (tool sonucu ya da LLM cevabı) hazır olduğunda
        çağrılır — bekleyen interim zamanlayıcıyı iptal eder."""
        self._interim.cancel()

    def cancel_current_response(self) -> None:
        """Kullanıcı araya girdiğinde (barge-in) çağrılır — interim
        zamanlayıcıyı ve takip edilen tüm görevleri iptal eder."""
        self._interim.cancel()
        self._cancellation.cancel_all()

    def finish_turn(self) -> None:
        """Tur tamamen bittiğinde (asistanın cevabı loglandığında) çağrılır."""
        self._interim.cancel()
        self._turn_active = False

    @property
    def turn_active(self) -> bool:
        return self._turn_active
