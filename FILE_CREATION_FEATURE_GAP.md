# 파일 생성 기능 미구현 - 이슈 정리

**발견일:** 2026-04-15 (캐시 전략 검증 중)
**영향도:** 높음 (파일 관리 UI의 핵심 기능)
**우선순위:** 높음

---

## 📌 **개요**

현재 AI Dev Harness는 **디렉토리는 생성/삭제 가능하지만, 파일 생성 기능이 없습니다.**

이로 인해:
- ❌ 사용자가 새 파일을 생성할 수 없음
- ❌ 캐시 검증 테스트 5 (delete → 재생성) 완전 실행 불가
- ❌ 파일 관리 워크플로우 불완전

---

## 🔍 **현재 상태**

### **구현되어 있는 것**
```
✅ 디렉토리 생성: createDirectory()
✅ 파일/디렉토리 삭제: deleteFile()
✅ 파일 이름변경/이동: moveFile()
✅ 파일 편집/저장: saveFileContent()
```

### **구현되지 않은 것**
```
❌ 파일 생성: createFile() 또는 유사 기능
❌ 파일 생성 UI: "New File" 버튼/다이얼로그
❌ 파일 생성 백엔드 API
```

---

## 🛠️ **필요한 구현**

### **1. 백엔드 API (FastAPI)**

**파일:** `backend/app/routes/files.py`

```python
@router.post("/file")
async def create_file(request: CreateFileRequest) -> CreateFileResponse:
    """
    새 파일 생성

    Request:
    {
      "project_id": "my-project",
      "path": "src/new_file.py",
      "content": ""  # 초기 내용 (선택)
    }

    Response:
    {
      "success": true,
      "message": "File created successfully",
      "path": "src/new_file.py"
    }
    """
```

**구현 요구사항:**
- 파일 경로 유효성 검증 (경로 위반 방지)
- 파일 이미 존재 여부 확인
- 부모 디렉토리 존재 여부 확인
- 파일 시스템에 실제 파일 생성

---

### **2. 프론트엔드 Hook (React)**

**파일:** `frontend/src/hooks/useFileAPI.ts`

```typescript
const createFile = useCallback(
  async (projectId: string, path: string, content: string = ''): Promise<CreateFileResponse | null> => {
    // 1. API 호출
    // 2. 성능 측정 기록
    // 3. 에러 처리
    return result
  },
  [recordRequest]
)
```

---

### **3. UI 컴포넌트**

**파일:** `frontend/src/components/FileActions.tsx`

```typescript
// "Create File" 버튼 추가
<button onClick={onCreateFile}>+ New File</button>

// 파일명 입력 다이얼로그 (기존 InputDialog 재사용)
<InputDialog
  title="Create New File"
  placeholder="file_name.py"
  onSubmit={handleCreateFile}
/>
```

---

### **4. App 통합**

**파일:** `frontend/src/App.tsx`

```typescript
const handleCreateFile = async (fileName: string) => {
  if (!selectedProjectId) return

  // 현재 경로에 새 파일 생성
  const newPath = currentPath ? `${currentPath}/${fileName}` : fileName
  const result = await createFile(selectedProjectId, newPath, '')

  if (result?.success) {
    // 파일 목록 갱신
    const treeResult = await getFileTree(selectedProjectId, currentPath)
    if (treeResult) setFileItems(treeResult.items)

    // 새 파일 자동 선택 (선택사항)
    setSelectedFile(newPath)
    setSelectedFileType('file')
  }
}
```

---

## 🧪 **테스트 영향**

### **현재 상황**
- 캐시 검증 테스트 5 (delete → 재생성 → 재fetch)의 **재생성 부분을 검증할 수 없음**
- 파일 생성 UI가 없어서 캐시 무효화 후 재fetch 검증 불가능
- Delete 시 캐시 무효화는 ✅ 로그 기준 정상 작동 확인
- 재생성 → 재fetch 부분은 ❌ 파일 생성 기능이 있을 때만 검증 가능

### **파일 생성 구현 후**
```
파일 A 생성
  ├─ [CACHE STORED] A (새로 생성 후 열기)
파일 A 삭제
  ├─ [CACHE INVALIDATED] A ✅ (이미 작동함)
파일 A 다시 생성
  ├─ [CACHE MISS] A (이전 캐시 제거됨 - 현재 delete 무효화로 로그 기준 정상)
  ├─ API 새로 요청
  └─ [CACHE STORED] A (새 내용으로 캐시 - 파일 생성 UI로만 검증 가능)
```

---

## 📝 **구현 체크리스트**

### **백엔드**
- [ ] `CreateFileRequest` / `CreateFileResponse` 스키마 추가
- [ ] `FileService.create_file()` 메서드 구현
- [ ] `/api/files/file` POST 엔드포인트 추가
- [ ] 테스트: 정상 생성, 중복 생성, 경로 검증

### **프론트엔드**
- [ ] `useFileAPI.createFile()` 훅 추가
- [ ] `FileActions` 컴포넌트에 "New File" 버튼 추가
- [ ] 파일명 입력 다이얼로그 통합
- [ ] App에서 `handleCreateFile()` 추가
- [ ] 파일 목록 갱신 로직 연결

### **테스트**
- [ ] 수동 테스트: 파일 생성 → 에디터에서 열기
- [ ] 캐시 테스트: 생성 → 수정 → 삭제 → 재생성 → 캐시 무효화 확인
- [ ] 에러 테스트: 중복 생성, 잘못된 경로 등

---

## 🎯 **우선순위 및 일정**

**우선순위:** 높음
- 파일 관리의 핵심 기능
- 캐시 전략의 완전한 검증을 위해 필수

**예상 작업량:** 중간 (2-3시간)
- 백엔드 API: 1시간
- 프론트엔드 UI: 1시간
- 테스트: 30분

---

## 📊 **의존성**

- 캐시 전략 구현 (완료) ✅
- FileActions 컴포넌트 (이미 존재) ✅
- InputDialog 컴포넌트 (이미 존재) ✅

---

## 💡 **추가 고려사항**

### **초기 내용**
- 파일 생성 시 빈 파일 또는 템플릿?
- 추천: 빈 파일로 시작 (사용자 선택)

### **파일명 유효성**
- 확장자 강제? (예: `.py`, `.js`)
- 추천: 확장자 선택 사항

### **자동 선택**
- 생성 후 즉시 에디터에서 열기?
- 추천: Yes (UX 개선)

### **디렉토리 구분**
- 같은 이름 파일/디렉토리 동시 존재?
- 추천: 그대로 허용 (파일시스템 정책)

---

## ✨ **결론**

파일 생성 기능은:
1. **캐시 전략 검증의 필수 요소**
2. **파일 관리 UI의 핵심 기능 누락**
3. **비교적 간단한 구현** (기존 패턴 활용)

**다음 우선순위로 구현 추천**
