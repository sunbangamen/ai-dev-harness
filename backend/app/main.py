from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routes import projects, files

# FastAPI 앱 생성
app = FastAPI(
    title="AI Dev Harness Backend",
    description="로컬 프로젝트 관리 API",
    version="0.1.0"
)

# CORS 미들웨어 설정 (개발 환경용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우트 포함
app.include_router(projects.router)
app.include_router(files.router)


@app.get("/health")
def health_check():
    """서버 상태 확인"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
