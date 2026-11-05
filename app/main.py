from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.api.routes_input import router as input_router
from app.api.routes_patients import router as patients_router
from app.api.routes_institutions import router as institutions_router
from app.api.routes_consultations import router as consultations_router
from app.db.local_db import create_tables as create_local_tables
from app.db.global_db import create_tables as create_global_tables, register_institution

llm_preload_finished = False


def _preload_models():
    """
    Pre-carga los modelos de IA en memoria durante el arranque del servidor.
    Esto evita que el primer paciente sufra una espera de 60-120 segundos.
    """
    import threading

    def _load():
        global llm_preload_finished
        try:
            print("[Startup] Pre-cargando modelo LLM médico...")
            from app.core.entity_extractor import _get_llm
            _get_llm()
            print("[Startup] LLM cargado ✅")
        except Exception as e:
            print(f"[Startup] ⚠️  No se pudo pre-cargar el LLM: {e}")
            print("[Startup] Se intentará cargar cuando llegue el primer paciente.")
        finally:
            llm_preload_finished = True

    # Cargar en un hilo para no bloquear el evento de startup
    # (uvicorn requiere que startup termine para aceptar conexiones)
    thread = threading.Thread(target=_load, daemon=True)
    thread.start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager para FastAPI (reemplaza el deprecated @app.on_event).
    Ejecuta la inicialización al arrancar y la limpieza al cerrar.
    """
    # ── STARTUP ──
    create_local_tables()
    create_global_tables()
    register_institution(
        clues="YUC-CR-001",
        nombre="Cruz Roja Mérida",
        ubicacion="Mérida, Yucatán",
    )
    _preload_models()
    print("✅ MedicAItion iniciado correctamente")

    yield

    # ── SHUTDOWN ──
    print("🔒 MedicAItion detenido")


app = FastAPI(
    title="MedicAItion",
    description="Sistema de captura, estandarización y gestión de datos médicos clínicos",
    version="3.0-NOM004",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status")
def get_status():
    global llm_preload_finished
    if llm_preload_finished:
        return {"status": "ready", "message": "Sistema listo"}
    else:
        return {"status": "loading", "message": "Cargando motor de Inteligencia Artificial..."}


app.include_router(input_router)
app.include_router(patients_router)
app.include_router(institutions_router)
app.include_router(consultations_router)

# Servir frontend estático
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

