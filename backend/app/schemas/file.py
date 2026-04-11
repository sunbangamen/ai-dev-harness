from pydantic import BaseModel
from typing import List, Optional


# 파일 트리의 한 항목
class FileTreeItem(BaseModel):
    name: str           # 파일/폴더 이름
    path: str           # 프로젝트 기준 상대 경로
    type: str           # "file" 또는 "directory"
    size: Optional[int] = None  # 파일 크기 (파일일 때만)


# 파일 목록 조회 응답
class FileTreeResponse(BaseModel):
    path: str           # 조회한 경로
    items: List[FileTreeItem]


# 파일 내용 조회 응답
class FileContentResponse(BaseModel):
    path: str           # 파일 경로
    content: str        # 파일 내용


# 파일 저장 요청
class FileSaveRequest(BaseModel):
    project_id: str     # 프로젝트 ID
    path: str           # 파일 경로 (프로젝트 기준)
    content: str        # 저장할 내용


# 파일 저장 응답
class FileSaveResponse(BaseModel):
    success: bool       # 저장 성공 여부
    path: str           # 저장한 파일 경로
