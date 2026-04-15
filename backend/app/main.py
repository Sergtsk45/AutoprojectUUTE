from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.orders import router as orders_router
from app.api.pipeline import router as pipeline_router
from app.api.emails import router as emails_router
from app.api.parsing import router as parsing_router
from app.api.admin import router as admin_router
from app.api.landing import router as landing_router
from app.api.calculator_config import router as calculator_config_router
from app.core.config import settings

STATIC_DIR = Path(__file__).parent.parent / "static"
FRONTEND_DIR = Path("/app/frontend-dist")


def _safe_dist_file(full_path: str) -> Path | None:
    """Файл из каталога сборки фронта или None (в т.ч. при path traversal)."""
    if not full_path or full_path.startswith("/"):
        return None
    if not FRONTEND_DIR.is_dir():
        return None
    try:
        base = FRONTEND_DIR.resolve()
        candidate = (FRONTEND_DIR / full_path).resolve()
        candidate.relative_to(base)
    except (OSError, ValueError, RuntimeError):
        return None
    return candidate if candidate.is_file() else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаём директорию для файлов при старте
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="УУТЭ Проектировщик",
    description="Сервис автоматизированного проектирования узлов учёта тепловой энергии",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — разрешаем запросы с лендинга
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: ограничить вашим доменом
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роуты
app.include_router(orders_router, prefix="/api/v1")
app.include_router(pipeline_router, prefix="/api/v1")
app.include_router(emails_router, prefix="/api/v1")
app.include_router(parsing_router, prefix="/api/v1")
app.include_router(landing_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(calculator_config_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/upload/{order_id}")
async def upload_page(order_id: str):
    """Страница загрузки документов для клиента.

    Клиент получает ссылку в письме:
    https://yourdomain.ru/upload/<order_id>
    """
    return FileResponse(STATIC_DIR / "upload.html", media_type="text/html")


@app.get("/admin")
async def admin_page():
    """Админ-панель для инженера."""
    return FileResponse(STATIC_DIR / "admin.html", media_type="text/html")


@app.get("/payment/{order_id}")
async def payment_page(order_id: str):
    """Страница оплаты для клиента.

    Клиент получает ссылку в письме:
    https://yourdomain.ru/payment/<order_id>
    """
    return FileResponse(STATIC_DIR / "payment.html", media_type="text/html")


# Статика (JS, CSS если понадобятся)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Собранный React (Vite): ./frontend/dist → /app/frontend-dist в prod
if FRONTEND_DIR.exists():
    _frontend_assets = FRONTEND_DIR / "assets"
    if _frontend_assets.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=str(_frontend_assets)),
            name="frontend-assets",
        )


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Статика из сборки (PDF в /downloads/, …) или React SPA."""
    dist_file = _safe_dist_file(full_path)
    if dist_file is not None:
        return FileResponse(dist_file)
    return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")
