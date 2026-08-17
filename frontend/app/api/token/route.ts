import { NextResponse } from "next/server";
import { AccessToken } from "livekit-server-sdk";
import { RoomConfiguration } from "@livekit/protocol";

type TokenRequestBody = {
  room_name?: string;
  participant_identity?: string;
  participant_name?: string;
  room_config?: unknown;
};

export async function POST(request: Request) {
  const body: TokenRequestBody = await request.json();

  const roomName = body.room_name ?? `tr-voice-agent-${crypto.randomUUID()}`;
  const participantIdentity = body.participant_identity ?? `user-${Date.now()}`;
  const participantName = body.participant_name ?? "Kullanıcı";

  const accessToken = new AccessToken(
    process.env.LIVEKIT_API_KEY,
    process.env.LIVEKIT_API_SECRET,
    {
      identity: participantIdentity,
      name: participantName,
      ttl: "10m",
    },
  );

  accessToken.addGrant({ roomJoin: true, room: roomName });

  if (body.room_config) {
    // Client, wire formatında snake_case JSON gönderiyor (`useProtoFieldName: true`).
    // `new RoomConfiguration(...)` bunu sessizce yanlış parse ediyor (agentName boş
    // kalıyor); doğru ayrıştırma için `fromJson` kullanılmalı.
    accessToken.roomConfig = RoomConfiguration.fromJson(
      body.room_config as Parameters<typeof RoomConfiguration.fromJson>[0],
    );
  }

  const participantToken = await accessToken.toJwt();

  return NextResponse.json(
    {
      server_url: process.env.LIVEKIT_URL,
      participant_token: participantToken,
    },
    { status: 201 },
  );
}
