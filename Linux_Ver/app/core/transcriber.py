import os
from dotenv import load_dotenv
from faster_whisper import WhisperModel

load_dotenv()

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "medium")

_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        print(f"[Whisper] Cargando modelo '{WHISPER_MODEL_SIZE}' en {device}...")
        _model = WhisperModel(WHISPER_MODEL_SIZE, device=device, compute_type=compute_type)
    return _model


def transcribe(audio_path: str) -> str:
    """
    Transcribe el audio al texto usando Faster-Whisper.
    Retorna el texto transcrito en español.
    """
    model = get_model()
    segments, info = model.transcribe(audio_path, language="es", beam_size=5)
    text = " ".join(segment.text.strip() for segment in segments)
    return text.strip()
