"""
커스텀 예외 클래스들
"""


class SecurityViolationError(Exception):
    """
    보안 위반 에러 (예: path traversal 시도)
    HTTP 403으로 매핑됨
    """
    pass


class ProjectNotFoundError(Exception):
    """
    프로젝트를 찾을 수 없음
    HTTP 404로 매핑됨
    """
    pass


class NotFoundError(Exception):
    """
    파일이나 디렉토리를 찾을 수 없음
    HTTP 404로 매핑됨
    """
    pass


class FileLikeError(Exception):
    """
    파일과 관련된 형식/타입 에러 (인코딩, 타입 불일치 등)
    HTTP 400으로 매핑됨
    """
    pass
