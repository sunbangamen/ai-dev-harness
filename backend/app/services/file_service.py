from pathlib import Path
from typing import List
from backend.app.schemas.file import (
    FileTreeItem,
    FileTreeResponse,
    FileContentResponse,
    FileSaveResponse,
)
from backend.app.services import project_service
from backend.app.exceptions import (
    SecurityViolationError,
    ProjectNotFoundError,
    NotFoundError,
    FileLikeError,
)


def resolve_safe_path(base_path: str, relative_path: str) -> Path:
    """
    base_path를 루트로 하여 relative_path를 안전하게 resolve합니다.
    Path traversal 공격 방지

    Args:
        base_path: 프로젝트 루트 경로
        relative_path: 사용자가 제공한 상대 경로

    Returns:
        Path: resolve된 절대 경로

    Raises:
        SecurityViolationError: 루트 밖으로 벗어나려는 경우 (403)
    """
    base = Path(base_path).resolve()
    target = (base / relative_path).resolve()

    # target이 base 안에 있는지 확인
    try:
        target.relative_to(base)
    except ValueError:
        raise SecurityViolationError(f"Access denied: path is outside the allowed directory")

    return target


def _get_project_path(project_id: str) -> str:
    """
    project_id로부터 프로젝트 경로를 조회합니다.

    Args:
        project_id: 프로젝트 ID (Step 1에서 등록한)

    Returns:
        str: 프로젝트 경로

    Raises:
        ProjectNotFoundError: 프로젝트를 찾을 수 없는 경우 (404)
    """
    projects = project_service.get_all_projects()
    for project in projects:
        if project.get("id") == project_id:
            return project["path"]

    raise ProjectNotFoundError(f"Project not found: {project_id}")


def list_directory(project_id: str, path: str = "") -> FileTreeResponse:
    """
    프로젝트 내 디렉토리의 파일/폴더 목록을 조회합니다.

    Args:
        project_id: 프로젝트 ID
        path: 조회할 상대 경로 (기본값: 루트)

    Returns:
        FileTreeResponse: 파일/폴더 목록

    Raises:
        ProjectNotFoundError: 프로젝트를 찾을 수 없는 경우 (404)
        NotFoundError: 경로가 존재하지 않음 (404)
        FileLikeError: 경로가 파일임 (400)
        SecurityViolationError: 경로 보안 위반 또는 권한 없음 (403)
    """
    # 프로젝트 경로 획득
    project_path = _get_project_path(project_id)

    # 안전한 경로로 resolve
    safe_path = resolve_safe_path(project_path, path)

    # 경로 존재 확인
    if not safe_path.exists():
        raise NotFoundError(f"Path not found: {path}")

    # 디렉토리 확인
    if not safe_path.is_dir():
        raise FileLikeError(f"Path is not a directory: {path}")

    # 디렉토리 내용 조회
    items: List[FileTreeItem] = []
    try:
        for item in sorted(safe_path.iterdir()):
            relative = item.relative_to(Path(project_path))
            relative_str = str(relative).replace("\\", "/")

            if item.is_dir():
                items.append(
                    FileTreeItem(
                        name=item.name,
                        path=relative_str,
                        type="directory",
                    )
                )
            else:
                items.append(
                    FileTreeItem(
                        name=item.name,
                        path=relative_str,
                        type="file",
                        size=item.stat().st_size,
                    )
                )
    except PermissionError as e:
        # 권한 문제 → 403 Forbidden
        raise SecurityViolationError(f"Permission denied: cannot read directory {path}")

    return FileTreeResponse(path=path, items=items)


def read_file(project_id: str, path: str) -> FileContentResponse:
    """
    프로젝트 내 파일의 내용을 읽습니다.
    텍스트 파일만 지원합니다 (UTF-8).

    Args:
        project_id: 프로젝트 ID
        path: 읽을 파일의 상대 경로

    Returns:
        FileContentResponse: 파일 경로와 내용

    Raises:
        ProjectNotFoundError: 프로젝트를 찾을 수 없는 경우 (404)
        NotFoundError: 파일이 없는 경우 (404)
        FileLikeError: 파일이 디렉토리이거나 디코딩 실패 (400)
        SecurityViolationError: 경로 보안 위반 또는 권한 없음 (403)
    """
    # 프로젝트 경로 획득
    project_path = _get_project_path(project_id)

    # 안전한 경로로 resolve
    safe_path = resolve_safe_path(project_path, path)

    # 파일 존재 확인
    if not safe_path.exists():
        raise NotFoundError(f"File not found: {path}")

    # 디렉토리 확인
    if safe_path.is_dir():
        raise FileLikeError(f"Path is a directory, not a file: {path}")

    # 파일 읽기 (UTF-8)
    try:
        content = safe_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        # 디코딩 실패 → 400 Bad Request (파일 형식 문제)
        raise FileLikeError(f"File cannot be decoded as UTF-8: {path}")
    except PermissionError as e:
        # 권한 문제 → 403 Forbidden
        raise SecurityViolationError(f"Permission denied: cannot read {path}")

    return FileContentResponse(path=path, content=content)


def write_file(project_id: str, path: str, content: str) -> FileSaveResponse:
    """
    프로젝트 내 파일의 내용을 저장합니다.
    기존 파일은 덮어쓰기, 없으면 새 파일 생성.
    상위 디렉토리는 존재해야 합니다.

    Args:
        project_id: 프로젝트 ID
        path: 저장할 파일의 상대 경로
        content: 저장할 내용

    Returns:
        FileSaveResponse: 저장 성공 여부와 파일 경로

    Raises:
        ProjectNotFoundError: 프로젝트를 찾을 수 없는 경우 (404)
        FileLikeError: 저장 대상이 디렉토리, 상위 디렉토리 없음, 인코딩 실패 (400)
        SecurityViolationError: 경로 보안 위반 또는 권한 없음 (403)
        IOError: 예상 못 한 저장 실패 (500)
    """
    # 프로젝트 경로 획득
    project_path = _get_project_path(project_id)

    # 안전한 경로로 resolve
    safe_path = resolve_safe_path(project_path, path)

    # 저장 대상이 디렉토리면 에러
    if safe_path.exists() and safe_path.is_dir():
        raise FileLikeError(f"Target is a directory, not a file: {path}")

    # 상위 디렉토리 확인
    parent_dir = safe_path.parent
    if not parent_dir.exists():
        raise FileLikeError(f"Parent directory does not exist: {path}")

    # 파일 저장
    try:
        safe_path.write_text(content, encoding="utf-8")
    except PermissionError as e:
        # 권한 문제 → 403 Forbidden
        raise SecurityViolationError(f"Permission denied: cannot write to {path}")
    except UnicodeEncodeError as e:
        # 인코딩 실패 → 400 Bad Request (입력 문제)
        raise FileLikeError(f"Content cannot be encoded as UTF-8: {e}")
    except OSError as e:
        # 디스크 풀, 파일시스템 에러 등 → 500 Internal Server Error
        raise IOError(f"Failed to write file: {e}")
    except Exception as e:
        # 예상 못 한 예외 → 500 Internal Server Error
        raise IOError(f"Failed to write file: {e}")

    return FileSaveResponse(success=True, path=path)
