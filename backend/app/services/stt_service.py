"""
Speech-to-text service using Deepgram Nova-2 (medical model)
with OpenAI Whisper API fallback.
"""

import asyncio
import io
import logging
from typing import Optional

import httpx
from deepgram import DeepgramClient, PrerecordedOptions, FileSource

from app.core.config import settings

logger = logging.getLogger(__name__)


class DeepgramSTTService:
    """
    Transcribes clinical audio using Deepgram Nova-2 medical model.
    Falls back to OpenAI Whisper if Deepgram fails or is unavailable.
    """

    MEDICAL_KEYWORDS = [
        "physical therapy",
        "occupational therapy",
        "ROM",
        "MMT",
        "SOAP",
        "OASIS",
        "ADL",
        "ambulation",
        "gait",
        "transfers",
    ]

    def __init__(self) -> None:
        self._deepgram: Optional[DeepgramClient] = None

    def _get_client(self) -> DeepgramClient:
        if self._deepgram is None:
            self._deepgram = DeepgramClient(settings.DEEPGRAM_API_KEY)
        return self._deepgram

    async def transcribe_audio(self, audio_bytes: bytes, mimetype: str = "audio/wav") -> str:
        """
        Transcribe *audio_bytes* and return the transcript text.

        Tries Deepgram first; falls back to OpenAI Whisper on failure.
        """
        try:
            return await self._transcribe_deepgram(audio_bytes, mimetype)
        except Exception as deepgram_exc:
            logger.warning(
                "Deepgram transcription failed (%s), falling back to Whisper", deepgram_exc
            )
            try:
                return await self._transcribe_whisper(audio_bytes, mimetype)
            except Exception as whisper_exc:
                logger.error("Whisper fallback also failed: %s", whisper_exc)
                raise RuntimeError(
                    f"Both STT providers failed. Deepgram: {deepgram_exc}. Whisper: {whisper_exc}"
                ) from whisper_exc

    async def _transcribe_deepgram(self, audio_bytes: bytes, mimetype: str) -> str:
        client = self._get_client()

        source: FileSource = {"buffer": audio_bytes, "mimetype": mimetype}
        options = PrerecordedOptions(
            model="nova-2-medical",
            language="en-US",
            smart_format=True,
            punctuate=True,
            diarize=False,
            utterances=False,
            keywords=self.MEDICAL_KEYWORDS,
        )

        # Deepgram SDK is synchronous; run in a thread pool
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.listen.prerecorded.v("1").transcribe_file(source, options),
        )

        try:
            transcript = (
                response.results.channels[0].alternatives[0].transcript
            )
        except (AttributeError, IndexError, KeyError) as exc:
            raise RuntimeError(f"Unexpected Deepgram response structure: {exc}") from exc

        if not transcript:
            raise RuntimeError("Deepgram returned an empty transcript")

        return transcript.strip()

    async def _transcribe_whisper(self, audio_bytes: bytes, mimetype: str) -> str:
        """
        Fallback: call OpenAI Whisper via HTTP API.
        Requires ANTHROPIC_API_KEY to be set to an OpenAI key, or configure
        OPENAI_API_KEY separately. This implementation uses the httpx client
        directly against the OpenAI endpoint.
        """
        import os
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_key:
            raise RuntimeError("OPENAI_API_KEY not configured for Whisper fallback")

        # Determine file extension from mimetype
        ext_map = {
            "audio/wav": "wav",
            "audio/mpeg": "mp3",
            "audio/mp4": "mp4",
            "audio/ogg": "ogg",
            "audio/webm": "webm",
            "audio/flac": "flac",
        }
        ext = ext_map.get(mimetype, "wav")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {openai_key}"},
                files={"file": (f"audio.{ext}", io.BytesIO(audio_bytes), mimetype)},
                data={
                    "model": "whisper-1",
                    "language": "en",
                    "prompt": (
                        "Clinical physical therapy visit note. "
                        "Include medical terms, ROM values, MMT grades, pain scales."
                    ),
                },
            )
            response.raise_for_status()
            result = response.json()

        transcript = result.get("text", "").strip()
        if not transcript:
            raise RuntimeError("Whisper returned an empty transcript")
        return transcript
