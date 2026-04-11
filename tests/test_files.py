import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import project_service


@pytest.fixture
def temp_project():
    """
    테스트용 임시 프로젝트를 생성합니다.
    """
    with TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()

        # 테스트 파일/폴더 생성
        (project_path / "README.md").write_text("# Test Project\n", encoding="utf-8")

        subdir = project_path / "src"
        subdir.mkdir()
        (subdir / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (subdir / "config.json").write_text('{"key": "value"}\n', encoding="utf-8")

        yield {
            "path": str(project_path),
            "name": "test_project",
        }


@pytest.fixture
def registered_project(temp_project):
    """
    프로젝트 저장소에 등록된 프로젝트를 반환합니다.
    """
    # 임시로 config.json 수정
    original_config = project_service.load_config()

    project = temp_project
    project_id = "test-project-uuid"
    project_entry = {
        "id": project_id,
        "name": project["name"],
        "path": project["path"],
        "created_at": "2026-04-11T00:00:00.000000",
    }
    original_config.setdefault("projects", []).append(project_entry)
    project_service.save_config(original_config)

    yield project_id

    # 정리
    original_config["projects"] = [
        p for p in original_config["projects"] if p.get("id") != project_id
    ]
    project_service.save_config(original_config)


client = TestClient(app)


class TestFileTree:
    """파일 목록 조회 테스트"""

    def test_list_root_directory(self, registered_project):
        """루트 디렉토리 목록 조회"""
        response = client.get(f"/api/files/tree?project_id={registered_project}&path=")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["path"] == ""

        # README.md, src 폴더가 있어야 함
        names = [item["name"] for item in data["items"]]
        assert "README.md" in names
        assert "src" in names

        # 파일과 폴더 구분 확인
        for item in data["items"]:
            if item["name"] == "README.md":
                assert item["type"] == "file"
                assert "size" in item
            elif item["name"] == "src":
                assert item["type"] == "directory"

    def test_list_subdirectory(self, registered_project):
        """서브 디렉토리 목록 조회"""
        response = client.get(f"/api/files/tree?project_id={registered_project}&path=src")
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "src"

        names = [item["name"] for item in data["items"]]
        assert "main.py" in names
        assert "config.json" in names

    def test_list_nonexistent_path(self, registered_project):
        """존재하지 않는 경로 조회 (400)"""
        response = client.get(
            f"/api/files/tree?project_id={registered_project}&path=nonexistent"
        )
        assert response.status_code == 400

    def test_list_file_as_directory(self, registered_project):
        """파일을 디렉토리처럼 조회 (400)"""
        response = client.get(
            f"/api/files/tree?project_id={registered_project}&path=README.md"
        )
        assert response.status_code == 400

    def test_path_traversal_attack_with_dotdot(self, registered_project):
        """../ 경로 traversal 공격 차단 (403)"""
        response = client.get(
            f"/api/files/tree?project_id={registered_project}&path=../"
        )
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    def test_path_traversal_attack_with_absolute(self, registered_project):
        """/etc/passwd 같은 절대 경로 차단 (403)"""
        response = client.get(
            f"/api/files/tree?project_id={registered_project}&path=/etc/passwd"
        )
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    def test_nonexistent_project_id(self):
        """존재하지 않는 project_id (404)"""
        response = client.get(
            "/api/files/tree?project_id=nonexistent-project&path="
        )
        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]


class TestFileContent:
    """파일 내용 조회 테스트"""

    def test_read_text_file(self, registered_project):
        """텍스트 파일 읽기"""
        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=README.md"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "README.md"
        assert "# Test Project" in data["content"]

    def test_read_nested_file(self, registered_project):
        """중첩된 파일 읽기"""
        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=src/main.py"
        )
        assert response.status_code == 200
        data = response.json()
        assert "print('hello')" in data["content"]

    def test_read_json_file(self, registered_project):
        """JSON 파일 읽기"""
        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=src/config.json"
        )
        assert response.status_code == 200
        data = response.json()
        assert "key" in data["content"]

    def test_read_nonexistent_file(self, registered_project):
        """존재하지 않는 파일 읽기 (404는 아니고 400)"""
        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=nonexistent.txt"
        )
        # FileLikeError -> 400
        assert response.status_code == 400

    def test_read_directory_as_file(self, registered_project):
        """디렉토리를 파일로 읽기 (400)"""
        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=src"
        )
        assert response.status_code == 400
        assert "directory" in response.json()["detail"].lower()

    def test_path_traversal_on_read(self, registered_project):
        """파일 읽기에서 path traversal 방지 (403)"""
        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=../../../etc/passwd"
        )
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    def test_utf8_decoding_failure(self, registered_project, temp_project):
        """UTF-8 디코딩 실패 시 400 반환"""
        # 바이너리 파일 생성
        binary_file = Path(temp_project["path"]) / "binary.bin"
        binary_file.write_bytes(b"\x80\x81\x82\x83")  # 유효하지 않은 UTF-8

        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=binary.bin"
        )
        assert response.status_code == 400
        assert "decode" in response.json()["detail"].lower()

    def test_nonexistent_project_id(self):
        """존재하지 않는 project_id (404)"""
        response = client.get(
            "/api/files/content?project_id=nonexistent-project&path=README.md"
        )
        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]


class TestFileSave:
    """파일 저장 테스트"""

    def test_save_new_file(self, registered_project):
        """새 파일 저장"""
        response = client.post(
            "/api/files/content",
            json={
                "project_id": registered_project,
                "path": "new_file.txt",
                "content": "Hello, World!\n",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["path"] == "new_file.txt"

        # 실제로 저장되었는지 확인
        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=new_file.txt"
        )
        assert response.status_code == 200
        assert response.json()["content"] == "Hello, World!\n"

    def test_overwrite_existing_file(self, registered_project):
        """기존 파일 덮어쓰기"""
        new_content = "Updated content\n"
        response = client.post(
            "/api/files/content",
            json={
                "project_id": registered_project,
                "path": "README.md",
                "content": new_content,
            },
        )
        assert response.status_code == 200

        # 실제로 변경되었는지 확인
        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=README.md"
        )
        assert response.json()["content"] == new_content

    def test_save_nested_file(self, registered_project):
        """중첩된 경로에 파일 저장"""
        response = client.post(
            "/api/files/content",
            json={
                "project_id": registered_project,
                "path": "src/new_module.py",
                "content": "def hello():\n    pass\n",
            },
        )
        assert response.status_code == 200

        # 실제로 저장되었는지 확인
        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=src/new_module.py"
        )
        assert response.status_code == 200

    def test_save_to_nonexistent_parent(self, registered_project):
        """상위 디렉토리가 없을 때 저장 시도 (400)"""
        response = client.post(
            "/api/files/content",
            json={
                "project_id": registered_project,
                "path": "nonexistent_dir/file.txt",
                "content": "content",
            },
        )
        assert response.status_code == 400
        assert "Parent directory" in response.json()["detail"]

    def test_path_traversal_on_save(self, registered_project):
        """파일 저장에서 path traversal 방지 (403)"""
        response = client.post(
            "/api/files/content",
            json={
                "project_id": registered_project,
                "path": "../../../tmp/evil.txt",
                "content": "evil",
            },
        )
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    def test_save_to_directory(self, registered_project):
        """디렉토리를 파일 저장 대상으로 주기 (400)"""
        response = client.post(
            "/api/files/content",
            json={
                "project_id": registered_project,
                "path": "src",  # 이미 존재하는 디렉토리
                "content": "content",
            },
        )
        assert response.status_code == 400
        assert "directory" in response.json()["detail"].lower()

    def test_save_with_invalid_project(self):
        """존재하지 않는 프로젝트로 저장 시도 (404)"""
        response = client.post(
            "/api/files/content",
            json={
                "project_id": "nonexistent-project",
                "path": "file.txt",
                "content": "content",
            },
        )
        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_path_parameter(self, registered_project):
        """빈 path 파라미터로 루트 조회"""
        response = client.get(
            f"/api/files/tree?project_id={registered_project}&path="
        )
        assert response.status_code == 200
        assert response.json()["path"] == ""

    def test_unicode_filename(self, registered_project, temp_project):
        """유니코드 파일명 지원"""
        # 유니코드 파일 생성
        unicode_file = Path(temp_project["path"]) / "한글파일.txt"
        unicode_file.write_text("한글 내용\n", encoding="utf-8")

        # 목록 조회
        response = client.get(
            f"/api/files/tree?project_id={registered_project}&path="
        )
        assert response.status_code == 200
        names = [item["name"] for item in response.json()["items"]]
        assert "한글파일.txt" in names

        # 파일 읽기
        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=한글파일.txt"
        )
        assert response.status_code == 200
        assert "한글 내용" in response.json()["content"]

    def test_large_file_read(self, registered_project, temp_project):
        """큰 파일 읽기"""
        large_content = "x" * 100000 + "\n"  # 100KB
        large_file = Path(temp_project["path"]) / "large.txt"
        large_file.write_text(large_content, encoding="utf-8")

        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=large.txt"
        )
        assert response.status_code == 200
        assert len(response.json()["content"]) > 100000


# 상태 코드 맵핑 검증 테스트
class TestStatusCodeMapping:
    """예외별 상태 코드 명확히 검증"""

    def test_project_not_found_returns_404(self):
        """ProjectNotFoundError -> 404"""
        response = client.get(
            "/api/files/tree?project_id=invalid-id&path="
        )
        assert response.status_code == 404

    def test_security_violation_returns_403(self, registered_project):
        """SecurityViolationError -> 403"""
        response = client.get(
            f"/api/files/tree?project_id={registered_project}&path=../../.."
        )
        assert response.status_code == 403

    def test_file_like_error_returns_400(self, registered_project):
        """FileLikeError -> 400"""
        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=nonexistent.txt"
        )
        assert response.status_code == 400

    def test_directory_save_returns_400(self, registered_project):
        """디렉토리 저장 시도 -> 400"""
        response = client.post(
            "/api/files/content",
            json={
                "project_id": registered_project,
                "path": "src",
                "content": "test",
            },
        )
        assert response.status_code == 400

    def test_utf8_decode_error_returns_400(self, registered_project, temp_project):
        """UTF-8 디코딩 실패 -> 400"""
        binary_file = Path(temp_project["path"]) / "bad.bin"
        binary_file.write_bytes(b"\xff\xfe")

        response = client.get(
            f"/api/files/content?project_id={registered_project}&path=bad.bin"
        )
        assert response.status_code == 400
