from pathlib import Path
from typing import List
import shutil
from backend.app.schemas.file import (
    FileTreeItem,
    FileTreeResponse,
    FileContentResponse,
    FileSaveResponse,
    DeleteResponse,
    MoveResponse,
    CreateDirectoryResponse,
    SearchResultItem,
    SearchResponse,
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


def delete_path(project_id: str, path: str) -> DeleteResponse:
    """
    파일이나 디렉토리를 삭제합니다.
    디렉토리는 내부가 비어있지 않아도 삭제됩니다 (재귀 삭제).

    주의: 프로젝트 루트 (path="") 삭제는 금지됩니다.

    Args:
        project_id: 프로젝트 ID
        path: 삭제할 파일/디렉토리의 상대 경로

    Returns:
        DeleteResponse: 삭제 성공 여부와 경로

    Raises:
        ProjectNotFoundError: 프로젝트를 찾을 수 없는 경우 (404)
        FileLikeError: 루트 삭제 시도 또는 경로가 파일이 아닌 경우 (400)
        NotFoundError: 파일/디렉토리가 없는 경우 (404)
        SecurityViolationError: 경로 보안 위반 또는 권한 없음 (403)
        IOError: 삭제 실패 (500)
    """
    # 프로젝트 경로 획득
    project_path = _get_project_path(project_id)

    # 루트 삭제 금지
    if not path or path.strip() == "":
        raise FileLikeError("Cannot delete project root")

    # 안전한 경로로 resolve
    safe_path = resolve_safe_path(project_path, path)

    # 경로 존재 확인
    if not safe_path.exists():
        raise NotFoundError(f"Path not found: {path}")

    # 삭제 시도
    try:
        if safe_path.is_dir():
            shutil.rmtree(safe_path)
        else:
            safe_path.unlink()
    except PermissionError as e:
        raise SecurityViolationError(f"Permission denied: cannot delete {path}")
    except OSError as e:
        raise IOError(f"Failed to delete path: {e}")
    except Exception as e:
        raise IOError(f"Failed to delete path: {e}")

    return DeleteResponse(success=True, path=path)


def move_path(project_id: str, src_path: str, dest_path: str) -> MoveResponse:
    """
    파일이나 디렉토리를 이동하거나 이름을 변경합니다.

    주의: 프로젝트 루트 (path="") 이동/이름변경은 금지됩니다.
    대상 경로가 이미 존재하면 400 에러를 반환합니다.

    Args:
        project_id: 프로젝트 ID
        src_path: 원본 파일/디렉토리의 상대 경로
        dest_path: 대상 파일/디렉토리의 상대 경로

    Returns:
        MoveResponse: 이동 성공 여부와 경로

    Raises:
        ProjectNotFoundError: 프로젝트를 찾을 수 없는 경우 (404)
        FileLikeError: 루트 이동 시도, 대상이 이미 존재, 부모 디렉토리 없음 (400)
        NotFoundError: 원본 파일/디렉토리가 없는 경우 (404)
        SecurityViolationError: 경로 보안 위반 또는 권한 없음 (403)
        IOError: 이동 실패 (500)
    """
    # 프로젝트 경로 획득
    project_path = _get_project_path(project_id)

    # 루트 이동/이름변경 금지
    if not src_path or src_path.strip() == "":
        raise FileLikeError("Cannot move project root")
    if not dest_path or dest_path.strip() == "":
        raise FileLikeError("Cannot move to project root")

    # 원본과 대상 경로 안전 처리
    src_safe_path = resolve_safe_path(project_path, src_path)
    dest_safe_path = resolve_safe_path(project_path, dest_path)

    # 원본 존재 확인
    if not src_safe_path.exists():
        raise NotFoundError(f"Source path not found: {src_path}")

    # 대상이 이미 존재하면 400 거절
    if dest_safe_path.exists():
        raise FileLikeError(f"Destination already exists: {dest_path}")

    # 대상 부모 디렉토리 확인
    dest_parent = dest_safe_path.parent
    if not dest_parent.exists():
        raise FileLikeError(f"Parent directory does not exist: {dest_path}")

    # 이동 시도
    try:
        src_safe_path.rename(dest_safe_path)
    except PermissionError as e:
        raise SecurityViolationError(f"Permission denied: cannot move {src_path}")
    except OSError as e:
        raise IOError(f"Failed to move path: {e}")
    except Exception as e:
        raise IOError(f"Failed to move path: {e}")

    return MoveResponse(success=True, src_path=src_path, dest_path=dest_path)


def create_directory(project_id: str, path: str) -> CreateDirectoryResponse:
    """
    디렉토리를 생성합니다.
    중첩된 경로는 자동으로 생성됩니다.

    Args:
        project_id: 프로젝트 ID
        path: 생성할 디렉토리의 상대 경로

    Returns:
        CreateDirectoryResponse: 생성 성공 여부와 경로

    Raises:
        ProjectNotFoundError: 프로젝트를 찾을 수 없는 경우 (404)
        FileLikeError: 경로가 이미 존재하는 경우 (400)
        SecurityViolationError: 경로 보안 위반 또는 권한 없음 (403)
        IOError: 생성 실패 (500)
    """
    # 프로젝트 경로 획득
    project_path = _get_project_path(project_id)

    # 안전한 경로로 resolve
    safe_path = resolve_safe_path(project_path, path)

    # 이미 존재 확인
    if safe_path.exists():
        raise FileLikeError(f"Path already exists: {path}")

    # 디렉토리 생성
    try:
        safe_path.mkdir(parents=True, exist_ok=False)
    except PermissionError as e:
        raise SecurityViolationError(f"Permission denied: cannot create directory {path}")
    except FileExistsError as e:
        raise FileLikeError(f"Path already exists: {path}")
    except OSError as e:
        raise IOError(f"Failed to create directory: {e}")
    except Exception as e:
        raise IOError(f"Failed to create directory: {e}")

    return CreateDirectoryResponse(success=True, path=path)


def search_files(project_id: str, query: str) -> SearchResponse:
    """
    프로젝트 내에서 파일/디렉토리를 이름으로 검색합니다.
    재귀적으로 모든 하위 항목을 탐색합니다.

    주의: query는 반드시 한 글자 이상의 문자를 포함해야 합니다.

    Args:
        project_id: 프로젝트 ID
        query: 검색 키워드 (부분 문자열 일치, 비어있으면 안됨)

    Returns:
        SearchResponse: 검색 결과 목록

    Raises:
        ProjectNotFoundError: 프로젝트를 찾을 수 없는 경우 (404)
        FileLikeError: 검색 키워드가 비어있는 경우 (400)
        SecurityViolationError: 권한 없음 (403)
        IOError: 검색 중 예외 (500)
    """
    # 검색 키워드 유효성 확인
    if not query or not query.strip():
        raise FileLikeError("Search query cannot be empty")

    # 프로젝트 경로 획득
    project_path = _get_project_path(project_id)
    base_path = Path(project_path)

    results: List[SearchResultItem] = []

    # 재귀 탐색
    try:
        for item in base_path.rglob("*"):
            # 항목 이름이 query를 포함하는지 확인
            if query.lower() in item.name.lower():
                relative = item.relative_to(base_path)
                relative_str = str(relative).replace("\\", "/")

                if item.is_dir():
                    item_type = "directory"
                else:
                    item_type = "file"

                results.append(
                    SearchResultItem(
                        name=item.name,
                        path=relative_str,
                        type=item_type,
                    )
                )
    except PermissionError as e:
        raise SecurityViolationError(f"Permission denied: cannot search in project")
    except Exception as e:
        raise IOError(f"Failed to search files: {e}")

    # 결과 정렬
    results.sort(key=lambda x: x.path)

    return SearchResponse(query=query, results=results)
