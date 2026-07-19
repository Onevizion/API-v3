# OneVizion Package Fixes for Downstream Dependencies

**Problem**: The onevizion package has critical bugs causing infinite hangs in downstream projects (sftp-to-efile).

**Root Causes**:
1. ❌ `curl.py` has NO timeout protection (infinite hangs)
2. ❌ `trackor.py` leaks file handles (resource exhaustion)
3. ❌ No connection pooling or retry logic

---

## Fix 1: Add Timeout Protection to curl.py

### Current Bug

**File**: `onevizion/curl.py:18-88`

```python
class curl:
    def __init__(self, ...):
        self.timeout = None  # ← HARDCODED, never used

    def runQuery(self):
        # NO TIMEOUT = infinite hang on slow/0KB file responses
        self.request = requests.request(self.method, self.url, **self.args)
```

**Impact**: 0KB files or slow networks cause indefinite hangs, blocking all file processing.

### Fix Options

#### Option A: Add timeout parameter (minimal change)

```python
class curl:
    def __init__(self, method='GET', url=None, timeout=60.0, **kwargs):
        # ... existing code ...
        self.timeout = timeout  # ← Use provided timeout

    def runQuery(self):
        # ... existing code ...
        try:
            self.request = requests.request(
                self.method,
                self.url,
                timeout=self.timeout,  # ← ADD TIMEOUT
                **self.args
            )
        except requests.Timeout as e:
            self.errors.append(f"Request timed out after {self.timeout}s")
```

**Changes**:
- Accept `timeout` parameter (default 60s)
- Pass to requests.request()
- Handle Timeout exceptions

**Benefits**:
- ✅ Minimal code change
- ✅ Backward compatible (default timeout)
- ✅ Fixes infinite hangs

**Cons**:
- ⚠️ Still uses requests (no connection pooling)
- ⚠️ No retry logic

#### Option B: Replace with httpx (recommended in FIX_PLAN)

```python
"""Modern HTTP client with timeout, retry, and connection pooling"""
import httpx
from datetime import datetime
from typing import Optional

class HttpClient:
    """Replacement for curl - uses httpx with proper timeout"""

    def __init__(self, method='GET', url=None, timeout=60.0, **kwargs):
        self.method = method
        self.url = url
        self.timeout = timeout
        self.kwargs = kwargs

        # Response tracking (backward compatibility)
        self.request = None
        self.errors = []
        self.jsonData = {}
        self.duration = None

        # Auto-run if URL provided
        if self.url:
            self.runQuery()

    def runQuery(self):
        self.errors = []
        self.jsonData = {}
        before = datetime.utcnow()

        try:
            response = httpx.request(
                method=self.method,
                url=self.url,
                timeout=self.timeout,
                **self.kwargs
            )
            self.request = response

            if not (200 <= response.status_code < 300):
                self.errors.append(
                    f"{response.status_code} = {response.reason_phrase}\n{response.text}"
                )

            try:
                self.jsonData = response.json()
            except Exception:
                pass

        except httpx.TimeoutException as e:
            self.errors.append(f"Timeout after {self.timeout}s: {e}")
        except httpx.RequestError as e:
            self.errors.append(f"Request failed: {e}")
        except Exception as e:
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            self.errors.append(str(e))

        self.duration = (datetime.utcnow() - before).total_seconds()

# Backward compatibility
curl = HttpClient
```

**Benefits**:
- ✅ Built-in timeout protection
- ✅ Connection pooling (reuses connections)
- ✅ Better error handling
- ✅ HTTP/2 support
- ✅ Drop-in replacement (same API)

**Cons**:
- ⚠️ New dependency (httpx)
- ⚠️ Slightly different response object

### Recommendation

**Start with Option A** (minimal risk):
1. Add timeout to existing curl.py
2. Test all existing uses
3. Release as patch version

**Then migrate to Option B** (better long-term):
1. Create http_client.py with httpx
2. Add httpx to dependencies
3. Update imports gradually
4. Deprecate curl.py

---

## Fix 2: File Handle Leak in trackor.py

### Current Bug

**File**: `onevizion/trackor.py:498-504`

```python
def UploadFile(self, trackorId, fieldName, fileName, newFileName=None):
    FilePath = fileName
    FileName = newFileName if newFileName else os.path.basename(FilePath)

    BinaryStream = open(FilePath, 'rb')  # ← NEVER CLOSED!

    self.UploadFileByFileContents(
        trackorId=trackorId,
        fieldName=fieldName,
        fileName=FileName,
        fileContents=BinaryStream  # ← File handle leaked
    )
```

**Impact**: After uploading 1024 files, system runs out of file descriptors.

### Fix

```python
def UploadFile(self, trackorId, fieldName, fileName, newFileName=None):
    FilePath = fileName
    FileName = newFileName if newFileName else os.path.basename(FilePath)

    with open(FilePath, 'rb') as BinaryStream:  # ← Auto-closes
        self.UploadFileByFileContents(
            trackorId=trackorId,
            fieldName=fieldName,
            fileName=FileName,
            fileContents=BinaryStream
        )
```

**Changes**:
- Use `with` statement for automatic file closure
- File handle guaranteed to close even on exception

**Testing**:
```python
# Test: Upload 2000 files should not exhaust file descriptors
for i in range(2000):
    trackor.UploadFile(trackorId=123, fieldName="F_FILE", fileName=f"test{i}.txt")
```

---

## Fix 3: Add Connection Pooling

### Current Problem

Every API call creates a new TCP connection:

```python
# 100 files = 100 new connections = slow
for file in files:
    trackor.UploadFile(...)  # New connection each time
```

### Fix: Session Reuse

**File**: `onevizion/trackor.py`

Add session pooling:

```python
class Trackor:
    def __init__(self, ...):
        # ... existing code ...
        self._session = None  # Lazy-init session

    @property
    def session(self):
        """Reusable session for connection pooling"""
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = self.auth
        return self._session

    def UploadFileByFileContents(self, ...):
        # Change from:
        # self.OVCall = curl('POST', url, ...)

        # To (if using requests):
        response = self.session.post(url, files=files, timeout=60.0)

        # OR (if using httpx):
        if not hasattr(self, '_http_client'):
            self._http_client = httpx.Client(timeout=60.0)
        response = self._http_client.post(url, files=files)
```

**Benefits**:
- ✅ Reuses TCP connections
- ✅ 5-10x faster for bulk operations
- ✅ Reduces server load

---

## Implementation Plan

### Phase 1: Critical Fixes (Week 1)

**Priority 1: Add timeout to curl.py**

```bash
# 1. Add timeout parameter
git checkout -b fix/curl-timeout

# 2. Edit onevizion/curl.py
# 3. Add tests
# 4. Run full test suite
uv run pytest tests/ -v

# 5. Commit and push
git commit -m "Add timeout parameter to curl class

- Default 60s timeout prevents infinite hangs
- Backward compatible (existing code works)
- Handles requests.Timeout exception"

git push origin fix/curl-timeout
```

**Priority 2: Fix file handle leak**

```bash
git checkout -b fix/trackor-file-leak

# Edit onevizion/trackor.py (use with statement)
# Test with 2000 file uploads
# Commit and push
```

**Priority 3: Add tests**

```python
# tests/test_curl.py

def test_curl_respects_timeout():
    """Verify timeout parameter is used"""
    import time

    # Mock a slow server
    with mock.patch('requests.request') as mock_request:
        mock_request.side_effect = requests.Timeout("Connection timeout")

        c = curl('GET', 'http://slow-server.com', timeout=5.0)

        assert len(c.errors) > 0
        assert "timeout" in c.errors[0].lower()

def test_curl_default_timeout():
    """Verify default 60s timeout"""
    with mock.patch('requests.request') as mock_request:
        mock_request.return_value = mock.MagicMock(status_code=200)

        c = curl('GET', 'http://example.com')

        # Verify timeout was passed
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs['timeout'] == 60.0
```

**Release**: v1.1.8 (patch release)

---

### Phase 2: httpx Migration (Week 2-3)

**Step 1: Add httpx dependency**

```toml
# pyproject.toml
[project]
dependencies = [
    "requests>=2.20.0",
    "httpx>=0.27.0",  # Add httpx
]
```

**Step 2: Create http_client.py**

```bash
git checkout -b feature/httpx-client

# Create onevizion/http_client.py
# Implement HttpClient class (see Option B above)
# Add tests
```

**Step 3: Gradual migration**

```python
# onevizion/__init__.py

# Phase 1: Import both
from onevizion.curl import curl
from onevizion.http_client import HttpClient

# Phase 2 (later): Switch default
# from onevizion.http_client import HttpClient as curl
# from onevizion.curl import curl as LegacyCurl  # deprecated
```

**Step 4: Update high-traffic modules**

Priority order:
1. `trackor.py` (most used)
2. `export.py`
3. `Import.py`
4. `task.py`
5. `workplan.py`

**Release**: v1.2.0 (minor version)

---

### Phase 3: Connection Pooling (Week 4)

**Add session reuse to all modules**

Each module (Trackor, Export, Import, etc.) should:
1. Create session/client in `__init__`
2. Reuse for all requests
3. Close in `__del__` (optional)

**Release**: v1.3.0 (minor version)

---

## Testing Strategy

### Unit Tests

```python
# tests/test_curl_timeout.py

import pytest
import requests
from onevizion.curl import curl

def test_timeout_parameter_passed():
    """Timeout parameter is passed to requests"""
    with mock.patch('requests.request') as mock_req:
        mock_req.return_value = mock.MagicMock(status_code=200)

        c = curl('GET', 'http://example.com', timeout=30.0)

        assert mock_req.call_args[1]['timeout'] == 30.0

def test_timeout_exception_caught():
    """Timeout exceptions are caught and logged"""
    with mock.patch('requests.request') as mock_req:
        mock_req.side_effect = requests.Timeout()

        c = curl('GET', 'http://slow.com', timeout=5.0)

        assert len(c.errors) > 0
        assert 'timeout' in str(c.errors[0]).lower()

def test_default_timeout():
    """Default timeout is 60 seconds"""
    with mock.patch('requests.request') as mock_req:
        mock_req.return_value = mock.MagicMock(status_code=200)

        c = curl('GET', 'http://example.com')

        assert mock_req.call_args[1]['timeout'] == 60.0
```

### Integration Tests

```python
# tests/test_trackor_file_handles.py

import pytest
import tempfile
from onevizion.trackor import Trackor

def test_upload_many_files_no_leak():
    """Uploading many files doesn't leak file descriptors"""
    import resource

    # Get initial open files
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    initial_fds = len(os.listdir('/proc/self/fd'))

    # Create test files
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(100):
            test_file = f"{tmpdir}/test{i}.txt"
            with open(test_file, 'w') as f:
                f.write(f"test content {i}")

        # Upload files (with mocked curl)
        with mock.patch('onevizion.trackor.curl') as mock_curl:
            mock_curl.return_value.errors = []

            t = Trackor(trackorType="Test", URL="http://test.com",
                       userName="u", password="p")

            for i in range(100):
                t.UploadFile(trackorId=123, fieldName="F_FILE",
                           fileName=f"{tmpdir}/test{i}.txt")

    # Check file descriptors didn't leak
    final_fds = len(os.listdir('/proc/self/fd'))
    assert final_fds - initial_fds < 10  # Allow small variation
```

---

## Backward Compatibility

### Ensure existing code works

All changes must be backward compatible:

```python
# These should all still work:

# 1. Basic usage (timeout added automatically)
from onevizion.curl import curl
c = curl('GET', 'http://api.com/data')

# 2. With custom timeout (new)
c = curl('GET', 'http://slow-api.com/data', timeout=120.0)

# 3. Disable timeout (if needed)
c = curl('GET', 'http://trusted-api.com/data', timeout=None)

# 4. All existing kwargs still work
c = curl('POST', url, auth=auth, json=data, headers=headers)
```

---

## Documentation Updates

### Update README.md

```markdown
## Timeout Protection (v1.1.8+)

All HTTP requests now have a default 60-second timeout to prevent infinite hangs.

### Custom Timeout

\```python
from onevizion.curl import curl

# 2 minute timeout for slow API
c = curl('GET', 'http://slow-api.com/export', timeout=120.0)
\```

### Disable Timeout

\```python
# Not recommended - use for trusted internal APIs only
c = curl('GET', 'http://internal-api.local/data', timeout=None)
\```
```

---

## Release Checklist

### v1.1.8 (Patch - Critical Fixes)

- [ ] Add timeout parameter to curl.py
- [ ] Fix file handle leak in trackor.py
- [ ] Add timeout tests
- [ ] Add file handle leak tests
- [ ] Update CHANGELOG.md
- [ ] Run full test suite on Python 2.7, 3.5-3.13
- [ ] Create PR
- [ ] Review and merge
- [ ] Tag release: `git tag v1.1.8`
- [ ] Push to PyPI

### v1.2.0 (Minor - httpx Migration)

- [ ] Add httpx dependency
- [ ] Create http_client.py
- [ ] Add HttpClient tests
- [ ] Update documentation
- [ ] Gradual migration plan
- [ ] Tag release: `git tag v1.2.0`

### v1.3.0 (Minor - Connection Pooling)

- [ ] Add session reuse to all modules
- [ ] Add pooling tests
- [ ] Performance benchmarks
- [ ] Tag release: `git tag v1.3.0`

---

## Impact on Downstream Projects

### sftp-to-efile

Once v1.1.8 is released:

```python
# requirements.txt
onevizion>=1.1.8  # Get timeout protection
```

**Benefits**:
- ✅ No more infinite hangs on 0KB files
- ✅ No more file descriptor exhaustion
- ✅ 60s timeout on all API calls

### Other Projects

All projects using onevizion package get:
- Automatic timeout protection
- Better error messages
- File handle safety

---

## Timeline

| Week | Task | Release |
|------|------|---------|
| 1 | Add timeout to curl.py | v1.1.8 (patch) |
| 1 | Fix file handle leak | v1.1.8 (patch) |
| 1 | Add tests | v1.1.8 (patch) |
| 2-3 | Create httpx client | v1.2.0 (minor) |
| 2-3 | Migrate high-traffic modules | v1.2.0 (minor) |
| 4 | Add connection pooling | v1.3.0 (minor) |

**Critical Path**: Week 1 fixes stop the bleeding for sftp-to-efile.

---

## Success Metrics

### Before Fixes
- ❌ Infinite hangs on 0KB files
- ❌ File descriptor exhaustion after 1000 files
- ❌ No timeout protection
- ❌ New connection per request

### After v1.1.8
- ✅ 60s timeout prevents hangs
- ✅ File handles properly closed
- ✅ Clear timeout error messages
- ⚠️ Still new connection per request

### After v1.3.0
- ✅ All v1.1.8 benefits
- ✅ Connection pooling (5-10x faster bulk ops)
- ✅ HTTP/2 support
- ✅ Better error handling
