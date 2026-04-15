import { useState, useEffect, useRef, useCallback } from 'react'
import { ProjectSelector } from './components/ProjectSelector'
import { FileList } from './components/FileList'
import { Editor } from './components/Editor'
import { FileActions } from './components/FileActions'
import { ConfirmDialog } from './components/ConfirmDialog'
import { ApiResponseInspector } from './components/ApiResponseInspector'
import { useFileAPI } from './hooks/useFileAPI'
import { useProjects } from './hooks/useProjects'
import { CacheStore } from './utils/cacheStore'
import type { FileItem } from './types'
import './App.css'

// Performance measurement helper - will be reset on each file selection
type PerformanceMeasurement = {
  selectedFile: string
  clickTime: number  // 클릭 시점을 기준점으로
  effectStartTime: number
  apiStartTime: number
  apiEndTime: number
}

let currentMeasurement: PerformanceMeasurement | null = null

function App() {
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [currentPath, setCurrentPath] = useState('')
  const [fileItems, setFileItems] = useState<FileItem[]>([])
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [selectedFileType, setSelectedFileType] = useState<'file' | 'directory' | null>(null)
  const [fileContent, setFileContent] = useState('')
  const [fileSize, setFileSize] = useState(0)

  // Dirty state (파일별 관리)
  const [dirtyFiles, setDirtyFiles] = useState<Set<string>>(new Set())

  // Unsaved changes dialog
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false)
  const [pendingFile, setPendingFile] = useState<string | null>(null)
  const [pendingProject, setPendingProject] = useState<string | null>(null)

  // Search
  const [searchQuery, setSearchQuery] = useState('')
  const [searchActive, setSearchActive] = useState(false)
  const [searchResults, setSearchResults] = useState<FileItem[]>([])

  // Search debounce + abort
  const abortControllerRef = useRef<AbortController | null>(null)
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // File content cache + request tracking
  const cacheStoreRef = useRef<CacheStore>(new CacheStore({ maxEntries: undefined }))
  const fileContentRequestIdRef = useRef(0)
  const fileContentAbortControllerRef = useRef<AbortController | null>(null)

  const {
    getFileTree,
    getFileContent,
    saveFileContent,
    deleteFile,
    createDirectory,
    createFile,
    moveFile,
    searchFiles,
    loadingTree,
    loadingContent,
    saving,
    error: fileError,
    requests,
  } = useFileAPI()

  const {
    projects,
    loading: projectsLoading,
    error: projectsError,
    fetchProjects,
    createProject,
    deleteProject,
    setFavorite,
    updateLastUsed,
  } = useProjects()

  // 현재 파일의 dirty 여부
  const isDirty = selectedFile ? dirtyFiles.has(selectedFile) : false

  // beforeunload 경고
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (dirtyFiles.size > 0) {
        e.preventDefault()
        e.returnValue = ''
        return ''
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [dirtyFiles])

  // Search debounce/abort cleanup (unmount 시)
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
        debounceTimerRef.current = null
      }

      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
        abortControllerRef.current = null
      }
    }
  }, [])

  // Fetch projects on mount
  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  // Update last used when project is selected
  useEffect(() => {
    if (selectedProjectId) {
      updateLastUsed(selectedProjectId)
    }
  }, [selectedProjectId, updateLastUsed])

  // Load file tree when project or path changes
  useEffect(() => {
    const loadFileTree = async () => {
      if (!selectedProjectId) return
      const result = await getFileTree(selectedProjectId, currentPath)
      if (result) {
        setFileItems(result.items)
      }
    }

    loadFileTree()
  }, [selectedProjectId, currentPath, getFileTree])

  // Load file content when file is selected (optimized: only for files)
  // Removed getFileContent from dependencies to prevent unnecessary re-executions
  useEffect(() => {
    const loadFileContent = async () => {
      // Only load content if a file is selected (not a directory)
      if (!selectedFile || !selectedProjectId || selectedFileType !== 'file') return

      const cacheStore = cacheStoreRef.current

      // 1️⃣ 캐시 확인: 캐시에 있으면 즉시 표시 (네트워크 요청 생략)
      const cachedContent = cacheStore.get(selectedProjectId, selectedFile)
      if (cachedContent !== null) {
        console.log(`%c[CACHE HIT] ${selectedFile}`, 'color: #4caf50; font-weight: bold;')
        setFileContent(cachedContent)
        setFileSize(cachedContent.length)

        // 성능 측정 (캐시에서)
        if (currentMeasurement && currentMeasurement.selectedFile === selectedFile) {
          currentMeasurement.apiEndTime = performance.now()
          const totalDuration = currentMeasurement.apiEndTime - currentMeasurement.clickTime
          console.log(`[PERF] Cache hit - total time: ${totalDuration.toFixed(2)}ms`)
        }
        return
      }

      // 2️⃣ 캐시 미스: API 요청 시작
      console.log(`%c[CACHE MISS] ${selectedFile}`, 'color: #ff9800; font-weight: bold;')

      // 이전 요청 취소
      if (fileContentAbortControllerRef.current) {
        fileContentAbortControllerRef.current.abort()
      }

      // 새 요청 ID 생성
      fileContentRequestIdRef.current += 1
      const currentRequestId = fileContentRequestIdRef.current
      const controller = new AbortController()
      fileContentAbortControllerRef.current = controller

      // 성능 측정: useEffect 실행 시점 기록 (클릭 기준점으로부터의 지연)
      if (currentMeasurement && currentMeasurement.selectedFile === selectedFile) {
        currentMeasurement.effectStartTime = performance.now()
        const delayFromClick = currentMeasurement.effectStartTime - currentMeasurement.clickTime
        console.log(`[PERF] useEffect triggered after: ${delayFromClick.toFixed(2)}ms from click`)
      }

      // 성능 측정: API 호출 시점
      if (currentMeasurement && currentMeasurement.selectedFile === selectedFile) {
        currentMeasurement.apiStartTime = performance.now()
        const effectTriggerDuration = currentMeasurement.apiStartTime - currentMeasurement.effectStartTime
        console.log(`[PERF] API call starting: ${effectTriggerDuration.toFixed(2)}ms after useEffect`)
      }

      const result = await getFileContent(selectedProjectId, selectedFile, controller.signal, currentRequestId)

      // 3️⃣ 응답 반영 직전: 이중 가드
      // Guard 1: requestId 확인 (stale response 방지)
      if (currentRequestId !== fileContentRequestIdRef.current) {
        console.warn(`[STALE] Ignoring response for old request: ${currentRequestId}`)
        return
      }

      // Guard 2: abort 확인 (AbortController 이중 방어)
      if (controller.signal.aborted) {
        console.warn(`[ABORTED] Request was aborted: ${currentRequestId}`)
        return
      }

      // 성능 측정: API 응답 시점
      if (currentMeasurement && currentMeasurement.selectedFile === selectedFile) {
        currentMeasurement.apiEndTime = performance.now()
        const apiResponseDuration = currentMeasurement.apiEndTime - currentMeasurement.apiStartTime
        const totalDuration = currentMeasurement.apiEndTime - currentMeasurement.clickTime

        if (result) {
          setFileContent(result.content)
          const contentSize = result.content.length
          setFileSize(contentSize)

          // 4️⃣ 캐시에 저장
          cacheStore.set(selectedProjectId, selectedFile, result.content)
          console.log(`%c[CACHE STORED] ${selectedFile}`, 'color: #2196f3; font-weight: bold;')

          console.log(`[PERF] API response time: ${apiResponseDuration.toFixed(2)}ms`)
          console.log(`[PERF] File size: ${contentSize} bytes`)
          console.log(`[PERF] Total time from click: ${totalDuration.toFixed(2)}ms`)

          // 세부 분석
          console.log(`%c[BREAKDOWN]`, 'color: #ff9800; font-weight: bold;')
          console.log(`  - Click to useEffect: ~2ms`)
          console.log(`  - useEffect to API start: ~0.2ms`)
          console.log(`  - API round-trip: ${apiResponseDuration.toFixed(2)}ms`)
          console.log(`    (includes server processing + network latency)`)
        } else {
          // ✅ 로딩 실패 시 fileContent 초기화 (stale content 방지)
          setFileContent('')
          console.log(`[PERF] API failed - total time: ${totalDuration.toFixed(2)}ms`)
        }
      } else {
        // Fallback if measurement tracking failed
        if (result) {
          setFileContent(result.content)
          const contentSize = result.content.length
          setFileSize(contentSize)

          // 캐시에 저장
          cacheStore.set(selectedProjectId, selectedFile, result.content)
        } else {
          setFileContent('')
        }
      }

      // 컨트롤러 정리
      fileContentAbortControllerRef.current = null
    }

    loadFileContent()
    // Intentionally omit getFileContent from dependency array to prevent re-creation loops
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFile, selectedProjectId, selectedFileType])

  // Dirty state 핸들러 (memoized)
  const handleEditorDirtyChange = useCallback(
    (filePath: string, isDirtyState: boolean) => {
      if (filePath !== selectedFile) {
        console.warn(
          `Dirty state mismatch: ${filePath} vs ${selectedFile}`
        )
        return
      }

      setDirtyFiles(prev => {
        const newSet = new Set(prev)
        if (isDirtyState) {
          newSet.add(filePath)
        } else {
          newSet.delete(filePath)
        }
        return newSet
      })
    },
    [selectedFile]
  )

  // 프로젝트 변경 (dirty 체크)
  const handleSelectProjectWithCheck = (projectId: string) => {
    if (isDirty) {
      setPendingProject(projectId)
      setShowUnsavedDialog(true)
      return
    }
    handleSelectProject(projectId)
  }

  const handleSelectProject = (projectId: string) => {
    // 진행 중인 파일 내용 로드 요청 취소
    if (fileContentAbortControllerRef.current) {
      fileContentAbortControllerRef.current.abort()
      fileContentAbortControllerRef.current = null
    }

    setSelectedProjectId(projectId)
    setCurrentPath('')
    setSelectedFile(null)
    setSelectedFileType(null)
    setFileContent('')
    setFileItems([])
    setSearchQuery('')
    setSearchActive(false)
    setSearchResults([])
    setDirtyFiles(new Set())  // dirty 상태 초기화

    // 💡 주의: 캐시는 유지 (다른 프로젝트 복귀 시 활용)
    // cacheStoreRef.current.clear() // ← 하지 않음
  }

  // 파일 선택 (dirty 체크)
  const handleSelectFileWithCheck = (path: string, type: 'file' | 'directory') => {
    console.log(`%c[DEBUG] handleSelectFileWithCheck called: path=${path}, type=${type}`, 'color: #ff00ff; font-weight: bold;')

    if (isDirty) {
      setPendingFile(path)
      setShowUnsavedDialog(true)
      return
    }

    // 성능 측정: 새로운 선택 시작 (클릭 시점을 기준점 0으로)
    if (type === 'file') {
      currentMeasurement = {
        selectedFile: path,
        clickTime: performance.now(),
        effectStartTime: 0,
        apiStartTime: 0,
        apiEndTime: 0,
      }
      console.clear()
      console.log(`%c[PERF] ===== File clicked: ${path} =====`, 'color: #00ff00; font-weight: bold; font-size: 14px;')
    }

    // 같은 파일을 다시 클릭한 경우: selectedFile을 null로 먼저 설정
    // 이렇게 하면 의존성이 변경되어 useEffect가 반드시 실행됨
    if (selectedFile === path && selectedFileType === type) {
      console.log(`%c[DEBUG] Same file re-selected, forcing useEffect`, 'color: #ff9800;')
      setSelectedFile(null)
      setSelectedFileType(null)
      setFileContent('')

      // 마이크로태스크 후에 다시 설정 (의존성 변경 후 useEffect 트리거)
      setTimeout(() => {
        setSelectedFile(path)
        setSelectedFileType(type)
      }, 0)
      return
    }

    setSelectedFile(path)
    setSelectedFileType(type)

    // 폴더면 즉시 content 비우기, 파일이면 로딩 표시 (빈 상태)
    if (type === 'directory') {
      setFileContent('')
    } else {
      setFileContent('') // 즉시 에디터 리셋 (로딩 중 표시)
    }
  }

  const handleSelectFile = (path: string, type: 'file' | 'directory') => {
    console.log(`%c[DEBUG] handleSelectFile called: path=${path}, type=${type}`, 'color: #ff00ff; font-weight: bold;')

    // 성능 측정: 새로운 선택 시작
    if (type === 'file') {
      currentMeasurement = {
        selectedFile: path,
        effectStartTime: 0,
        apiStartTime: 0,
        apiEndTime: 0,
      }
      console.clear()
      console.log(`%c[PERF] ===== File clicked: ${path} =====`, 'color: #00ff00; font-weight: bold; font-size: 14px;')
    }

    setSelectedFile(path)
    setSelectedFileType(type)

    // 폴더면 즉시 content 비우기, 파일이면 로딩 표시 (빈 상태)
    if (type === 'directory') {
      setFileContent('')
    } else {
      setFileContent('') // 즉시 에디터 리셋 (로딩 중 표시)
    }
  }

  const handleNavigateDirectory = (path: string) => {
    setCurrentPath(path)
    setSelectedFile(null)
    setSelectedFileType(null)
    setFileContent('')
    setSearchQuery('')
    setSearchActive(false)
    setSearchResults([])
  }

  // File content change handler (memoized)
  const handleFileContentChange = useCallback(
    (content: string) => {
      setFileContent(content)
    },
    []
  )

  // Save file handler (memoized)
  const handleSaveFile = useCallback(
    async (content: string): Promise<boolean> => {
      if (!selectedFile || !selectedProjectId) return false
      const result = await saveFileContent(selectedProjectId, selectedFile, content)

      // 저장 성공 시 캐시 갱신
      if (result?.success) {
        const cacheStore = cacheStoreRef.current
        cacheStore.set(selectedProjectId, selectedFile, content)
        console.log(`%c[CACHE UPDATED] ${selectedFile} (after save)`, 'color: #2196f3; font-weight: bold;')
      }

      return result?.success ?? false
    },
    [selectedFile, selectedProjectId, saveFileContent]
  )

  // 저장 후 파일/프로젝트 전환
  const handleSaveAndSwitch = async () => {
    if (!selectedFile) return

    const success = await handleSaveFile(fileContent)
    if (success) {
      setDirtyFiles(prev => {
        const newSet = new Set(prev)
        newSet.delete(selectedFile)
        return newSet
      })

      if (pendingFile) {
        setSelectedFile(pendingFile)
        setPendingFile(null)
      } else if (pendingProject) {
        handleSelectProject(pendingProject)
        setPendingProject(null)
      }
      setShowUnsavedDialog(false)
    }
  }

  // 저장 안 하고 전환
  const handleDiscardAndSwitch = () => {
    if (selectedFile) {
      setDirtyFiles(prev => {
        const newSet = new Set(prev)
        newSet.delete(selectedFile)
        return newSet
      })
    }

    if (pendingFile) {
      // Note: type will be loaded when we re-examine the file list
      setSelectedFile(pendingFile)
      // selectedFileType will be set based on file list when it updates
      setPendingFile(null)
    } else if (pendingProject) {
      handleSelectProject(pendingProject)
      setPendingProject(null)
    }
    setShowUnsavedDialog(false)
  }

  const handleDeleteFile = async () => {
    if (!selectedFile || !selectedProjectId) return
    const result = await deleteFile(selectedProjectId, selectedFile)
    if (result?.success) {
      // 삭제 성공 시 캐시 무효화
      const cacheStore = cacheStoreRef.current
      cacheStore.invalidate(selectedProjectId, selectedFile)
      console.log(`%c[CACHE INVALIDATED] ${selectedFile} (after delete)`, 'color: #ff5722; font-weight: bold;')

      setSelectedFile(null)
      setSelectedFileType(null)
      setFileContent('')
      const treeResult = await getFileTree(selectedProjectId, currentPath)
      if (treeResult) {
        setFileItems(treeResult.items)
      }
    }
  }

  const handleCreateDirectory = async (dirName: string) => {
    if (!selectedProjectId) return
    const newPath = currentPath ? `${currentPath}/${dirName}` : dirName
    const result = await createDirectory(selectedProjectId, newPath)
    if (result?.success) {
      // Refresh file list
      const treeResult = await getFileTree(selectedProjectId, currentPath)
      if (treeResult) {
        setFileItems(treeResult.items)
      }
    }
  }

  const handleCreateFile = async (filePath: string) => {
    if (!selectedProjectId) return

    // 1️⃣ API 호출: 파일 생성
    const result = await createFile(selectedProjectId, filePath, '')

    if (result?.success) {
      // 2️⃣ 캐시에 빈 내용으로 즉시 저장 (refetch 불필요)
      const cacheStore = cacheStoreRef.current
      cacheStore.set(selectedProjectId, filePath, '')
      console.log(`%c[CACHE STORED] ${filePath} (empty, no refetch)`, 'color: #2196f3; font-weight: bold;')

      // 3️⃣ 상태 리셋: fileContent 비우고, dirtyFiles는 유지
      setFileContent('')

      // 4️⃣ 파일 선택 (editor 즉시 오픈, auto-select)
      setSelectedFile(filePath)
      setSelectedFileType('file')

      // 5️⃣ 배경 갱신: file list (UI 업데이트 스킵)
      setTimeout(async () => {
        const treeResult = await getFileTree(selectedProjectId, currentPath)
        if (treeResult) {
          setFileItems(treeResult.items)
        }
      }, 0)
    }
  }

  const handleMoveFile = async (destPath: string) => {
    if (!selectedFile || !selectedProjectId) return
    const result = await moveFile(selectedProjectId, selectedFile, destPath)
    if (result?.success) {
      // 이름변경/이동 성공 시 구 경로 캐시 무효화
      const cacheStore = cacheStoreRef.current
      cacheStore.invalidate(selectedProjectId, selectedFile)
      console.log(`%c[CACHE INVALIDATED] ${selectedFile} (after move to ${destPath})`, 'color: #ff5722; font-weight: bold;')

      setSelectedFile(null)
      setSelectedFileType(null)
      setFileContent('')
      // Refresh file list
      const treeResult = await getFileTree(selectedProjectId, currentPath)
      if (treeResult) {
        setFileItems(treeResult.items)
      }
    }
  }

  // Search with debounce
  const handleSearch = useCallback(
    (query: string) => {
      setSearchQuery(query)

      // 기존 타이머 정리
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
        debounceTimerRef.current = null
      }

      // 기존 요청 취소
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
        abortControllerRef.current = null
      }

      if (!query.trim()) {
        setSearchActive(false)
        setSearchResults([])
        return
      }

      if (!selectedProjectId) return

      setSearchActive(true)

      // Debounce 타이머 (300ms)
      debounceTimerRef.current = setTimeout(async () => {
        const controller = new AbortController()
        abortControllerRef.current = controller

        const result = await searchFiles(
          selectedProjectId,
          query,
          controller.signal
        )

        // abort 후 null 정리
        if (controller.signal.aborted) {
          abortControllerRef.current = null
          return
        }

        if (result) {
          setSearchResults(result.results)
        }

        abortControllerRef.current = null
      }, 300)
    },
    [selectedProjectId, searchFiles]
  )

  const getSelectedItemType = (): 'file' | 'directory' | null => {
    // Use selectedFileType state instead of searching through items
    return selectedFileType
  }

  // ProjectSelector 호환 래퍼 함수
  const handleAddProject = async (projectId: string, path: string) => {
    const result = await createProject({ project_id: projectId, path })
    if (!result) {
      throw new Error('Failed to create project')
    }
  }

  const displayError = projectsError || fileError

  return (
    <div className="app">
      <header className="app-header">
        <h1>AI Dev Harness</h1>
        <ProjectSelector
          projects={projects}
          selectedProjectId={selectedProjectId}
          onSelectProject={handleSelectProjectWithCheck}
          onAddProject={handleAddProject}
          onDeleteProject={deleteProject}
          onToggleFavorite={setFavorite}
          loading={projectsLoading}
          error={projectsError}
        />
      </header>

      {displayError && <div className="error-banner">{displayError}</div>}

      <div className="app-container">
        <div className="sidebar">
          <h2>Files</h2>
          <FileList
            items={fileItems}
            currentPath={currentPath}
            selectedFile={selectedFile}
            onSelectFile={handleSelectFileWithCheck}
            onNavigateDirectory={handleNavigateDirectory}
            onSearch={handleSearch}
            loading={loadingTree}
            searchActive={searchActive}
            searchResults={searchResults}
          />
          <FileActions
            selectedFile={selectedFile}
            selectedType={getSelectedItemType()}
            currentPath={currentPath}
            loading={loadingTree}
            onDelete={handleDeleteFile}
            onCreateDirectory={handleCreateDirectory}
            onCreateFile={handleCreateFile}
            onMove={handleMoveFile}
          />
        </div>

        <div className="main-content">
          <Editor
            filePath={selectedFile}
            content={fileContent}
            onChange={handleFileContentChange}
            onDirtyChange={handleEditorDirtyChange}
            onSave={handleSaveFile}
            loading={loadingContent}
            saving={saving}
          />
        </div>
      </div>

      {/* Unsaved changes confirmation dialog */}
      <ConfirmDialog
        isOpen={showUnsavedDialog}
        title="Unsaved Changes"
        message={`You have unsaved changes. What would you like to do?`}
        onConfirm={handleSaveAndSwitch}
        onCancel={() => setShowUnsavedDialog(false)}
        onDiscard={handleDiscardAndSwitch}
        confirmText="Save"
        discardText="Don't Save"
        cancelText="Cancel"
      />

      <div className="inspector-panel">
        <ApiResponseInspector requests={requests} />
      </div>
    </div>
  )
}

export default App
