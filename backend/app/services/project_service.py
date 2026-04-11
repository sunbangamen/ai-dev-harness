import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# data/config.json 경로
CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "data" / "config.json"


def load_config() -> Dict[str, Any]:
    """config.json 파일에서 프로젝트 목록을 읽습니다."""
    if not CONFIG_PATH.exists():
        return {"projects": []}

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: Dict[str, Any]) -> None:
    """프로젝트 목록을 config.json에 저장합니다."""
    # data 디렉토리가 없으면 생성
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_all_projects() -> List[Dict[str, Any]]:
    """저장된 모든 프로젝트 목록을 반환합니다."""
    config = load_config()
    return config.get("projects", [])


def add_project(name: str, path: str) -> Dict[str, Any]:
    """
    새로운 프로젝트를 추가합니다.
    - 경로가 존재하는지 확인
    - name과 path 중복 체크
    - ai 폴더 및 기본 파일 생성 (있으면 유지)
    - config.json에 저장
    """
    project_path = Path(path)

    # 경로가 존재하는지 확인
    if not project_path.exists():
        raise ValueError(f"Path does not exist: {path}")

    if not project_path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    # 설정 로드
    config = load_config()
    existing_projects = config.get("projects", [])

    # 프로젝트 중복 확인 (name과 path 둘 다 체크)
    for project in existing_projects:
        if project["name"] == name:
            raise ValueError(f"Project with name '{name}' already exists")
        if project["path"] == path:
            raise ValueError(f"Project with path '{path}' already registered")

    # ai 폴더 구조 초기화
    _initialize_ai_folder(project_path)

    # 새 프로젝트 추가 (UUID 생성)
    project_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    new_project = {
        "id": project_id,
        "name": name,
        "path": path,
        "created_at": created_at
    }
    existing_projects.append(new_project)
    config["projects"] = existing_projects

    # 저장
    save_config(config)

    return {"id": project_id, "name": name, "path": path, "created_at": created_at}


def _initialize_ai_folder(project_path: Path) -> None:
    """
    ai 폴더 및 기본 파일을 생성합니다.
    파일이 이미 존재하면 생성하지 않습니다.
    """
    ai_folder = project_path / "ai"
    ai_folder.mkdir(parents=True, exist_ok=True)

    # 생성할 파일들의 기본 내용
    files_to_create = {
        "README.md": """# AI Project Folder

이 폴더는 프로젝트의 AI 관련 산출물과 상태를 관리합니다.

## 폴더 구조

- `PROJECT_BRIEF.md` - 프로젝트 요약
- `ARCHITECTURE.md` - 아키텍처 설명
- `TASKS.md` - 작업 목록
- `REVIEW.md` - 리뷰 노트
- `CHANGE_REQUEST.md` - 변경 요청
- `STATE.json` - 프로젝트 상태
- `logs/` - 실행 로그
""",
        "PROJECT_BRIEF.md": """# Project Brief

## 개요
프로젝트에 대한 간단한 설명을 작성하세요.

## 목표
- 목표 1
- 목표 2

## 범위
프로젝트의 범위를 정의하세요.
""",
        "ARCHITECTURE.md": """# Architecture

## 시스템 구조

전체 시스템의 아키텍처를 설명하세요.

## 주요 컴포넌트

- Component 1
- Component 2

## 데이터 흐름

데이터 흐름 다이어그램과 설명을 추가하세요.
""",
        "TASKS.md": """# Tasks

## 진행 중
- [ ] Task 1
- [ ] Task 2

## 완료됨
- [x] Task 0

## 계획
- [ ] Future Task 1
- [ ] Future Task 2
""",
        "REVIEW.md": """# Review Notes

## 최근 리뷰
작성 날짜:

### 피드백
- 피드백 1
- 피드백 2

### 개선사항
- 개선사항 1
""",
        "CHANGE_REQUEST.md": """# Change Requests

## 미처리 요청
- [ ] Request 1
- [ ] Request 2

## 처리된 요청
- [x] Request 0
""",
    }

    # 텍스트 파일 생성 (있으면 유지)
    for filename, content in files_to_create.items():
        file_path = ai_folder / filename
        if not file_path.exists():
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

    # STATE.json 생성 (있으면 유지)
    state_file = ai_folder / "STATE.json"
    if not state_file.exists():
        state_data = {
            "phase": "planning",
            "last_updated": datetime.now().isoformat(),
            "summary": "프로젝트 초기화 상태",
            "completed_tasks": [],
            "in_progress": [],
            "blockers": []
        }
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)

    # logs 디렉토리 및 prompts.jsonl 생성
    logs_dir = ai_folder / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    prompts_file = logs_dir / "prompts.jsonl"
    if not prompts_file.exists():
        # 빈 JSONL 파일 생성
        with open(prompts_file, "w", encoding="utf-8") as f:
            pass  # 완전 빈 파일
