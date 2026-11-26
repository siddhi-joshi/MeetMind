from functools import lru_cache
from pathlib import Path

from app.config import get_settings


@lru_cache(maxsize=2)
def _pipeline(language_code: str):
    try:
        from kokoro import KPipeline
    except ImportError as exc:
        raise RuntimeError("Kokoro is not installed. Install requirements.txt to enable read aloud.") from exc
    return KPipeline(lang_code=language_code)


def synthesize(text: str, language: str, output_path: Path) -> Path:
    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        raise RuntimeError("Kokoro audio dependencies are not installed.") from exc

    settings = get_settings()
    is_hindi = language.lower().startswith("hi")
    lang_code = "h" if is_hindi else "a"
    voice = settings.kokoro_voice_hi if is_hindi else settings.kokoro_voice_en
    pieces = []
    for _, _, audio in _pipeline(lang_code)(text, voice=voice, speed=1, split_pattern=r"\n+"):
        pieces.append(audio)
    if not pieces:
        raise RuntimeError("Kokoro did not generate any audio.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), np.concatenate(pieces), 24000)
    return output_path

