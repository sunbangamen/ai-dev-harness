import React, { useState } from 'react'
import { ConfirmDialog } from './ConfirmDialog'
import { InputDialog } from './InputDialog'
import type { ValidationResult } from './InputDialog'

interface FileActionsProps {
  selectedFile: string | null
  selectedType: 'file' | 'directory' | null
  currentPath: string
  loading: boolean
  onDelete: () => void
  onCreateDirectory: (path: string) => void
  onCreateFile: (path: string) => void
  onMove: (destPath: string) => void
}

// Validators
const validateDirectoryName = (name: string): ValidationResult => {
  if (!name.trim()) {
    return { valid: false, error: 'Directory name cannot be empty' }
  }

  // 경로 분리자 포함 금지 (폴더 생성은 단일 이름만)
  if (name.includes('/') || name.includes('\\')) {
    return { valid: false, error: 'Directory name cannot contain path separators (use single name only)' }
  }

  // 금지 문자 체크
  const forbidden = /[<>:"|?*\\]/g
  if (forbidden.test(name)) {
    return { valid: false, error: 'Directory name contains invalid characters' }
  }

  return { valid: true }
}

const validateFileName = (name: string): ValidationResult => {
  if (!name.trim()) {
    return { valid: false, error: 'File name cannot be empty' }
  }

  // 경로 분리자 및 금지 문자 체크
  const forbidden = /[/<>:"|?*\\]/g
  if (forbidden.test(name)) {
    return { valid: false, error: 'File name contains invalid characters' }
  }

  return { valid: true }
}

const validateMovePath = (destPath: string): ValidationResult => {
  if (!destPath.trim()) {
    return { valid: false, error: 'Destination path cannot be empty' }
  }

  // 절대 경로 확인
  if (!destPath.startsWith('/')) {
    return { valid: false, error: 'Destination path must be absolute (start with /)' }
  }

  // 프로젝트 루트 이탈 방지
  if (destPath.includes('/../')) {
    return { valid: false, error: 'Cannot move file outside project root' }
  }

  return { valid: true }
}

export function FileActions({
  selectedFile,
  selectedType,
  currentPath,
  loading,
  onDelete,
  onCreateDirectory,
  onCreateFile,
  onMove,
}: FileActionsProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showCreateFileDialog, setShowCreateFileDialog] = useState(false)
  const [showMoveDialog, setShowMoveDialog] = useState(false)

  const hasSelection = selectedFile !== null && selectedType !== null

  const handleDeleteClick = () => {
    setShowDeleteConfirm(true)
  }

  const handleDeleteConfirm = () => {
    setShowDeleteConfirm(false)
    onDelete()
  }

  const handleCreateDirectory = (path: string) => {
    setShowCreateDialog(false)
    onCreateDirectory(path)
  }

  const handleCreateFile = (fileName: string) => {
    setShowCreateFileDialog(false)
    // currentPath 기반으로 전체 경로 조합 (디렉토리 생성과 동일한 방식)
    let fullPath: string
    if (!currentPath || currentPath === '') {
      // 루트 디렉토리
      fullPath = `/${fileName}`
    } else if (currentPath === '/') {
      // 명시적 루트
      fullPath = `/${fileName}`
    } else {
      // 중첩 디렉토리 - currentPath가 이미 상대경로이므로 앞에 / 추가
      fullPath = `/${currentPath}/${fileName}`
    }
    console.log(`[DEBUG] Creating file: path="${currentPath}" + name="${fileName}" = "${fullPath}"`)
    onCreateFile(fullPath)
  }

  const handleMove = (destPath: string) => {
    setShowMoveDialog(false)
    onMove(destPath)
  }

  return (
    <>
      <div className="file-actions">
        <div className="actions-header">
          {/* 항상 보이는 생성 버튼 (현재 디렉토리) */}
          <div className="actions-buttons">
            <button
              onClick={() => setShowCreateDialog(true)}
              disabled={loading}
              className="btn-action btn-create"
              title="Create new directory"
            >
              New Dir
            </button>
            <button
              onClick={() => setShowCreateFileDialog(true)}
              disabled={loading}
              className="btn-action btn-create"
              title="Create new file"
            >
              New File
            </button>
          </div>
        </div>

        {/* 선택 기반 버튼 (파일/폴더 선택 시에만) */}
        {hasSelection && (
          <div className="actions-header">
            <span className="selection-info">
              {selectedType === 'directory' ? '📁' : '📄'} {selectedFile}
            </span>
            <div className="actions-buttons">
              <button
                onClick={() => setShowMoveDialog(true)}
                disabled={loading}
                className="btn-action btn-move"
                title="Move or rename"
              >
                Move
              </button>
              <button
                onClick={handleDeleteClick}
                disabled={loading}
                className="btn-action btn-delete"
                title="Delete file or folder"
              >
                {loading ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        )}
      </div>

      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="Confirm Delete"
        message={`Are you sure you want to delete "${selectedFile}"? This action cannot be undone.`}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setShowDeleteConfirm(false)}
        confirmText="Delete"
        cancelText="Cancel"
        isDangerous={true}
      />

      <InputDialog
        isOpen={showCreateDialog}
        title="Create Directory"
        label="Directory name:"
        placeholder="e.g., new_folder"
        validator={validateDirectoryName}
        onSubmit={handleCreateDirectory}
        onCancel={() => setShowCreateDialog(false)}
        submitText="Create"
      />

      <InputDialog
        isOpen={showCreateFileDialog}
        title="Create File"
        label="File name:"
        placeholder="e.g., newfile.txt"
        validator={validateFileName}
        onSubmit={handleCreateFile}
        onCancel={() => setShowCreateFileDialog(false)}
        submitText="Create"
      />

      <InputDialog
        isOpen={showMoveDialog}
        title="Move / Rename"
        label="New path:"
        placeholder={selectedFile ? selectedFile : ''}
        initialValue={selectedFile ? selectedFile : ''}
        validator={validateMovePath}
        onSubmit={handleMove}
        onCancel={() => setShowMoveDialog(false)}
        submitText="Move"
      />
    </>
  )
}
