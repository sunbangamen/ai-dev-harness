from fastapi import APIRouter, HTTPException
from backend.app.schemas.file import (
    FileTreeResponse,
    FileContentResponse,
    FileSaveRequest,
    FileSaveResponse,
)
from backend.app.services import file_service
from backend.app.exceptions import (
    SecurityViolationError,
    ProjectNotFoundError,
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
