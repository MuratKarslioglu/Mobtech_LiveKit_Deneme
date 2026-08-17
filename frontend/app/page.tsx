"use client";

import { useEffect, useRef, useState } from "react";
import { TokenSource } from "livekit-client";
import {
  RoomAudioRenderer,
  SessionProvider,
  useAgent,
  useIsSpeaking,
  useLocalParticipant,
  useSession,
  useSessionMessages,
} from "@livekit/components-react";

const tokenSource = TokenSource.endpoint("/api/token");

const AGENT_STATE_LABELS: Record<string, string> = {
  connecting: "Bağlanıyor…",
  "pre-connect-buffering": "Bağlanıyor…",
  initializing: "Hazırlanıyor…",
  idle: "Seni dinliyor",
  listening: "Seni dinliyor",
  thinking: "Düşünüyor…",
  speaking: "Konuşuyor",
  disconnected: "Bağlantı kesildi",
  failed: "Bir hata oluştu",
};

const AGENT_STATE_DOT: Record<string, string> = {
  listening: "bg-emerald-500",
  idle: "bg-emerald-500",
  thinking: "bg-amber-500",
  speaking: "bg-blue-500",
  failed: "bg-red-500",
};

function formatTime(ms: number) {
  return new Date(ms).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
}

function formatDuration(totalSeconds: number) {
  const m = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (totalSeconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function useElapsedSeconds(active: boolean) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!active) {
      return;
    }
    // Sayacı her yeni bağlantıda sıfırlıyoruz; bu bilinçli bir reset, bir
    // dış sistemle senkronizasyon eksikliği değil.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSeconds(0);
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [active]);
  return active ? seconds : 0;
}

function Dot({ colorClass, animated }: { colorClass: string; animated: boolean }) {
  return (
    <span className="relative flex h-2.5 w-2.5">
      {animated && (
        <span
          className={`absolute inline-flex h-full w-full animate-ping rounded-full ${colorClass} opacity-60`}
        />
      )}
      <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${colorClass}`} />
    </span>
  );
}

function MicIcon({ muted }: { muted: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth={2}>
      <path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Z" strokeLinecap="round" />
      <path d="M19 11a7 7 0 0 1-14 0M12 18v3" strokeLinecap="round" />
      {muted && <path d="M4 4l16 16" strokeLinecap="round" />}
    </svg>
  );
}

/** Sol taraftaki bilgi paneli: bağlantı durumu, konuşma süresi, teknik detaylar ve ipuçları. */
function InfoSidebar({ connected }: { connected: boolean }) {
  // Hook'lar her render'da aynı sırada, koşulsuz çağrılmalı (React kuralı);
  // "connected" durumuna göre sadece döndürdükleri değeri kullanıyoruz.
  const agent = useAgent();
  const { localParticipant } = useLocalParticipant();
  const isUserSpeaking = useIsSpeaking(localParticipant);
  const elapsed = useElapsedSeconds(connected);

  return (
    <aside className="hidden w-[30%] min-w-[260px] flex-col overflow-y-auto border-r border-neutral-200 bg-white p-6 lg:flex">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-neutral-900 text-sm font-semibold text-white">
          TR
        </div>
        <div>
          <h1 className="text-sm font-semibold text-neutral-900">Sesli Asistan</h1>
          <p className="text-xs text-neutral-400">Türkçe konuşan yapay zeka</p>
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-neutral-200 p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium tracking-wide text-neutral-400 uppercase">
            Durum
          </span>
          <div className="flex items-center gap-1.5">
            <Dot colorClass={connected ? "bg-emerald-500" : "bg-neutral-300"} animated={connected} />
            <span className="text-xs font-medium text-neutral-600">
              {connected ? "Bağlı" : "Çevrimdışı"}
            </span>
          </div>
        </div>
        {connected && (
          <p className="mt-2 font-mono text-2xl font-semibold text-neutral-900">
            {formatDuration(elapsed)}
          </p>
        )}
      </div>

      {connected && (
        <div className="mt-4 flex flex-col gap-3 rounded-xl border border-neutral-200 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-neutral-600">Sen</span>
            <div className="flex items-center gap-1.5">
              <Dot colorClass={isUserSpeaking ? "bg-emerald-500" : "bg-neutral-300"} animated={isUserSpeaking} />
              <span className="text-xs text-neutral-500">
                {isUserSpeaking ? "konuşuyorsun" : "sessiz"}
              </span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-neutral-600">Asistan</span>
            <div className="flex items-center gap-1.5">
              <Dot colorClass={AGENT_STATE_DOT[agent.state] ?? "bg-neutral-300"} animated />
              <span className="text-xs text-neutral-500">
                {AGENT_STATE_LABELS[agent.state] ?? agent.state}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="mt-4 rounded-xl border border-neutral-200 p-4">
        <span className="text-xs font-medium tracking-wide text-neutral-400 uppercase">
          Kullanılan modeller
        </span>
        <dl className="mt-2 flex flex-col gap-1.5 text-sm">
          <div className="flex justify-between gap-2">
            <dt className="text-neutral-500">STT</dt>
            <dd className="text-right text-neutral-700">Azure OpenAI</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt className="text-neutral-500">LLM</dt>
            <dd className="text-right text-neutral-700">Azure OpenAI</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt className="text-neutral-500">TTS</dt>
            <dd className="text-right text-neutral-700">Azure OpenAI</dd>
          </div>
        </dl>
      </div>

      <div className="mt-4 rounded-xl bg-neutral-50 p-4">
        <span className="text-xs font-medium tracking-wide text-neutral-400 uppercase">
          İpuçları
        </span>
        <ul className="mt-2 flex flex-col gap-1.5 text-sm text-neutral-600">
          <li>Agent konuşurken araya girip yeni bir şey sorabilirsin.</li>
          <li>Mikrofonu istediğin an alt bardaki simgeden kapatabilirsin.</li>
          <li>Konuşma geçmişi bağlı kaldığın sürece hatırlanır.</li>
        </ul>
      </div>

      <div className="flex-1" />
      <p className="text-xs text-neutral-300">tr-voice-agent</p>
    </aside>
  );
}

function TypingBubble() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md border border-neutral-200 bg-white px-3.5 py-2.5 shadow-sm">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400" />
      </div>
    </div>
  );
}

function ChatMessages() {
  const { messages } = useSessionMessages();
  const agent = useAgent();
  const bottomRef = useRef<HTMLDivElement>(null);
  const showTyping = agent.state === "thinking";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, showTyping]);

  if (messages.length === 0 && !showTyping) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-neutral-400">Konuşmaya başlamak için bir şeyler söyle.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-2.5 overflow-y-auto px-4 py-5">
      {messages.map((message) => {
        const isLocal = Boolean(message.from?.isLocal);
        return (
          <div key={message.id} className={`flex ${isLocal ? "justify-end" : "justify-start"}`}>
            <div className={`flex max-w-[70%] flex-col ${isLocal ? "items-end" : "items-start"}`}>
              <div
                className={`rounded-2xl px-3.5 py-2 text-sm leading-relaxed shadow-sm ${
                  isLocal
                    ? "rounded-br-md bg-neutral-900 text-white"
                    : "rounded-bl-md border border-neutral-200 bg-white text-neutral-900"
                }`}
              >
                {message.message}
              </div>
              <span className="mt-0.5 px-1 text-[10px] text-neutral-400">
                {formatTime(message.timestamp)}
              </span>
            </div>
          </div>
        );
      })}
      {showTyping && <TypingBubble />}
      <div ref={bottomRef} />
    </div>
  );
}

function CallBar({ onDisconnect }: { onDisconnect: () => void }) {
  const { localParticipant, isMicrophoneEnabled } = useLocalParticipant();

  const toggleMic = () => {
    localParticipant.setMicrophoneEnabled(!isMicrophoneEnabled);
  };

  return (
    <footer className="flex items-center justify-center gap-3 border-t border-neutral-200 bg-white px-4 py-3">
      <button
        onClick={toggleMic}
        title={isMicrophoneEnabled ? "Mikrofonu kapat" : "Mikrofonu aç"}
        className={`flex h-10 w-10 items-center justify-center rounded-full transition-colors ${
          isMicrophoneEnabled
            ? "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
            : "bg-red-50 text-red-600 hover:bg-red-100"
        }`}
      >
        <MicIcon muted={!isMicrophoneEnabled} />
      </button>
      <button
        onClick={onDisconnect}
        className="rounded-full border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-100"
      >
        Ayrıl
      </button>
    </footer>
  );
}

export default function Home() {
  // Her sekme/oturum kendi odasını kullanır. Sabit bir oda adı paylaşılsaydı,
  // LiveKit agent dispatch bilgisini yalnızca odanın İLK oluşturulduğu anda
  // işler; aynı oda tekrar tekrar kullanılırsa sonraki bağlantılarda agent
  // hiç çağrılmaz. Benzersiz isim bu sorunu kökten önlüyor.
  const [roomName] = useState(() => `tr-voice-agent-${crypto.randomUUID()}`);
  const session = useSession(tokenSource, {
    roomName,
    agentName: "tr-voice-agent",
  });
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConnect = async () => {
    setError(null);
    setConnecting(true);
    try {
      await session.start({ tracks: { microphone: { enabled: true } } });
      setConnected(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bağlantı kurulamadı.");
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    await session.end();
    setConnected(false);
  };

  return (
    <SessionProvider session={session}>
      <div className="flex h-screen bg-neutral-50">
        <InfoSidebar connected={connected} />

        <div className="flex flex-1 flex-col">
          <RoomAudioRenderer />

          {connected ? (
            <>
              <ChatMessages />
              <CallBar onDisconnect={handleDisconnect} />
            </>
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-neutral-900">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  className="h-6 w-6 text-white"
                  stroke="currentColor"
                  strokeWidth={1.8}
                >
                  <path
                    d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Z"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path d="M19 11a7 7 0 0 1-14 0M12 18v3" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div>
                <h2 className="text-base font-semibold text-neutral-900">
                  Türkçe sesli asistanınla konuş
                </h2>
                <p className="mt-1 max-w-xs text-sm text-neutral-500">
                  Bağlan&apos;a bas, mikrofon iznini onayla ve konuşmaya başla.
                </p>
              </div>
              <button
                onClick={handleConnect}
                disabled={connecting}
                className="rounded-full bg-neutral-900 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:opacity-50"
              >
                {connecting ? "Bağlanıyor…" : "Bağlan"}
              </button>
              {error && <p className="text-sm text-red-600">{error}</p>}
            </div>
          )}
        </div>
      </div>
    </SessionProvider>
  );
}
