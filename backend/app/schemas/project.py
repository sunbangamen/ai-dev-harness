from pydantic import BaseModel


# 프로젝트 생성 요청 스키마
class ProjectCreate(BaseModel):
    name: str
    path: str


# 프로젝트 응답 스키마
class ProjectResponse(BaseModel):
    id: str           # UUID 문자열
    name: str
    path: str
    created_at: str   # ISO 형식 타임스탐프
