"""FastAPI 시작점. 영역 라우터 6개(core + a0~a4)만 등록한다. 1일차 고정, PM만 수정 (AGENTS 4-3). 담당: KHS

실행: cd backend && uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.a0_reader.router import router as reader_router
from app.a1_history.router import router as history_router
from app.a2_registry.router import router as registry_router
from app.a3_judge.router import router as judge_router
from app.a4_settings.router import router as settings_router
from app.core.auth.deps import require_login
from app.core.auth.router import router as auth_router
from app.core.config import get_settings
from app.core.errors import install_handlers
from app.core.router import router as core_router
from app.core.storage import local_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    local_db.migrate()
    yield


app = FastAPI(title="declaration_list", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_handlers(app)

API = "/api"
# 로그인 없이: /core/health, /core/auth/*
app.include_router(core_router, prefix=API)
app.include_router(auth_router, prefix=API)
# 나머지는 전부 로그인 필요
LOGIN = [Depends(require_login)]
for r in (reader_router, history_router, registry_router, judge_router, settings_router):
    app.include_router(r, prefix=API, dependencies=LOGIN)
