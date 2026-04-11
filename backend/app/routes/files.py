from fastapi import APIRouter, HTTPException
from backend.app.schemas.file import (
    FileTreeResponse,
    FileContentResponse,
    FileSaveRequest,
    FileSaveResponse,
    DeleteResponse,
    MoveRequest,
    MoveResponse,
    CreateDirectoryRequest,
    CreateDirectoryResponse,
    SearchResponse,
)
from backend.app.services import file_service
from backend.app.exceptions import (
    SecurityViolationError,
    ProjectNotFoundError,
    NotFoundError,
    FileLikeError,
)

# 라우터 생성
router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/tree", response_model=FileTreeResponse)
def get_file_tree(project_id: str, path: str = ""):
    """
    프로젝트 내 디렉토리 목록을 조회합니다.

    Args:
        project_id: 프로젝트 ID
        path: 조회할 경로 (기본값: 루트)

    Returns:
        FileTreeResponse: 파일/폴더 목록
    """
    try:
        result = file_service.list_directory(project_id, path)
        return result
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SecurityViolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileLikeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/content", response_model=FileContentResponse)
def get_file_content(project_id: str, path: str):
    """
    파일의 내용을 읽습니다 (텍스트).

    Args:
        project_id: 프로젝트 ID
        path: 읽을 파일 경로

    Returns:
        FileContentResponse: 파일 내용
    """
    try:
        result = file_service.read_file(project_id, path)
        return result
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SecurityViolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileLikeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/content", response_model=FileSaveResponse)
def save_file_content(request: FileSaveRequest):
    """
    파일의 내용을 저장합니다 (덮어쓰기).

    Args:
        request: FileSaveRequest (project_id, path, content)

    Returns:
        FileSaveResponse: 저장 성공 여부
    """
    try:
        result = file_service.write_file(
            request.project_id, request.path, request.content
        )
        return result
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SecurityViolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileLikeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IOError as e:
        # 예상 못 한 시스템 에러 (디스크 풀, 파일시스템 에러 등) → 500
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("", response_model=DeleteResponse)
def delete_file_or_directory(project_id: str, path: str):
    """
    파일이나 디렉토리를 삭제합니다 (재귀 삭제 가능).

    Args:
        project_id: 프로젝트 ID
        path: 삭제할 경로

    Returns:
        DeleteResponse: 삭제 성공 여부
    """
    try:
        result = file_service.delete_path(project_id, path)
        return result
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SecurityViolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileLikeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/move", response_model=MoveResponse)
def move_file_or_directory(request: MoveRequest):
    """
    파일이나 디렉토리를 이동하거나 이름을 변경합니다.

    Args:
        request: MoveRequest (project_id, src_path, dest_path)

    Returns:
        MoveResponse: 이동 성공 여부
    """
    try:
        result = file_service.move_path(
            request.project_id, request.src_path, request.dest_path
        )
        return result
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SecurityViolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileLikeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/directory", response_model=CreateDirectoryResponse)
def create_new_directory(request: CreateDirectoryRequest):
    """
    새 디렉토리를 생성합니다 (중첩 경로 자동 생성 가능).

    Args:
        request: CreateDirectoryRequest (project_id, path)

    Returns:
        CreateDirectoryResponse: 생성 성공 여부
    """
    try:
        result = file_service.create_directory(request.project_id, request.path)
        return result
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SecurityViolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileLikeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/search", response_model=SearchResponse)
def search_files_by_name(project_id: str, query: str):
    """
    파일/디렉토리를 이름으로 검색합니다 (부분 문자열 일치, 대소문자 무관).

    Args:
        project_id: 프로젝트 ID
        query: 검색 키워드

    Returns:
        SearchResponse: 검색 결과 목록
    """
    try:
        result = file_service.search_files(project_id, query)
        return result
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SecurityViolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
