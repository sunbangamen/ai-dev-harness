# 파일 생성 기능 구현 계획

**작성일:** 2026-04-15
**범위:** 파일 생성 기능 + 캐시 통합

---

## 📋 **구현 기준 (결정 완료)**

### **1️⃣ UX: 파일 생성 후 자동 선택 + 에디터 오픈**

**동작 흐름:**
```
사용자가 "New File" 클릭
  ↓
파일명 입력 다이얼로그
  ↓
생성 API 호출 (backend)
  ↓
✅ 생성 성공
  ├─ 파일 목록 갱신 (getFileTree)
  ├─ 새 파일 자동 선택 (setSelectedFile)
  ├─ 파일 타입 자동 설정: 'file'
  └─ 에디터 자동 오픈 (성능 측정 시작)
     ↓
[CACHE STORED] (빈 content로 즉시 캐시)
  ↓
에디터에 빈 파일 표시 (준비 완료)
```

**목표:**
- 사용자는 "생성 후 즉시 편집 가능" UX 경험
- 추가 클릭 없음

---

### **2️⃣ 캐시: 생성 직후 빈 content로 즉시 캐시 (추가 fetch 없음)**

**원리:**
- 파일 생성 = 기본적으로 새로운 빈 파일
- 백엔드가 기본 템플릿을 넣는 구조 아님
- 생성 직후 캐시 저장 후 에디터 즉시 오픈 가능

**구현:**
```typescript
const handleCreateFile = async (fileName: string) => {
  if (!selectedProjectId) return

  // 1. 새 파일 경로 구성
  const newPath = currentPath ? `${currentPath}/${fileName}` : fileName

  // 2. 생성 API 호출
  const result = await createFile(selectedProjectId, newPath, '')

  if (result?.success) {
    // 3. 파일 목록 갱신
    const treeResult = await getFileTree(selectedProjectId, currentPath)
    if (treeResult) {
      setFileItems(treeResult.items)
    }

    // 4. ⭐ 캐시에 빈 content 즉시 저장 (추가 fetch 불필요)
    const cacheStore = cacheStoreRef.current
    cacheStore.set(selectedProjectId, newPath, '')
    console.log(`%c[CACHE STORED] ${newPath} (empty file)`, 'color: #2196f3; font-weight: bold;')

    // 5. ⭐ 상태 정리: 이전 파일 내용이 남지 않게 함
    setFileContent('')           // 에디터 초기화 (빈 파일)
    setDirtyFiles(new Set())     // dirty 상태 초기화

    // 6. 새 파일 자동 선택 + 에디터 오픈 (즉시, 추가 파일 내용 fetch 없음)
    setSelectedFile(newPath)
    setSelectedFileType('file')
    // setSelectedFile 변경 시 useEffect는 실행되지만,
    // 캐시에 이미 존재하므로 [CACHE HIT]으로 즉시 표시

    // 7. 다이얼로그 닫기
    setShowCreateFileDialog(false)

    console.log(`%c[FILE CREATE] ${newPath}`, 'color: #4caf50; font-weight: bold;')
  }
}
```

**캐시 처리:**
- ✅ 생성 직후: **빈 content로 즉시 cacheStore.set(projectId, path, '')**
- ✅ 추가 파일 내용 fetch 없음 (새 파일 = 기본 빈 파일)
- ✅ 에디터 즉시 오픈 (빈 파일 준비됨)
- ✅ 최적 UX: 생성 후 바로 편집 가능

---

## ⭐ **생성 직후 상태 정리 (중요)**

파일 생성 완료 직후, 이전 파일의 내용이 에디터에 남지 않도록 명시적으로 상태를 정리합니다:

```typescript
// 1. 에디터 초기화 (빈 파일 상태)
setFileContent('')

// 2. Dirty 상태: setDirtyFiles(new Set()) 하지 않기! (위험)
// 이유:
// - dirtyFiles는 여러 파일의 수정 상태를 관리하는 Set
// - new Set()으로 비우면 다른 파일의 dirty 상태도 날아감
// - 새 파일은 방금 생성됐으므로 이미 dirty 상태가 없음
// - 따라서 명시적 정리가 불필요함

// 3. 새 파일 자동 선택
setSelectedFile(newPath)
setSelectedFileType('file')

// 4. 파일 목록 갱신 (백그라운드)
// setTimeout(async () => getFileTree(...)) 사용
// → 에디터를 먼저 열고, 목록을 나중에 갱신 (UX 최적)
```

**효과:**
- ✅ 이전 파일 내용이 에디터에 표시되지 않음
- ✅ 기존 파일들의 dirty 상태 안전하게 유지
- ✅ 새 파일 준비 완료 상태
- ✅ 에디터 먼저 오픈, 목록은 백그라운드 갱신

**타이밍:**
- 캐시 저장 직후 실행
- useEffect가 캐시 히트로 빈 파일 표시
- 파일 목록 갱신은 그 이후 (setTimeout 0)

---

## 🔄 **캐시와의 상호작용**

### **시나리오: 파일 A 생성 → 편집 → 저장 → 재클릭**

```
1️⃣ 파일 A 생성 (완료)
   ├─ createFile API 호출
   ├─ [CACHE STORED] A (empty file) ← 즉시 캐시!
   ├─ 파일 목록 갱신
   └─ 에디터 자동 오픈 (빈 파일 준비됨)

2️⃣ 에디터에서 편집
   └─ 메모리만 수정 (dirty state)

3️⃣ Ctrl+S 저장
   ├─ saveFileContent API
   └─ [CACHE UPDATED] A (새로운 content)

4️⃣ 파일 B로 이동
   └─ [정상 작동]

5️⃣ 파일 A 다시 클릭
   ├─ [CACHE HIT] A
   └─ 저장된 최신 content 즉시 표시 (2ms)
```

**특징:**
- 생성 직후 추가 API 호출 없음 (빈 파일이므로)
- 에디터 즉시 오픈 가능
- 저장 후 캐시 자동 갱신
- 재클릭 시 캐시 히트로 빠름

---

## 💻 **구현 단계**

### **Phase 1: 백엔드 API**

**파일:** `backend/app/routes/files.py`

**엔드포인트:** `POST /api/files/file`
(기존 패턴 일관성: `/directory`, `/move`, `/content`와 동일)

```python
@router.post("/file")
async def create_file(request: CreateFileRequest) -> CreateFileResponse:
    """
    새 파일 생성

    Request:
    {
      "project_id": "my-project",
      "path": "src/new_file.py",
      "content": ""  # 초기 내용 (기본값: 빈 파일)
    }

    Response:
    {
      "success": true,
      "message": "File created successfully",
      "path": "src/new_file.py"
    }
    """
    # 1. 경로 유효성 검증 (보안)
    # 2. 파일 존재 여부 확인 (중복 방지)
    # 3. 부모 디렉토리 존재 확인
    # 4. 파일 시스템에 생성
    # 5. 응답 반환
```

**체크리스트:**
- [ ] CreateFileRequest 스키마 정의
- [ ] FileService.create_file() 메서드 구현
- [ ] /api/files/file POST 엔드포인트 추가
- [ ] 경로 위반 방지 (../../ 등)
- [ ] 중복 생성 방지
- [ ] 에러 처리 (권한, 디스크 부족 등)

---

### **Phase 2: 프론트엔드 훅**

**파일:** `frontend/src/hooks/useFileAPI.ts`

```typescript
const createFile = useCallback(
  async (
    projectId: string,
    path: string,
    content: string = ''
  ): Promise<CreateFileResponse | null> => {
    // 성능 측정
    const startTime = Date.now()

    // API 호출
    const response = await fetch(`${API_BASE}/file`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, path, content })
    })

    // 응답 처리
    const responseBody = await response.json()
    const duration = Date.now() - startTime

    // 요청 기록
    const request: ApiRequest = {
      method: 'POST',
      endpoint: '/api/files/file',
      body: { project_id: projectId, path, content },
      status: response.status,
      responseBody,
      duration
    }

    if (response.ok && responseBody.success) {
      recordRequest(request)
      return responseBody
    }

    // 에러 처리
    const error = responseBody.detail || `HTTP ${response.status}`
    request.error = error
    recordRequest(request)
    setError(error)
    return null
  },
  [recordRequest]
)
```

**체크리스트:**
- [ ] createFile 훅 추가
- [ ] 성능 측정 포함
- [ ] 요청 기록 (ApiResponseInspector용)
- [ ] 에러 처리

---

### **Phase 3: 프론트엔드 UI**

**파일:** `frontend/src/components/FileActions.tsx`

```typescript
// "New File" 버튼 추가
<button
  onClick={() => setShowCreateFileDialog(true)}
  disabled={!selectedProjectId || selectedFileType === 'directory'}
>
  + New File
</button>

// 파일명 입력 다이얼로그 (InputDialog 재사용)
<InputDialog
  isOpen={showCreateFileDialog}
  title="Create New File"
  placeholder="file_name.py"
  onSubmit={handleCreateFile}
  onCancel={() => setShowCreateFileDialog(false)}
/>
```

**체크리스트:**
- [ ] "New File" 버튼 추가
- [ ] InputDialog 통합
- [ ] 파일명 유효성 검증 (클라이언트)
- [ ] 상태 관리 (showCreateFileDialog)

---

### **Phase 4: App 통합**

**파일:** `frontend/src/App.tsx`

```typescript
const handleCreateFile = async (fileName: string) => {
  if (!selectedProjectId) return

  // 1. 현재 경로에 새 파일 경로 구성
  const newPath = currentPath ? `${currentPath}/${fileName}` : fileName

  // 2. 파일 생성 API 호출
  const result = await createFile(selectedProjectId, newPath, '')

  if (result?.success) {
    // 3. ⭐ 캐시에 빈 content 즉시 저장
    const cacheStore = cacheStoreRef.current
    cacheStore.set(selectedProjectId, newPath, '')
    console.log(`%c[CACHE STORED] ${newPath} (empty file)`, 'color: #2196f3; font-weight: bold;')

    // 4. ⭐ 에디터 상태 준비: 이전 파일 내용이 남지 않게 함
    setFileContent('')           // 에디터 초기화 (빈 파일)
    // 주의: setDirtyFiles(new Set()) 하지 않음!
    // → 다른 파일들의 dirty 상태를 유지해야 함
    // → 새 파일은 방금 생성됐으므로 이미 dirty 상태가 없음

    // 5. 새 파일 자동 선택 + 에디터 오픈 (추가 파일 내용 fetch 없음)
    // → useEffect 실행되지만 캐시 HIT로 즉시 표시
    setSelectedFile(newPath)
    setSelectedFileType('file')

    // 6. 다이얼로그 닫기
    setShowCreateFileDialog(false)

    console.log(`%c[FILE CREATE] ${newPath}`, 'color: #4caf50; font-weight: bold;')

    // 7. 파일 목록 갱신 (백그라운드, 에디터 오픈 후)
    // → UX: 에디터를 먼저 열고 목록을 갱신
    setTimeout(async () => {
      const treeResult = await getFileTree(selectedProjectId, currentPath)
      if (treeResult) {
        setFileItems(treeResult.items)
      }
    }, 0)
  }
}
```

**체크리스트:**
- [ ] handleCreateFile 구현
- [ ] 파일 목록 갱신 연동
- [ ] 캐시에 빈 content 즉시 저장 (cacheStore.set)
- [ ] 상태 정리 (fileContent, dirtyFiles 초기화)
- [ ] 자동 선택 + 에디터 오픈
- [ ] 로그 출력

---

## 📊 **테스트 체크리스트**

### **단위 테스트**

- [ ] API: 정상 생성, 중복 생성, 경로 검증
- [ ] UI: 버튼 활성화/비활성화, 다이얼로그 동작
- [ ] 캐시: 생성 후 캐시 미스 → API → 캐시 저장

### **통합 테스트**

- [ ] 파일 생성 → 에디터 자동 오픈
- [ ] 생성 후 편집 → 저장 → [CACHE UPDATED]
- [ ] 생성 후 다른 파일로 이동 → 다시 복귀 → [CACHE HIT]

### **UX 검증 (구현 후 수동 확인 필요)**

- [ ] **이전 파일 잔상 확인**
  - 다른 파일 열어둔 상태 → 새 파일 생성
  - 이전 파일의 텍스트가 에디터에 남아있지 않은지 확인
  - `setFileContent('')` 직후 `setSelectedFile()` 전환이 명확한지 확인

- [ ] **빈 깜빡임 UX 확인**
  - 새 파일 생성 후 에디터가 너무 어색한 빈 상태로 깜빡이지 않는지 확인
  - 빠른 연속 생성 시 부자연스러운 상태 전환이 없는지 확인
  - 에디터 로딩 과정이 자연스러운지 확인

### **캐시 테스트 5 재검증**

```
1️⃣ 파일 A 생성
   └─ [CACHE STORED] A (empty file)

2️⃣ 파일 A 삭제
   └─ [CACHE INVALIDATED] A ✅

3️⃣ 파일 A 다시 생성
   └─ [CACHE STORED] A (empty file)
      (이전 캐시는 이미 무효화되었으므로 OK)

결과: 캐시 무효화 → 재생성 → 재캐시 정상 작동 ✅
```

---

## 🎯 **완성 기준**

| 항목 | 기준 | 확인 |
|------|------|------|
| **UX** | 생성 후 즉시 에디터 오픈 | ✅ 구현 |
| **캐시** | 빈 content로 즉시 캐시 | ✅ 로그 확인 |
| **테스트 5** | 5/5 완료 | ✅ 재검증 |
| **성능** | 파일 목록 갱신 빠름 | ✅ 로그 기준 |

---

## 📝 **예상 시간**

| 단계 | 예상 시간 | 비고 |
|------|---------|------|
| **Phase 1 (백엔드)** | 1시간 | 경로 검증 포함 |
| **Phase 2 (훅)** | 30분 | 기존 패턴 재사용 |
| **Phase 3 (UI)** | 30분 | InputDialog 재사용 |
| **Phase 4 (통합)** | 30분 | handleCreateFile |
| **테스트** | 1시간 | 단위 + 통합 + 캐시 |
| **총 소요** | **3-3.5시간** | |

---

## ✨ **완성 후 상태**

### **파일 관리 기능 완성**

```
✅ 디렉토리 생성/삭제
✅ 파일 생성 (새로 추가!)
✅ 파일 편집/저장
✅ 파일 삭제
✅ 파일 이름변경/이동
```

### **캐시 전략 완전 검증**

```
✅ 테스트 1-4: 이미 완료
✅ 테스트 5: 파일 생성으로 완전 검증
→ 5/5 완료 = 캐시 전략 완전 마무리
```

---

## 📌 **구현 중 주의점**

1. **캐시 무효화 로직 활용**
   - 삭제 후 같은 이름으로 재생성 시 이전 캐시 제거됨
   - 정상 동작 (캐시 설계가 이미 처리함)

2. **파일명 유효성**
   - 클라이언트: 기본 검증 (빈 문자열, 경로 분리자 등)
   - 서버: 엄격한 검증 (보안)

3. **콘솔 로그**
   - `[FILE CREATE]` 로그 추가 (디버깅)
   - 캐시 로그와 구분 가능하게

4. **성능 측정**
   - 파일 생성 → 목록 갱신 → 에디터 오픈까지 시간 측정
   - `[PERF]` 로그로 기록

---

## **🎯 구현 준비 최종 상태**

| 항목 | 상태 | 비고 |
|------|------|------|
| **캐시 전략** | ✅ 설계 완료 | 빈 content 즉시 저장 |
| **상태 정리** | ✅ 설계 완료 | fileContent='', dirty 안전 |
| **UX 순서** | ✅ 설계 완료 | 에디터 우선, 목록 백그라운드 |
| **API 경로** | ✅ 확인 완료 | POST /api/files/file (일관성) |
| **UX 검증** | ⏳ 구현 후 확인 | 이전 잔상, 깜빡임 확인 필요 |

---

**이제 설계와 준비가 완료되었습니다. 실제 구현 단계로 넘어가면 됩니다!** 🚀
