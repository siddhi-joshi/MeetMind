from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import get_settings


@lru_cache(maxsize=1)
def _model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is not installed. Install requirements.txt to enable transcription."
        ) from exc

    settings = get_settings()
    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


def transcribe_audio(audio_path: Path, language: str = "auto") -> dict[str, Any]:
    selected_language = None if language == "auto" else language
    segments_iterator, info = _model().transcribe(
        str(audio_path),
        language=selected_language,
        beam_size=5,
        vad_filter=True,
        word_timestamps=True,
    )
    segments = []
    transcript_parts = []
    for index, segment in enumerate(segments_iterator):
        text = segment.text.strip()
        if not text:
            continue
        transcript_parts.append(text)
        segments.append(
            {
                "index": index,
                "speaker": "Speaker",
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": text,
            }
        )
    return {
        "text": " ".join(transcript_parts),
        "segments": segments,
        "language": info.language,
        "duration": getattr(info, "duration", 0) or 0,
    }

