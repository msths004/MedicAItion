"""
app/core/local_llm_runner.py — Motor de Inferencia LLM 100% Local (llama-cpp-python / GGUF)
========================================================================================
Ejecuta modelos LLM cuantizados (GGUF) directamente en la CPU/GPU de la máquina sin
depender de internet ni de servicios externos.
"""

from __future__ import annotations

import glob
import os
import re
import threading
from typing import Any, Dict, Generator, List, Optional

_LLM_LOCK = threading.Lock()
_LLM_INSTANCE = None
_CURRENT_MODEL_PATH: Optional[str] = None


def find_local_gguf_model() -> Optional[str]:
    """Busca modelos .gguf en la carpeta models/ o config.json."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    models_dir = os.path.join(base_dir, "models")
    
    # 1. Preferir arquitectura híbrida RTX 4050 (Qwen3-8B Q4_K_M + medgemma-4b-it) y fallbacks clínicos
    preferred = [
        "Qwen3-8B-Q4_K_M.gguf",
        "qwen3-8b-q4_k_m.gguf",
        "medgemma-4b-it-Q4_K_M.gguf",
        "medgemma-4b-it-q4_k_m.gguf",
        "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        "qwen2.5-7b-instruct-q4_k_m.gguf",
        "OpenBioLLM-Llama3-8B-Q4_K_M.gguf",
        "OpenBioLLM-Llama3-8B-Q3_K_M.gguf",
        "BioMistral-7B.Q4_K_M.gguf",
        "Llama3-Med42-8B-Q4_K_M.gguf",
        "Llama3-Med42-8B.Q2_K.gguf",
        "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
    ]
    for pref in preferred:
        p = os.path.join(models_dir, pref)
        if os.path.exists(p) and os.path.getsize(p) > 50 * 1024 * 1024:
            return p

    # 2. Cualquier archivo .gguf completo en models/
    if os.path.isdir(models_dir):
        ggufs = glob.glob(os.path.join(models_dir, "*.gguf"))
        for g in ggufs:
            if not g.endswith(".part") and os.path.getsize(g) > 50 * 1024 * 1024:
                return g

    # 3. Revisar config.json si existe
    cfg_file = os.path.join(base_dir, "config.json")
    if os.path.exists(cfg_file):
        try:
            import json
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            m_path = cfg.get("model_path")
            if m_path and os.path.exists(m_path) and os.path.getsize(m_path) > 50 * 1024 * 1024:
                return m_path
        except Exception:
            pass

    return None


def is_hybrid_sota_gguf(model_path: Optional[str]) -> bool:
    """
    Determina si el archivo GGUF corresponde a la familia híbrida SOTA recomendada
    (Qwen3 / MedGemma / Qwen2.5 >= 3B / Gemma-2/3 / Llama-3.1) y excluye modelos
    legados con alucinación de rol o baja capacidad generalista (OpenBioLLM-8B, 0.5B).
    """
    if not model_path:
        return False
    name = os.path.basename(model_path).lower()
    if any(legacy in name for legacy in ("openbiollm", "0.5b", "biomistral")):
        return False
    return any(sota in name for sota in ("qwen3", "medgemma", "qwen2.5-7b", "qwen2.5-3b", "gemma-2", "gemma-3", "llama-3.1"))


def get_local_llm_status() -> Dict[str, Any]:
    """Devuelve información sobre el estado del LLM local GGUF."""
    model_path = find_local_gguf_model()
    has_model = model_path is not None
    is_sota = is_hybrid_sota_gguf(model_path)
    size_mb = round(os.path.getsize(model_path) / (1024 * 1024), 1) if has_model else 0
    model_name = os.path.basename(model_path) if has_model else "Ninguno descargado"
    
    # Revisar si hay una descarga en progreso
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    part_files = glob.glob(os.path.join(base_dir, "models", "*.part"))
    downloading = len(part_files) > 0
    part_mb = round(os.path.getsize(part_files[0]) / (1024 * 1024), 1) if downloading else 0

    return {
        "has_local_gguf": has_model,
        "is_hybrid_sota": is_sota,
        "model_name": model_name,
        "model_path": model_path,
        "size_mb": size_mb,
        "is_downloading": downloading,
        "downloaded_part_mb": part_mb,
        "engine_ready": has_model,
    }


def get_llm_instance():
    """Obtiene o inicializa la instancia singleton de Llama."""
    global _LLM_INSTANCE, _CURRENT_MODEL_PATH
    with _LLM_LOCK:
        model_path = find_local_gguf_model()
        if not model_path:
            return None

        if _LLM_INSTANCE is not None and _CURRENT_MODEL_PATH == model_path:
            return _LLM_INSTANCE

        try:
            from app.core.entity_extractor import setup_cuda_dll_path
            setup_cuda_dll_path()
            from llama_cpp import Llama

            cpu_threads = max(1, min(8, (os.cpu_count() or 4) - 1))
            print(f"[LocalLLM] Cargando modelo GGUF: {model_path} con {cpu_threads} hilos...")
            
            m_name = os.path.basename(model_path).lower()
            # 100% Capas en GPU RTX 4050 (6 GB VRAM) + KV Cache Q8_0 (type_k=8, type_v=8)
            use_full_gpu = any(tag in m_name for tag in ("qwen3", "medgemma", "8b", "7b", "4b"))
            gpu_layers = -1 if use_full_gpu else 0

            loaded = False
            for ctx_size in (8192, 4096, 2048):
                for use_q8_kv in (True, False):
                    try:
                        kwargs = dict(
                            model_path=model_path,
                            n_ctx=ctx_size,
                            n_threads=cpu_threads,
                            n_batch=512,
                            n_gpu_layers=gpu_layers,
                            verbose=False,
                        )
                        if use_q8_kv:
                            kwargs["type_k"] = 8
                            kwargs["type_v"] = 8
                        _LLM_INSTANCE = Llama(**kwargs)
                        loaded = True
                        break
                    except Exception as e_gpu:
                        print(f"[LocalLLM] Aviso ctx={ctx_size} q8_kv={use_q8_kv} gpu={gpu_layers}: {e_gpu}")
                if loaded:
                    break

            if not loaded:
                _LLM_INSTANCE = Llama(
                    model_path=model_path,
                    n_ctx=2048,
                    n_threads=cpu_threads,
                    n_batch=512,
                    n_gpu_layers=0,
                    verbose=False,
                )
            _CURRENT_MODEL_PATH = model_path
            print("[LocalLLM] Modelo GGUF cargado exitosamente en memoria RAM/VRAM.")
            return _LLM_INSTANCE
        except Exception as e:
            print(f"[LocalLLM] Error cargando modelo GGUF '{model_path}': {e}")
            return None


def detect_prompt_language(text: str) -> str:
    """
    Detecta el idioma predominante de la consulta para responder en el mismo idioma:
    'es' (español), 'en' (inglés), 'fr' (francés), 'pt' (portugués), 'de' (alemán), o 'auto'.
    """
    if not text:
        return "es"
    low = text.lower()

    # Caracteres distintivos del español
    if any(c in low for c in ["¿", "¡", "ñ", "á", "é", "í", "ó", "ú"]):
        return "es"

    es_words = {"que", "como", "cual", "cuales", "donde", "quien", "por", "para", "dolor", "fiebre", "dosis", "paciente", "hola", "buenos", "dias", "tardes", "noches", "gracias", "salud", "enfermedad", "tratamiento", "sintomas", "presion", "sangre", "medicamento", "medico", "estomago", "cabeza"}
    en_words = {"what", "how", "who", "when", "why", "where", "which", "is", "are", "the", "can", "could", "should", "please", "help", "hello", "hi", "good", "morning", "afternoon", "evening", "pain", "fever", "dose", "dosage", "patient", "treatment", "symptoms", "burn", "disease", "blood", "pressure", "stomach", "headache", "doctor"}
    fr_words = {"comment", "quel", "quelle", "quels", "quelles", "pourquoi", "bonjour", "bonsoir", "merci", "douleur", "fievre", "traitement", "symptomes", "malade", "medecin"}
    pt_words = {"como", "qual", "quais", "onde", "porque", "ola", "obrigado", "obrigada", "febre", "tratamento", "sintomas", "doente", "remedio"}
    de_words = {"wie", "was", "wer", "wo", "warum", "hallo", "guten", "morgen", "danke", "schmerz", "fieber", "behandlung", "symptome", "arzt"}

    tokens = set(re.findall(r"\b\w+\b", low))
    scores = [
        ("es", len(tokens & es_words)),
        ("en", len(tokens & en_words)),
        ("fr", len(tokens & fr_words)),
        ("pt", len(tokens & pt_words)),
        ("de", len(tokens & de_words)),
    ]
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[0][0] if scores[0][1] > 0 else "auto"


def stream_local_llm_chat(
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> Generator[str, None, None]:
    """
    Genera tokens en streaming utilizando el modelo GGUF local (Qwen3 / MedGemma / Llama)
    con tokenización de tokens especiales y Sliding Window ya aplicado por el orquestador.
    """
    llm = get_llm_instance()
    if llm is None:
        return

    m_name = os.path.basename(_CURRENT_MODEL_PATH or "").lower()

    default_sys = (
        "Eres Dr. Oso (Pulso), Sistema de IA Híbrida integrado en MedicAItion. "
        "Asistes al médico tratante; jamás asumas la identidad de ningún paciente. "
        "Responde en el mismo idioma que el usuario."
    )

    processed_messages = []
    has_system = False
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            has_system = True
        processed_messages.append({"role": role, "content": content})

    if not has_system:
        processed_messages.insert(0, {"role": "system", "content": default_sys})

    # Formateo nativo según arquitectura (Gemma/MedGemma vs Llama-3 vs Qwen3 ChatML)
    if "gemma" in m_name:
        sys_msg = ""
        parts = []
        for m in processed_messages:
            if m["role"] == "system":
                sys_msg = m["content"]
                continue
            r = "model" if m["role"] == "assistant" else "user"
            txt = f"{sys_msg}\n\n{m['content']}" if (r == "user" and sys_msg) else m["content"]
            if r == "user" and sys_msg:
                sys_msg = ""
            parts.append(f"<start_of_turn>{r}\n{txt}<end_of_turn>")
        parts.append("<start_of_turn>model\n")
        prompt = "\n".join(parts)
        stop_tokens_str = ["<end_of_turn>", "<eos>"]
    elif "llama" in m_name or "openbiollm" in m_name or "med42" in m_name:
        prompt = "<|begin_of_text|>"
        for m in processed_messages:
            prompt += f"<|start_header_id|>{m['role']}<|end_header_id|>\n\n{m['content']}<|eot_id|>"
        prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        stop_tokens_str = ["<|eot_id|>", "<|end_of_text|>"]
    else:
        # ChatML nativo para Qwen3, Qwen2.5, Mistral, BioMistral
        parts = []
        for m in processed_messages:
            parts.append(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>")
        parts.append("<|im_start|>assistant\n")
        prompt = "\n".join(parts)
        stop_tokens_str = ["<|im_end|>", "<|endoftext|>"]

    try:
        input_tokens = llm.tokenize(prompt.encode("utf-8"), special=True)
        tokens_generated = 0
        eos_id = llm.token_eos()

        for token_id in llm.generate(input_tokens, temp=temperature):
            if token_id == eos_id:
                break
            tokens_generated += 1
            if tokens_generated > max_tokens:
                break
            text_chunk = llm.detokenize([token_id]).decode("utf-8", errors="replace")
            if any(st in text_chunk for st in stop_tokens_str):
                break
            if text_chunk:
                yield text_chunk
    except Exception as e:
        print(f"[LocalLLM] Error durante streaming: {e}")
        yield f"\n\n*(Error local en inferencia GGUF: {e})*"
