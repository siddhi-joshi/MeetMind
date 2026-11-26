from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MeetMind"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    kokoro_voice_en: str = "af_heart"
    kokoro_voice_hi: str = "hf_alpha"
    meetmind_data_dir: Path = Path("data")
    meetmind_upload_dir: Path = Path("uploads")
    meetmind_generated_dir: Path = Path("generated")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def ensure_directories(self) -> None:
        for directory in (
            self.meetmind_data_dir,
            self.meetmind_upload_dir,
            self.meetmind_generated_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings

