import noisereduce as nr
import numpy as np
from faster_whisper.audio import decode_audio


def suppress_noise(audio_path: str) -> np.ndarray:
    """
    Aplica reducción de ruido al archivo de audio.
    Soporta formatos WebM/MP4 gracias a faster_whisper.
    Retorna el audio limpio como un array de NumPy a 16kHz.
    """
    # decode_audio maneja WebM, OGG, M4A, etc. sin FFMPEG externo (usa PyAV).
    # Siempre lo convierte a 16000 Hz, que es lo que Whisper necesita.
    data = decode_audio(audio_path, sampling_rate=16000)

    # Aplicar reducción de ruido (noisereduce soporta arrays directos)
    reduced = nr.reduce_noise(y=data, sr=16000, stationary=False, prop_decrease=0.75)

    return reduced
