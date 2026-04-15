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


# 파일/디렉토리 삭제 응답
class DeleteResponse(BaseModel):
    success: bool       # 삭제 성공 여부
    path: str           # 삭제한 경로


# 파일/디렉토리 이동 요청
class MoveRequest(BaseModel):
    project_id: str     # 프로젝트 ID
    src_path: str       # 원본 경로
    dest_path: str      # 대상 경로


# 파일/디렉토리 이동 응답
class MoveResponse(BaseModel):
    success: bool       # 이동 성공 여부
    src_path: str       # 원본 경로
    dest_path: str      # 대상 경로


# 디렉토리 생성 요청
class CreateDirectoryRequest(BaseModel):
    project_id: str     # 프로젝트 ID
    path: str           # 생성할 디렉토리 경로


# 디렉토리 생성 응답
class CreateDirectoryResponse(BaseModel):
    success: bool       # 생성 성공 여부
    path: str           # 생성한 디렉토리 경로


# 검색 결과 항목
class SearchResultItem(BaseModel):
    name: str           # 파일/폴더 이름
    path: str           # 프로젝트 기준 상대 경로
    type: str           # "file" 또는 "directory"


# 파일/디렉토리 검색 응답
class SearchResponse(BaseModel):
    query: str          # 검색 키워드
    results: List[SearchResultItem]  # 검색 결과


# 파일 생성 요청
class CreateFileRequest(BaseModel):
    project_id: str     # 프로젝트 ID
    path: str           # 생성할 파일 경로
    content: str = ""   # 초기 내용 (기본값: 빈 파일)


# 파일 생성 응답
class CreateFileResponse(BaseModel):
    success: bool       # 생성 성공 여부
    path: str           # 생성한 파일 경로
