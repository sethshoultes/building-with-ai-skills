# LITE mode audio format

LiveAvatar streams the avatar's video in real time, lip-synced to the audio coming from the conversational agent. For the lip-sync to work, the audio stream that reaches LiveAvatar **must be PCM 16-bit, 24 kHz, mono**.

## Why this matters

In LITE mode, the agent (ElevenLabs Conversational AI) produces TTS audio and LiveAvatar consumes it. ElevenLabs's default TTS output is MP3, which LiveAvatar can't lip-sync to. The agent has to be configured to emit PCM 24K, otherwise the avatar appears, the agent is "talking" (you'll see text in the transcription event), but the lip-sync is silent — no audio, no mouth movement.

## How to configure ElevenLabs to emit PCM 24K

In the agent's settings (Conversational AI dashboard, or via the API), set:

- **TTS output format**: `pcm_24000`
- **Voice**: any standard or cloned voice — the format is independent of the voice

Via API (PATCH the agent):

```json
{
  "conversation_config": {
    "tts": {
      "output_format": "pcm_24000"
    }
  }
}
```

## How to verify

Two checks:

1. **Dashboard test.** In the ElevenLabs Conversational AI dashboard, run the test conversation. The agent should respond audibly. If you can't hear it in the dashboard, the output format is wrong upstream of LiveAvatar — fix it there first.
2. **Browser console.** With the avatar session running, open the browser console and watch for `AVATAR_TRANSCRIPTION` events. If you see transcription text but the video is muted/static-mouthed, the format is the problem.

## Common mistakes

- Setting the format on the **voice** rather than the **agent**. The voice's `output_format` is for direct TTS calls; the agent's TTS config is what LITE mode reads.
- Using `mp3_44100_128` (the dashboard default). MP3 cannot be lip-synced.
- Mismatched sample rates (e.g. `pcm_16000`). LiveAvatar specifically wants 24 kHz.

## What the SDK reports when the format is wrong

The `LiveAvatarSession.start()` resolves successfully — the WebRTC channel opens, the avatar appears. But:

- `AVATAR_TRANSCRIPTION` events fire with text (the agent is producing speech).
- The video element shows the avatar with closed mouth and no audio.
- No error is logged.

This is the failure mode. If you see "talking head, silent" — check the audio format first.
