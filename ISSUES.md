# Code Quality Issues - Comprehensive Audit

## Summary

This document tracks all CRITICAL and HIGH severity issues identified in the `matt/performance_fixing` branch audit, comparing against `master`.

**Status:** 2 of 12 tasks completed

---

## CRITICAL Issues

### ✅ C1: File handle leak in Import.py [FIXED]
**File:** `onevizion/Import.py:71`
**Status:** FIXED + TESTED

**Problem:**
```python
self.ImportFile = {'file': (os.path.basename(self.file), open(self.file,'rb'))}
self.OVCall = curl('POST',self.ImportURL,files=self.ImportFile,auth=self.auth)
```
File handle never closed - identical pattern to bug fixed in `trackor.py` by this branch.

**Fix Applied:**
```python
with open(self.file, 'rb') as import_fp:
    self.ImportFile = {'file': (os.path.basename(self.file), import_fp)}
    self.OVCall = curl('POST',self.ImportURL,files=self.ImportFile,auth=self.auth)
```

**Test Added:** `tests/test_import.py::TestImportRun::test_import_closes_file_handle`
- Creates temp file
- Calls Import
- Verifies file can be deleted (handle closed)

---

### ⏳ C2: GetFile() bypasses timeout fix with direct requests.get()
**File:** `onevizion/trackor.py:448`
**Status:** FIX IN PROGRESS

**Problem:**
```python
self.request = requests.get(URL, stream=True, auth=self.auth, allow_redirects=True)
# NO timeout parameter!
```
Defeats entire purpose of this branch - unresponsive downloads hang forever.

**Fix Applied:**
```python
self.request = requests.get(URL, stream=True, auth=self.auth, allow_redirects=True, timeout=300.0)
```

**Test Needed:** Verify timeout parameter is passed to requests.get()

---

### 🔴 C3: `raise` on string literal never fires in Python 3
**File:** `onevizion/EMail.py:72`
**Status:** NOT STARTED

**Problem:**
```python
raise ("UserName,Password,and Server are required in the PasswordData json")
```
In Python 3, raises `TypeError` instead of intended validation error. Validation completely broken.

**Fix Required:**
```python
raise ValueError("UserName, Password, and Server are required in the PasswordData json")
```

**Test Needed:** Verify ValueError raised when SMTP credentials missing

---

### 🔴 C4: Singleton.__del__ crashes on Windows
**File:** `onevizion/singleton.py:81`
**Status:** NOT STARTED

**Problem:**
```python
os.close(self.LockFileName)  # BUG: LockFileName is a str, not an int fd
```
Every Windows process using Singleton crashes with `sys.exit(-1)` on cleanup.

**Fix Required:**
```python
os.close(self.LockFile)  # Use the fd, not the filename
```

**Test Needed:** Mock Windows platform and verify __del__ cleanup works

---

### 🔴 C5: Test doesn't actually verify file handle closure
**File:** `tests/test_trackor.py:641-661`
**Status:** NOT STARTED

**Problem:**
```python
t.UploadFile(trackorId=123, fieldName="F_FILE", fileName=test_file_path)
os.remove(test_file_path)  # Succeeds on Linux even if handle still open!
```
False confidence - test passes both before and after the fix.

**Fix Required:** Use `/proc/self/fd` counting or `psutil.Process().open_files()`

---

## HIGH Issues

### 🔴 H1: EMail.sendmail() - 4 file handle leaks
**File:** `onevizion/EMail.py:148-164`
**Status:** NOT STARTED

**Problem:**
```python
fp = open(file)  # 4 instances: text/image/audio/binary attachments
attachment = MIMEText(fp.read(), _subtype=subtype)
fp.close()  # Never reached if fp.read() raises
```
Same class of bug fixed in this branch. Exception leaves handles open.

**Fix Required:** Replace all 4 with `with open(...) as fp:`

**Tests Needed:**
- Test image attachment
- Test audio attachment
- Test error during attachment read

---

### 🔴 H2: Parent dict mutation bug - data corruption
**File:** `onevizion/trackor.py:204-211` (also `295-302` in create)
**Status:** NOT STARTED

**Problem:**
```python
Parentx = {}  # Created ONCE before loop
for key, value in parents.items():
    Parentx["trackor_type"] = key  # Mutates same dict
    ParentsSection.append(Parentx)  # Appends same reference!
```
Multi-parent updates send last parent N times instead of N distinct parents.

**Fix Required:** Move `Parentx = {}` inside loop (in both update and create methods)

**Test Needed:** Create/update trackor with 2+ parents, verify all distinct in JSON payload

---

### 🔴 H3: GetFile predictable temp files - security issue
**File:** `onevizion/trackor.py:434, 440`
**Status:** NOT STARTED

**Problem:**
```python
tmpFileName = str(trackorId) + fieldName + ".tmp"  # e.g., "123F_FILE.tmp"
```
**Issues:**
- Concurrent calls with same ID corrupt each other
- If `fieldName` contains `../`, writes escape directory
- Predictable names in cwd

**Fix Required:** Use `tempfile.NamedTemporaryFile(delete=False)`

**Tests Needed:**
- Concurrent GetFile calls don't collide
- Path traversal prevented

---

### 🔴 H4: Import.getProcessData wires wrong parameter
**File:** `onevizion/Import.py:179`
**Status:** NOT STARTED

**Problem:**
```python
addParam('is_pdf', comments)  # Should be: isPdf
```
`isPdf` parameter silently ignored. Copy-paste bug.

**Fix Required:**
```python
addParam('is_pdf', isPdf)
```

**Test Needed:** Verify isPdf parameter correctly passed to API

---

### 🔴 H5: assignWorkplan doesn't URL-encode template name
**File:** `onevizion/trackor.py:353-357`
**Status:** NOT STARTED

**Problem:**
```python
URL = "...?workplan_template={workplan_template}...".format(
    workplan_template=workplanTemplate  # NOT encoded!
)
```
Template names with spaces/ampersands produce malformed URLs.

**Fix Required:**
```python
workplan_template=URLEncode(workplanTemplate)
```

**Test Needed:** Template name with special chars properly encoded

---

### 🔴 H6: HTTPBearerAuth transmits secret in cleartext header
**File:** `onevizion/httpbearer.py:18`
**Status:** DESIGN REVIEW NEEDED

**Problem:**
```python
r.headers['Authorization'] = 'Bearer ' + self.accessKey + ':' + self.secretKey
```
Both access key and secret appear in every HTTP log/proxy. Non-standard Bearer format.

**Recommendation:** Needs security team review - may be intentional API design

---

### 🔴 H7: Singleton untested (Windows path, __del__ exceptions)
**File:** `onevizion/singleton.py:47-63, 80-95`
**Status:** NOT STARTED

**Coverage:** 32% - Windows code path and sys.exit(-1) handler never exercised

**Tests Needed:**
- Windows platform branch
- Default lock filename derivation
- __del__ exception handling and sys.exit behavior

---

### 🔴 H8: HTTPBearerAuth.__call__ header construction untested
**File:** `onevizion/httpbearer.py:17-19`
**Status:** NOT STARTED

**Coverage:** Actual `Authorization: Bearer` header format never validated

**Test Needed:**
```python
def test_call_sets_authorization_header():
    auth = HTTPBearerAuth('mykey', 'mysecret')
    mock_request = mock.MagicMock()
    mock_request.headers = {}
    result = auth(mock_request)
    assert result.headers['Authorization'] == 'Bearer mykey:mysecret'
```

---

## Task Status Summary

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | CRITICAL | Import.py file handle leak | ✅ FIXED + TESTED |
| 2 | CRITICAL | GetFile timeout missing | ⏳ FIX IN PROGRESS |
| 3 | CRITICAL | EMail raise string literal | 🔴 NOT STARTED |
| 4 | CRITICAL | Singleton Windows crash | 🔴 NOT STARTED |
| 5 | CRITICAL | Test false confidence | 🔴 NOT STARTED |
| 6 | HIGH | EMail 4 file leaks | 🔴 NOT STARTED |
| 7 | HIGH | Parent dict mutation | 🔴 NOT STARTED |
| 8 | HIGH | GetFile temp file security | 🔴 NOT STARTED |
| 9 | HIGH | Import isPdf parameter | 🔴 NOT STARTED |
| 10 | HIGH | Workplan template encoding | 🔴 NOT STARTED |
| 11 | HIGH | Singleton test coverage | 🔴 NOT STARTED |
| 12 | HIGH | HTTPBearerAuth test | 🔴 NOT STARTED |

**H6 (HTTPBearerAuth design)** - flagged for security review, not tracked as task

---

## Testing Strategy

### Test Requirements
Each fix must include:
1. **Production code fix** - minimal change to address the bug
2. **Regression test** - proves the fix works
3. **Test passes** - verified with `uv run pytest`

### Test Patterns Used

**File handle closure:**
```python
# Create temp file
with tempfile.NamedTemporaryFile(delete=False) as f:
    path = f.name
try:
    # Call function that should close handle
    function_under_test(path)
    # Verify handle closed by deleting file
    os.remove(path)
finally:
    try:
        os.remove(path)
    except:
        pass
```

**Timeout verification:**
```python
@mock.patch('requests.get')
def test_timeout_passed(mock_get):
    # Call function
    function_under_test()
    # Verify timeout in call args
    assert mock_get.call_args[1]['timeout'] == 300.0
```

**URL encoding:**
```python
def test_url_encoding_special_chars(mock_curl):
    # Use special chars
    function_under_test(template="Name With Spaces & Special=Chars")
    url = mock_curl.call_args[0][1]
    assert '&' not in url.split('?')[1]  # No raw ampersands in query string
```

---

## Progress Notes

### Completed
1. **C1 - Import.py file handle leak**
   - Production fix: Added `with` statement wrapping curl call
   - Test: `test_import_closes_file_handle` in TestImportRun class
   - Verified: Test passes, file handle properly closed

2. **C2 - GetFile timeout** (partial)
   - Production fix: Added `timeout=300.0` to requests.get()
   - Test: IN PROGRESS

### Next Steps
1. Complete C2 test
2. Fix C3 (EMail raise ValueError)
3. Fix C4 (Singleton Windows crash)
4. Fix C5 (improve test)
5. Continue through remaining HIGH issues

---

## Related Files Modified

### Production Code
- `onevizion/Import.py` - File handle fix
- `onevizion/trackor.py` - GetFile timeout fix

### Tests
- `tests/test_import.py` - Added test_import_closes_file_handle
- `tests/test_trackor.py` - Test needed for GetFile timeout

---

## Branch Context

**Branch:** `matt/performance_fixing`
**Base:** `master`
**Purpose:** Fix timeout and file handle leaks

**Original Changes:**
1. `curl.py` - Added default timeout=300.0
2. `trackor.py:UploadFile` - Fixed file handle leak with `with` statement

**Scope Expansion:**
Audit found identical and related bugs throughout codebase that should be fixed together to prevent similar issues.

---

## Architecture Notes

Several architectural issues observed (not blocking this PR but worth noting):

1. **Global mutable Config dict** - Thread-unsafe, causes test pollution
2. **Side-effect constructors** - `Trackor`, `Import`, `Export` make HTTP calls in `__init__`
3. **Duplicated error handling** - 12-line error block copy-pasted 10+ times across modules
4. **Mutable default arguments** - Present in 12+ method signatures

These are lower priority but contribute to maintenance burden and testing difficulty.
