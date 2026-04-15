# File Creation Feature - 검증 체크리스트

**목표:** 4가지 핵심 동작 검증 → production-ready 판정

**사전 준비:**
- DevTools 콘솔 열기 (F12)
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- 프로젝트 선택: "test1" (기존 프로젝트)

---

## ✅ Test 1: 생성 직후 이전 파일 내용 잔상 여부

**목표:** 새 파일 생성 시 이전 파일 내용이 보이지 않는지 확인

### 시나리오
1. **README.md 선택** (기존 파일 with content)
   - 에디터에 내용이 표시됨
   - 콘솔에 `[CACHE HIT]` 또는 파일 내용 로그

2. **"New File" 클릭**

3. **"/test_stale.txt" 입력** → Create

4. **즉시 확인 (1초 이내)**
   - ❌ **실패:** 에디터에 README.md 내용이 보임
   - ✅ **패스:** 에디터이 **완전히 비어있음** (아무것도 보이지 않음)
   - ⚠️ **경계:** 매우 잠깐 README 내용 보였다가 사라짐 (race condition)

### 콘솔 확인
```
[CACHE STORED] /test_stale.txt (empty, no refetch)
```

### 결과 기록
- [ ] 패스: 파일 내용 없음, 캐시 로그 있음
- [ ] 실패: _____ (실패 내용 기술)

---

## ✅ Test 2: 빠른 연속 생성/클릭 시 Race Condition

**목표:** 빠른 연속 작업 시 데이터 일관성 확인

### 시나리오 A: 빠른 연속 생성
1. **File A 선택**
2. **"New File" → "/race_test_1.txt" → Create** (1초 기다리지 않음)
3. **바로 다시 "New File" → "/race_test_2.txt" → Create**
4. **확인:**
   - ✅ **패스:** 두 파일 모두 창에 표시됨, 내용이 섞이지 않음
   - ❌ **실패:** 어느 한쪽 파일이 표시되지 않거나 내용이 섞임

### 콘솔 확인
```
[STALE] Ignoring response for old request: X
```
- 위 로그가 있으면 race condition 감지했다는 의미 (정상)

### 시나리오 B: 빠른 연속 클릭
1. **파일 A 선택 → 즉시 파일 B 선택 → 즉시 파일 C 선택**
2. **결과가 C 파일로 안정화될 때까지 기다림**
3. **확인:**
   - ✅ **패스:** 최종 표시는 파일 C의 내용만 보임
   - ❌ **실패:** 파일 A 또는 B의 내용이 섞여 보임

### 결과 기록
- [ ] 시나리오 A 패스
- [ ] 시나리오 B 패스
- [ ] [STALE] 로그 확인됨 (race condition 방어 working)

---

## ✅ Test 3: Delete → 재생성 → 재fetch (캐시 테스트 5)

**목표:** 캐시 무효화 및 재생성 시 신선한 데이터 로드 확인

### 단계 1: 파일 생성
1. **"New File" → "/cache_test_file.txt" → Create**
2. **콘솔 확인:**
   ```
   [CACHE STORED] /cache_test_file.txt (empty, no refetch)
   ```

### 단계 2: 파일 삭제
1. **파일이 여전히 선택된 상태**
2. **"Delete" 버튼 클릭**
3. **콘솔 확인:**
   ```
   [CACHE INVALIDATED] /cache_test_file.txt (after delete)
   ```
   - ✅ **패스:** 위 로그 보임
   - ❌ **실패:** 로그 없음

### 단계 3: 재생성
1. **"New File" → "/cache_test_file.txt" (같은 이름) → Create**
2. **콘솔 확인:**
   ```
   [CACHE STORED] /cache_test_file.txt (empty, no refetch)
   ```
   - 이전 로그와 다른 시점의 캐시 저장

### 단계 4: 재fetch 확인
1. **같은 파일 다시 클릭**
2. **콘솔 확인:**
   ```
   [CACHE HIT] /cache_test_file.txt
   ```
   - 내용은 **비어있어야 함** (이전 데이터가 아님)

3. **내용 입력 후 저장**
   ```
   [CACHE UPDATED] /cache_test_file.txt (after save)
   ```

### 결과 기록
- [ ] 단계 2: [CACHE INVALIDATED] 로그 확인
- [ ] 단계 3: [CACHE STORED] 로그 (재생성)
- [ ] 단계 4: [CACHE HIT] 로그, 내용 비어있음
- [ ] 전체 캐시 사이클 정상 작동

---

## ✅ Test 4: 기존 파일의 Dirty 상태 유지 여부

**목표:** 새 파일 생성 후 다른 파일의 dirty 상태가 유지되는지 확인

### 단계 1: 파일 수정 (dirty 생성)
1. **기존 파일 선택 (e.g., "README.md")**
2. **에디터에서 내용 수정** (마지막에 " - MODIFIED" 추가)
   - 버튼 변경: "Save" 나타나야 함
   - 제목에 asterisk (*) 나타나야 함
3. **저장하지 않음** (dirty 상태 유지)

### 단계 2: 다른 작업 수행 (새 파일 생성)
1. **"New File" → "/dirty_test.txt" → Create**
2. **에디터에 새 파일의 빈 내용이 보임**

### 단계 3: 이전 파일로 돌아가기
1. **파일 목록에서 "README.md" 다시 선택**
2. **unsaved changes 다이얼로그 나타남?**
   - ✅ **패스:** "You have unsaved changes" 다이얼로그 나타남
   - ❌ **실패:** 다이얼로그 없음 (dirty 상태 손실)

3. **"Cancel" 선택** (변경 취소)
4. **에디터에 여전히 수정된 내용 보임** (저장 전 상태)
5. **"Save" 버튼 클릭해서 저장**

### 단계 4: 다시 새 파일로
1. **새 파일 "/dirty_test.txt" 다시 선택**
2. **에디터는 빈 상태**
3. **README.md의 수정 내용이 보이지 않음** (올바른 파일 콘텐츠만)

### 결과 기록
- [ ] 단계 2: 새 파일 생성 후 이전 파일의 modified 표시 유지됨
- [ ] 단계 3: Unsaved changes 다이얼로그 나타남
- [ ] 단계 4: 다시 전환 후에도 각 파일의 올바른 내용 표시
- [ ] **dirtyFiles 상태 안전하게 유지됨** ✅

---

## 📋 최종 검증 결과

### Test 1: 이전 파일 잔상 여부
- [ ] **PASS** - 잔상 없음, 깨끗한 상태
- [ ] **FAIL** - 잔상 있음 → 원인: __________

### Test 2: Race Condition
- [ ] **PASS** - 빠른 연속 작업에도 안전
- [ ] **FAIL** - Race condition 발생 → 원인: __________

### Test 3: 캐시 사이클 (Delete → 재생성)
- [ ] **PASS** - 캐시 무효화 및 재생성 정상
- [ ] **FAIL** - 캐시 사이클 문제 → 원인: __________

### Test 4: Dirty 상태 유지
- [ ] **PASS** - 다른 파일의 dirty 상태 유지
- [ ] **FAIL** - Dirty 상태 손실 → 원인: __________

---

## ✅ 최종 판정

### 모두 PASS인 경우
```
🎉 Production-Ready 판정
- 구현 완료 ✅
- 동작 검증 완료 ✅
- 모든 엣지 케이스 안전 ✅
```

### 하나라도 FAIL인 경우
```
⚠️ 수정 필요
- 실패한 test 항목 기술
- 예상 원인 분석
- 수정 방향 제시
```

---

## 참고: 콘솔 로그 해석

| 로그 | 의미 | 정상 여부 |
|------|------|---------|
| `[CACHE STORED]` | 캐시에 저장됨 | ✅ |
| `[CACHE HIT]` | 캐시에서 로드됨 | ✅ |
| `[CACHE INVALIDATED]` | 캐시 무효화됨 | ✅ |
| `[CACHE UPDATED]` | 캐시 업데이트됨 | ✅ |
| `[STALE]` | 이전 요청 응답 무시됨 | ✅ (race condition 방어) |
| `[ABORTED]` | 요청 취소됨 | ✅ (race condition 방어) |

---

**지시사항:**
1. 위 4가지 test를 브라우저에서 수동으로 진행
2. 각 test의 결과 기록
3. 모두 PASS → 최종 완료 판정
4. FAIL → 구체적인 실패 내용 기술

**예상 소요 시간:** 15-20분
