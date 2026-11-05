import noisereduce as nr
import soundfile as sf
import numpy as np
import tempfile
import os


def suppress_noise(audio_path: str) -> str:
    """
    Aplica reducción de ruido al archivo de audio.
    Retorna la ruta del audio limpio en formato WAV temporal.
    """
    data, rate = sf.read(audio_path)

    # Convertir a mono si es estéreo
    if data.ndim > 1:
        data = data.mean(axis=1)

    # Aplicar reducción de ruido
    reduced = nr.reduce_noise(y=data, sr=rate, stationary=False, prop_decrease=0.75)

    # Guardar en archivo temporal
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, reduced, rate)
    tmp.close()

    return tmp.name
