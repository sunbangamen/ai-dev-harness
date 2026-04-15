# File Creation Feature - Manual Testing Guide

**Implementation Status:** ✅ Complete (Phase 1-4)
**Date:** 2026-04-15

---

## Test Environment Setup

1. **Frontend:** http://localhost:5173 (Vite dev server running ✅)
2. **Backend:** http://localhost:8000 (Uvicorn running ✅)
3. **Browser:** Open DevTools Console (F12) to monitor cache logs

---

## Test Plan

### ✅ Test 1: "New File" Button Visibility
**Goal:** Verify button appears only when a file or directory is selected

1. Open app → Select a project (e.g., "test1")
2. Verify: No "New File" button appears (only "No selection" shown)
3. Click any file/folder in the tree
4. ✅ **Expected:** "New File" button appears alongside "New Dir", "Move", "Delete"

---

### ✅ Test 2: File Creation Dialog & Validation
**Goal:** Verify dialog accepts/rejects paths correctly

1. With a file selected, click "New File"
2. ✅ Dialog title: "Create File"
3. Label: "File path:"
4. Placeholder: "e.g., /filename.txt"

**Test 2a: Invalid - Empty path**
- Submit empty → ✅ Error: "File path cannot be empty"

**Test 2b: Invalid - Path with forbidden characters**
- Enter: `/file<name>.txt` → ✅ Error: "File path contains invalid characters"
- Enter: `/file|name.txt` → ✅ Error: "File path contains invalid characters"

**Test 2c: Invalid - No directory component**
- Enter: `filename.txt` (no `/` prefix) → ✅ Error: "File path must include at least directory"

**Test 2d: Invalid - Path traversal attempt**
- Enter: `/test/../../../etc/passwd` → ✅ Error: "Cannot create file outside project root"

**Test 2e: Valid - Simple filename**
- Enter: `/test.txt` → ✅ Should succeed (boundary case)

**Test 2f: Valid - Nested path**
- Enter: `/src/components/new.tsx` → ✅ Should succeed

---

### ✅ Test 3: File Creation API Call
**Goal:** Verify API creates file on server

1. In DevTools Console, look for logs
2. Enter `/test_new_file.txt` and submit
3. ✅ **Expected logs:**
   - `[CACHE STORED] /test_new_file.txt (empty, no refetch)` (blue text)
   - API request in Network tab: `POST /api/files/file` → 200 OK

---

### ✅ Test 4: Editor Opens Immediately (Auto-Select)
**Goal:** Verify file opens in editor without delay, no stale content

**Prerequisites:** Select a file first (e.g., `README.md`), read its content

1. Note the content in the editor (e.g., "This is README...")
2. Click "New File" → Enter `/test_immediate.txt` → Submit
3. ✅ **Expected:**
   - Editor shows **empty content** (not README)
   - No flickering of previous file content
   - No stale content visible
   - File size: 0 bytes

---

### ✅ Test 5: Cache Strategy with New File
**Goal:** Verify cache stores empty content, no refetch happens

1. Create file `/test_cache.txt` as in Test 3
2. In Console, verify: `[CACHE STORED] /test_cache.txt (empty, no refetch)` (blue)
3. Navigate to another file
4. Click back on `/test_cache.txt`
5. ✅ **Expected:**
   - Console shows: `[CACHE HIT] /test_cache.txt` (green)
   - No API request made
   - Content is empty
   - Load time < 5ms

---

### ✅ Test 6: File List Updates (Background Refresh)
**Goal:** Verify new file appears in the file list without blocking UI

1. Create file `/test_listupdate.txt`
2. ✅ **Expected behavior:**
   - Editor opens immediately (no wait)
   - 1-2 seconds later, file list refreshes
   - New file appears in tree with 📄 icon
   - No UI lag or blocking

---

### ✅ Test 7: Create Multiple Files in Sequence
**Goal:** Verify rapid file creation works correctly

1. Create `/test1.txt` → Verify in editor
2. Immediately (while editor is open) click "New File" again
3. Create `/test2.txt` → Verify different content
4. ✅ **Expected:**
   - Both files created successfully
   - Each file has empty content
   - Cache entries separate: `/test1.txt` and `/test2.txt`
   - No cache collision

---

### ✅ Test 8: Create File in Different Directory
**Goal:** Verify paths with multiple directory levels work

**Setup:** Navigate to `/src/components` directory (or create it)

1. With a file in `/src/components/` selected
2. Click "New File"
3. Enter `/src/components/NewComponent.tsx`
4. ✅ **Expected:**
   - File created at correct path
   - Editor shows empty content
   - File list shows in current directory

---

### ✅ Test 9: Cache + Delete + Recreate Integration
**Goal:** Verify cache invalidation on delete, fresh cache on recreate

1. Create file `/test_recreate.txt` → Verify in editor
2. Delete the file (click Delete button)
3. ✅ Console shows: `[CACHE INVALIDATED] /test_recreate.txt (after delete)` (orange)
4. Create same file again: `/test_recreate.txt`
5. ✅ **Expected:**
   - New file has empty content (not old content)
   - Cache store shows fresh entry
   - No stale content visible

---

### ✅ Test 10: UX Smoothness Check
**Goal:** Verify overall user experience feels natural

**Checklist:**
- [ ] No loading spinner appears (file is empty, instant)
- [ ] Editor text is **never** overwritten with wrong content
- [ ] No flickering between old file and new file
- [ ] Button click feedback is immediate
- [ ] Dialog is dismissible (Cancel button works)
- [ ] Console logs are clear and helpful for debugging

---

## Console Log Reference

Look for these logs during testing:

```
✅ SUCCESS CASE:
[CACHE STORED] /filename.txt (empty, no refetch)  <- Blue text, indicates cache was set
[CACHE HIT] /filename.txt                         <- Green text, subsequent loads from cache
```

```
⚠️ WARNING (expected in some cases):
[STALE] Ignoring response for old request        <- Race condition prevention working
[CACHE INVALIDATED] /filename.txt (after delete) <- Cache cleanup working
```

---

## Known Limitations & Notes

1. **Parent directory must exist:** If creating `/src/new/deep/file.txt`, parent `/src/new/deep` must exist first
   - Create parent directory first using "New Dir"

2. **Path format:** Must start with `/` and use forward slashes `/`
   - ✅ `/file.txt` (correct)
   - ✅ `/src/file.txt` (correct)
   - ❌ `file.txt` (invalid - no `/` prefix)
   - ❌ `\file.txt` (invalid - Windows path)

3. **File extension matters:** `.txt`, `.tsx`, `.md`, etc. can be any extension

---

## Failure Cases to Avoid

1. **Stale content:** If you see old file's content in editor → Cache issue
2. **API error 400:** Usually means invalid path format (check validation)
3. **API error 404:** Parent directory doesn't exist
4. **API error 403:** Permission denied (security validation)
5. **File not in list:** List refresh might take 1-2 seconds, wait a moment

---

## Summary

All 10 tests should pass with no errors. If any test fails, check:
1. Console logs for error messages
2. Network tab for API responses
3. Browser DevTools → Application → Cache (if available)

**Success Criteria:**
- [ ] Tests 1-6: Core functionality working
- [ ] Tests 7-9: Edge cases handled
- [ ] Test 10: UX is smooth and natural
- [ ] No stale content, no race conditions
- [ ] Cache integration seamless

---

**Implementation:** All 4 phases complete
**Status:** Ready for manual validation ✅
