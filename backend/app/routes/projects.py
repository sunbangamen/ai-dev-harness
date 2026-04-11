from fastapi import APIRouter, HTTPException
from backend.app.schemas.project import ProjectCreate, ProjectResponse
from backend.app.services import project_service

# 라우터 생성
router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
def list_projects():
    """저장된 모든 프로젝트를 조회합니다."""
    projects = project_service.get_all_projects()
    # id, name, path, created_at 필드 반환
    return [{"id": p.get("id", p.get("name")),
             "name": p["name"],
             "path": p["path"],
             "created_at": p.get("created_at", "")}
            for p in projects]


@router.post("", response_model=ProjectResponse)
def create_project(project: ProjectCreate):
    """
    새로운 프로젝트를 등록합니다.
    - 경로 존재 여부 확인
    - name과 path 중복 체크
    - ai 폴더 및 기본 파일 자동 생성
    """
    try:
        result = project_service.add_project(project.name, project.path)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
