import os
import sys
import time
import urllib.request

# OpenBioLLM-Llama3-8B: Modelo Médico SOTA (Saama AI Labs) #1 en MedQA / USMLE
URL = "https://huggingface.co/bartowski/OpenBioLLM-Llama3-8B-GGUF/resolve/main/OpenBioLLM-Llama3-8B-Q4_K_M.gguf"
DEST_DIR = os.path.abspath("models")
DEST_FILE = os.path.join(DEST_DIR, "OpenBioLLM-Llama3-8B-Q4_K_M.gguf")
PART_FILE = DEST_FILE + ".part"

os.makedirs(DEST_DIR, exist_ok=True)

if os.path.exists(DEST_FILE) and os.path.getsize(DEST_FILE) > 4000 * 1024 * 1024:
    print(f"Model already downloaded: {DEST_FILE} ({os.path.getsize(DEST_FILE)} bytes)", flush=True)
    sys.exit(0)

# Soporte de reanudación (Resume)
existing_bytes = os.path.getsize(PART_FILE) if os.path.exists(PART_FILE) else 0

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
if existing_bytes > 0:
    headers["Range"] = f"bytes={existing_bytes}-"
    print(f"Resuming download from byte {existing_bytes} ({existing_bytes/(1024*1024):.1f} MB)...", flush=True)
else:
    print(f"Starting fresh download of SOTA Medical Model OpenBioLLM-8B to {DEST_FILE}...", flush=True)

req = urllib.request.Request(URL, headers=headers)
start_time = time.time()

try:
    mode = "ab" if existing_bytes > 0 else "wb"
    with urllib.request.urlopen(req, timeout=45) as response, open(PART_FILE, mode) as out_f:
        content_range = response.headers.get("Content-Range")
        if content_range:
            total_len = int(content_range.split("/")[-1])
        else:
            total_len = int(response.headers.get("Content-Length", 0)) + existing_bytes

        downloaded = existing_bytes
        chunk_size = 4 * 1024 * 1024  # 4 MB
        last_print = 0

        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_f.write(chunk)
            out_f.flush()
            downloaded += len(chunk)
            now = time.time()
            if now - last_print > 4:
                pct = (downloaded / total_len * 100) if total_len else 0
                mb = downloaded / (1024 * 1024)
                tot_mb = total_len / (1024 * 1024) if total_len else 0
                speed_mb = ((downloaded - existing_bytes) / (1024 * 1024)) / (now - start_time) if (now - start_time) > 0 else 0
                rem_seconds = (total_len - downloaded) / (speed_mb * 1024 * 1024) if speed_mb > 0 else 0
                print(
                    f"Progreso OpenBioLLM Medico: {mb:.1f} MB / {tot_mb:.1f} MB ({pct:.1f}%) "
                    f"@ {speed_mb:.2f} MB/s · ETA: {rem_seconds/60:.1f} min",
                    flush=True
                )
                last_print = now

    if os.path.exists(DEST_FILE):
        os.remove(DEST_FILE)
    os.rename(PART_FILE, DEST_FILE)
    elapsed = time.time() - start_time
    print(f"SUCCESS: Modelo Medico SOTA OpenBioLLM-8B listo: {os.path.getsize(DEST_FILE)} bytes en {elapsed:.1f} s", flush=True)
except Exception as e:
    print(f"Error descargando modelo medico: {e}", flush=True)
    sys.exit(1)
