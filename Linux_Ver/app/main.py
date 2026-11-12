import re
from contextlib import asynccontextmanager
from urllib.parse import unquote
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.api.routes_input import router as input_router
from app.api.routes_patients import router as patients_router
from app.api.routes_institutions import router as institutions_router
from app.api.routes_consultations import router as consultations_router
from app.api.routes_appointments import router as appointments_router
from app.api.routes_wearables import router as wearables_router
from app.api.routes_analytics import router as analytics_router
from app.api.routes_citizen import router as citizen_router
from app.api.routes_security import router as security_router, normalize_role
from app.api.routes_legal import router as legal_router
from app.api.routes_auth import router as auth_router
from app.core.crypto_vault import verify_session_token
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
            print("[Startup] LLM cargado [OK]")
        except Exception as e:
            print(f"[Startup] [WARN] No se pudo pre-cargar el LLM: {e}")
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
    print("[OK] MedicAItion iniciado correctamente")

    yield

    # ── SHUTDOWN ──
    print("[INFO] MedicAItion detenido")


app = FastAPI(
    title="MedicAItion",
    description="Sistema de captura, estandarización y gestión de datos médicos clínicos",
    version="3.0-NOM004",
    lifespan=lifespan,
)

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


_PATIENT_SELF_PATTERNS = (
    re.compile(r"^/api/patient-portal/([A-Za-z0-9_-]+)(?:/logs)?$"),
    re.compile(r"^/api/auth/patient-appointments/([A-Za-z0-9_-]+)$"),
    re.compile(r"^/api/ice/([A-Za-z0-9_-]+)(?:/qr)?$"),
    re.compile(r"^/api/legal/consent/([A-Za-z0-9_-]+)(?:/revoke)?$"),
    re.compile(r"^/api/legal/arco/([A-Za-z0-9_-]+)/export$"),
)


class RolePrivacyIsolationMiddleware(BaseHTTPMiddleware):
    """
    Separa estrictamente la sesión del Paciente ("Mi Salud Hoy") de la sesión
    del Personal Clínico, y evita que Recepción lea contenido clínico privado.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        token = (
            request.headers.get("X-Session-Token")
            or request.headers.get("X-Patient-Token")
            or ""
        ).strip()
        claims = None
        if token:
            claims = verify_session_token(token)
            if not claims:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Sesión expirada o token inválido. Inicia sesión nuevamente."},
                )

        raw_role = unquote(request.headers.get("X-Operator-Role") or "")
        role = normalize_role(raw_role) if raw_role else (
            "Paciente" if (claims and claims.get("type") == "patient") else "Médico"
        )
        if claims and claims.get("type") == "patient":
            role = "Paciente"

        if role == "Paciente":
            if path in (
                "/api/status",
                "/api/legal/framework",
                "/api/auth/roles",
                "/api/auth/staff-login",
                "/api/auth/patient-login",
                "/api/auth/me",
            ):
                return await call_next(request)

            own_curp = (
                (claims.get("sub") if claims and claims.get("type") == "patient" else None)
                or request.headers.get("X-Patient-Curp")
                or ""
            ).strip().upper()

            for pat in _PATIENT_SELF_PATTERNS:
                m = pat.match(path)
                if m:
                    target_curp = m.group(1).upper()
                    if target_curp in ("SYSTEM", "SISTEMA") or not own_curp or target_curp != own_curp:
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "Privacidad ARCO: solo puedes consultar tu propio expediente personal."},
                        )
                    return await call_next(request)

            return JSONResponse(
                status_code=403,
                content={"detail": "Acceso restringido: la sesión de Paciente solo permite su Portal Personal y Derechos ARCO."},
            )

        if role == "Recepción":
            if any(
                path.startswith(p)
                for p in ("/api/consultations", "/api/input", "/api/security/audit-logs")
            ) or any(
                suffix in path for suffix in ("/ask", "/fhir", "/summary-ia")
            ):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Privacidad LFPDPPP: el rol Recepción no tiene acceso a notas médicas ni contenido clínico."},
                )

        return await call_next(request)


app.add_middleware(RolePrivacyIsolationMiddleware)
app.add_middleware(NoCacheMiddleware)

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
app.include_router(appointments_router)
app.include_router(wearables_router)
app.include_router(analytics_router)
app.include_router(citizen_router)
app.include_router(security_router)
app.include_router(legal_router)
app.include_router(auth_router)

# Servir frontend estático
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

