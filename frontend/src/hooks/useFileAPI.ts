import { useState, useCallback } from 'react'
import type {
  FileTreeResponse,
  FileContentResponse,
  FileSaveResponse,
  DeleteResponse,
  CreateDirectoryResponse,
  CreateFileResponse,
  MoveResponse,
  SearchResponse,
  ApiRequest
} from '../types'

const API_BASE = '/api/files'
const MAX_HISTORY = 5

// Response 파싱 (JSON 아닐 경우 text로 fallback)
const parseResponseBody = async (response: Response): Promise<any | null> => {
  try {
    const contentType = response.headers.get('content-type')

    // JSON 파싱 시도
    if (contentType && contentType.includes('application/json')) {
      const text = await response.text()
      if (!text) {
        console.warn('Empty response body')
        return null
      }
      return JSON.parse(text)
    }

    // Fallback: JSON이 아니면 text로 읽기
    const text = await response.text()
    if (!text) {
      console.warn(`Non-JSON response with no body. Content-Type: ${contentType}`)
      return null
    }

    console.warn(`Non-JSON response: ${text.substring(0, 200)}`)
    return { error: text }  // 에러 메시지 보존
  } catch (err) {
    console.error('Response parsing error:', err)
    return null
  }
}

// 에러 메시지 가공
const formatErrorMessage = (rawError: string | undefined): string => {
  if (!rawError) {
    return 'Unknown error occurred'
  }

  // HTML 에러 페이지 감지
  if (rawError.toLowerCase().includes('<!doctype') ||
      rawError.toLowerCase().includes('<html')) {
    return 'Server error: Invalid response from API'
  }

  // 매우 긴 텍스트 (500자 이상) → 요약
  if (rawError.length > 500) {
    return 'Server error: ' + rawError.substring(0, 100) + '...'
  }

  // JSON 파싱 에러
  if (rawError.includes('JSON') || rawError.includes('json')) {
    return 'Server error: Invalid response format'
  }

  // 네트워크 관련 에러
  if (rawError.includes('network') || rawError.includes('connection')) {
    return 'Network error: Please check your connection'
  }

  // 그 외
  return rawError
}

interface ApiState {
  requests: ApiRequest[]
}

export function useFileAPI() {
  const [loadingTree, setLoadingTree] = useState(false)
  const [loadingContent, setLoadingContent] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [apiState, setApiState] = useState<ApiState>({ requests: [] })

  const recordRequest = useCallback((request: ApiRequest) => {
    setApiState((prev) => ({
      requests: [{ ...request, timestamp: Date.now() }, ...prev.requests].slice(0, MAX_HISTORY),
    }))
  }, [])

  const getFileTree = useCallback(
    async (projectId: string, path: string = ''): Promise<FileTreeResponse | null> => {
      const startTime = Date.now()
      setLoadingTree(true)
      setError(null)

      const params = new URLSearchParams({
        project_id: projectId,
        path: path,
      })

      try {
        const url = `${API_BASE}/tree?${params.toString()}`

        const response = await fetch(url)
        const responseBody = await response.json()
        const duration = Date.now() - startTime

        const request: ApiRequest = {
          method: 'GET',
          endpoint: '/api/files/tree',
          params,
          status: response.status,
          responseBody,
          duration,
        }

        if (!response.ok) {
          const error = responseBody.detail || `HTTP ${response.status}`
          request.error = error
          recordRequest(request)
          setError(error)
          return null
        }

        recordRequest(request)
        return responseBody
      } catch (err) {
        const duration = Date.now() - startTime
        const message = err instanceof Error ? err.message : 'Unknown error'
        const request: ApiRequest = {
          method: 'GET',
          endpoint: '/api/files/tree',
          params,
          error: message,
          duration,
        }
        recordRequest(request)
        setError(message)
        return null
      } finally {
        setLoadingTree(false)
      }
    },
    [recordRequest]
  )

  const getFileContent = useCallback(
    async (
      projectId: string,
      path: string,
      signal?: AbortSignal,
      requestId?: number
    ): Promise<FileContentResponse | null> => {
      const startTime = Date.now()
      setLoadingContent(true)
      setError(null)

      const params = new URLSearchParams({
        project_id: projectId,
        path: path,
      })

      try {
        const url = `${API_BASE}/content?${params.toString()}`

        const response = await fetch(url, { signal })

        // Guard: abort되었는지 확인 (AbortController 이중 방어)
        if (signal?.aborted) {
          setLoadingContent(false)
          return null
        }

        const responseBody = await response.json()
        const duration = Date.now() - startTime

        const request: ApiRequest = {
          method: 'GET',
          endpoint: '/api/files/content',
          params,
          status: response.status,
          responseBody,
          duration,
        }

        if (!response.ok) {
          const error = responseBody.detail || `HTTP ${response.status}`
          request.error = error
          recordRequest(request)
          setError(error)
          return null
        }

        recordRequest(request)
        return responseBody
      } catch (err) {
        // AbortError는 의도적인 취소이므로 무시
        if (err instanceof Error && err.name === 'AbortError') {
          setLoadingContent(false)
          return null
        }

        const duration = Date.now() - startTime
        const message = err instanceof Error ? err.message : 'Unknown error'
        const request: ApiRequest = {
          method: 'GET',
          endpoint: '/api/files/content',
          params,
          error: message,
          duration,
        }
        recordRequest(request)
        setError(message)
        return null
      } finally {
        setLoadingContent(false)
      }
    },
    [recordRequest]
  )

  const saveFileContent = useCallback(
    async (projectId: string, path: string, content: string): Promise<FileSaveResponse | null> => {
      const startTime = Date.now()
      setSaving(true)
      setError(null)

      const body = {
        project_id: projectId,
        path,
        content,
      }

      try {
        const response = await fetch(`${API_BASE}/content`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(body),
        })

        const responseBody = await response.json()
        const duration = Date.now() - startTime

        const request: ApiRequest = {
          method: 'POST',
          endpoint: '/api/files/content',
          body,
          status: response.status,
          responseBody,
          duration,
        }

        if (!response.ok) {
          const error = responseBody.detail || `HTTP ${response.status}`
          request.error = error
          recordRequest(request)
          setError(error)
          return null
        }

        const data: FileSaveResponse = responseBody
        if (!data.success) {
          const error = 'Save failed on server'
          request.error = error
          recordRequest(request)
          setError(error)
          return null
        }

        recordRequest(request)
        return data
      } catch (err) {
        const duration = Date.now() - startTime
        const message = err instanceof Error ? err.message : 'Unknown error'
        const request: ApiRequest = {
          method: 'POST',
          endpoint: '/api/files/content',
          body,
          error: message,
          duration,
        }
        recordRequest(request)
        setError(message)
        return null
      } finally {
        setSaving(false)
      }
    },
    [recordRequest]
  )

  const deleteFile = useCallback(
    async (projectId: string, path: string): Promise<DeleteResponse | null> => {
      const startTime = Date.now()
      setLoadingTree(true)
      setError(null)

      const params = new URLSearchParams({
        project_id: projectId,
        path: path,
      })

      try {
        const url = `${API_BASE}?${params.toString()}`

        const response = await fetch(url, { method: 'DELETE' })
        const responseBody = await response.json()
        const duration = Date.now() - startTime

        const request: ApiRequest = {
          method: 'DELETE',
          endpoint: '/api/files',
          params,
          status: response.status,
          responseBody,
          duration,
        }

        if (!response.ok) {
          const error = responseBody.detail || `HTTP ${response.status}`
          request.error = error
          recordRequest(request)
          setError(error)
          return null
        }

        const data: DeleteResponse = responseBody
        if (!data.success) {
          const error = 'Delete failed on server'
          request.error = error
          recordRequest(request)
          setError(error)
          return null
        }

        recordRequest(request)
        return data
      } catch (err) {
        const duration = Date.now() - startTime
        const message = err instanceof Error ? err.message : 'Unknown error'
        const request: ApiRequest = {
          method: 'DELETE',
          endpoint: '/api/files',
          params,
          error: message,
          duration,
        }
        recordRequest(request)
        setError(message)
        return null
      } finally {
        setLoadingTree(false)
      }
    },
    [recordRequest]
  )

  const createDirectory = useCallback(
    async (projectId: string, path: string): Promise<CreateDirectoryResponse | null> => {
      const startTime = Date.now()
      setLoadingTree(true)
      setError(null)

      const body = {
        project_id: projectId,
        path,
      }

      try {
        const response = await fetch(`${API_BASE}/directory`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(body),
        })

        const responseBody = await response.json()
        const duration = Date.now() - startTime

        const request: ApiRequest = {
          method: 'POST',
          endpoint: '/api/files/directory',
          body,
          status: response.status,
          responseBody,
          duration,
        }

        if (!response.ok) {
          const error = responseBody.detail || `HTTP ${response.status}`
          request.error = error
          recordRequest(request)
          setError(error)
          return null
        }

        const data: CreateDirectoryResponse = responseBody
        if (!data.success) {
          const error = 'Create directory failed on server'
          request.error = error
          recordRequest(request)
          setError(error)
          return null
        }

        recordRequest(request)
        return data
      } catch (err) {
        const duration = Date.now() - startTime
        const message = err instanceof Error ? err.message : 'Unknown error'
        const request: ApiRequest = {
          method: 'POST',
          endpoint: '/api/files/directory',
          body,
          error: message,
          duration,
        }
        recordRequest(request)
        setError(message)
        return null
      } finally {
        setLoadingTree(false)
      }
    },
    [recordRequest]
  )

  const createFile = useCallback(
    async (projectId: string, path: string, content: string = ''): Promise<CreateFileResponse | null> => {
      const startTime = Date.now()
      setLoadingTree(true)
      setError(null)

      const body = {
        project_id: projectId,
        path,
        content,
      }

      try {
        const response = await fetch(`${API_BASE}/file`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(body),
        })

        const responseBody = await response.json()
        const duration = Date.now() - startTime

        const request: ApiRequest = {
          method: 'POST',
          endpoint: '/api/files/file',
          body,
          status: response.status,
          responseBody,
          duration,
        }

        if (!response.ok) {
          const error = responseBody.detail || `HTTP ${response.status}`
          request.error = error
          recordRequest(request)
          setError(error)
          return null
        }

        const data: CreateFileResponse = responseBody
        if (!data.success) {
          const error = 'Create file failed on server'
          request.error = error
          recordRequest(request)
          setError(error)
          return null
        }

        recordRequest(request)
        return data
      } catch (err) {
        const duration = Date.now() - startTime
        const message = err instanceof Error ? err.message : 'Unknown error'
        const request: ApiRequest = {
          method: 'POST',
          endpoint: '/api/files/file',
          body,
          error: message,
          duration,
        }
        recordRequest(request)
        setError(message)
        return null
      } finally {
        setLoadingTree(false)
      }
    },
    [recordRequest]
  )

  const moveFile = useCallback(
    async (projectId: string, srcPath: string, destPath: string): Promise<MoveResponse | null> => {
      const startTime = Date.now()
      setLoadingTree(true)
      setError(null)

      const body = {
        project_id: projectId,
        src_path: srcPath,
        dest_path: destPath,
      }

      try {
        const response = await fetch(`${API_BASE}/move`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(body),
        })

        const responseBody = await response.json()
        const duration = Date.now() - startTime

        const request: ApiRequest = {
          method: 'POST',
          endpoint: '/api/files/move',
          body,
          status: response.status,
          responseBody,
          duration,
        }

        if (!response.ok) {
          const error = responseBody.detail || `HTTP ${response.status}`
          request.error = error
          recordRequest(request)
          setError(error)
          return null
        }

        const data: MoveResponse = responseBody
        if (!data.success) {
          const error = 'Move failed on server'
          request.error = error
          recordRequest(request)
          setError(error)
          return null
        }

        recordRequest(request)
        return data
      } catch (err) {
        const duration = Date.now() - startTime
        const message = err instanceof Error ? err.message : 'Unknown error'
        const request: ApiRequest = {
          method: 'POST',
          endpoint: '/api/files/move',
          body,
          error: message,
          duration,
        }
        recordRequest(request)
        setError(message)
        return null
      } finally {
        setLoadingTree(false)
      }
    },
    [recordRequest]
  )

  const searchFiles = useCallback(
    async (
      projectId: string,
      query: string,
      signal?: AbortSignal
    ): Promise<SearchResponse | null> => {
      const startTime = Date.now()
      setLoadingTree(true)
      setError(null)

      const params = new URLSearchParams({
        project_id: projectId,
        query,
      })

      try {
        const url = `${API_BASE}/search?${params.toString()}`

        const response = await fetch(url, { signal })
        const responseBody = await parseResponseBody(response)
        const duration = Date.now() - startTime

        const request: ApiRequest = {
          method: 'GET',
          endpoint: '/api/files/search',
          params,
          status: response.status,
          responseBody,
          duration,
        }

        if (!response.ok) {
          const rawError =
            responseBody?.detail ||
            responseBody?.error ||
            `HTTP ${response.status}`
          const error = formatErrorMessage(rawError)
          request.error = error
          recordRequest(request)
          setError(error)
          return null
        }

        if (!responseBody) {
          setError('Invalid response format')
          return null
        }

        recordRequest(request)
        return responseBody
      } catch (err) {
        // AbortError는 의도적인 취소이므로 무시
        if (err instanceof Error && err.name === 'AbortError') {
          return null
        }

        const duration = Date.now() - startTime
        const message = err instanceof Error ? err.message : 'Unknown error'
        const formattedError = formatErrorMessage(message)
        const request: ApiRequest = {
          method: 'GET',
          endpoint: '/api/files/search',
          params,
          error: formattedError,
          duration,
        }
        recordRequest(request)
        setError(formattedError)
        return null
      } finally {
        setLoadingTree(false)
      }
    },
    [recordRequest]
  )

  return {
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
    error,
    requests: apiState.requests,
  }
}
