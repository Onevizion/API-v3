# Full Clean Refactor TODO

## Progress: 8/58 tasks complete (14%)

---

## ✅ CRITICAL (4/4 complete) - 100%

- [x] Fix unreachable `attempt += 1` in curl.py retry loop
- [x] Add 3xx redirect handling in curl.py
- [x] Remove redundant response closing in trackor.py GetFile
- [x] Add parameter type validation in trackor.py GetFile

---

## 🔄 HIGH Priority (4/12 complete) - 33%

### Dangerous Patterns
- [x] Validate kwargs against allowed list in curl.py (no more dangerous setattr)
- [x] Document state reset behavior in curl.py runQuery()

### DRY - Code Duplication
- [x] Extract `_build_fields_section()` helper in trackor.py
- [x] Extract `_build_parents_section()` helper in trackor.py
- [ ] **Apply `_execute_api_call()` to remaining methods:** (Est: 45min)
  - [ ] trackor.py: read()
  - [ ] trackor.py: update()
  - [ ] trackor.py: create()
  - [ ] trackor.py: assignWorkplan()
  - [ ] trackor.py: UploadFile()

### Code Organization
- [ ] Extract `_init_from_param_token()` in trackor.py (Est: 15min)
- [ ] Remove duplicate URL protocol validation (trackor vs curl) (Est: 20min)
  - Delegate to curl or create shared validator

---

## 📋 MEDIUM Priority (0/10 complete) - 0%

### curl.py
- [ ] Split `_validate_inputs()` into focused validators (Est: 30min)
  - [ ] `_validate_url()`
  - [ ] `_validate_method()`
  - [ ] `_validate_timeout()`
  - [ ] `_validate_retries()`

- [ ] Improve HTTP error formatting in `_append_http_error()` (Est: 10min)
  - Use consistent format strings, not concatenation

- [ ] Rename `jsonData` → `json_data` for PEP 8 (Est: 30min)
  - **Breaking change** - needs major version bump or deprecation

- [ ] Refactor `__init__` to use config object or builder pattern (Est: 1h)
  - Too many parameters (7 + **kwargs)

### trackor.py
- [ ] Move `get_filename_from_cd()` out of GetFile() (Est: 10min)
  - Make it a private method or module-level function

- [ ] Clarify conditional JSON building in update() (Est: 15min)
  - Add comments or restructure logic

- [ ] Group related instance variables (Est: 30min)
  - Credentials, API state, configuration

- [ ] Extract `_build_read_url()` helper for read() method (Est: 30min)
  - Complex URL building logic

- [ ] Break down GetFile() method (Est: 45min)
  - Currently 63 lines, does too much
  - Extract: parameter validation, file size checking, file writing

- [ ] Use consistent tmpFileName generation pattern (Est: 10min)
  - Two different patterns at lines 519, 525

---

## 🎨 LOW Priority (0/10 complete) - 0%

### Naming Conventions (PEP 8)
- [ ] Consider renaming `curl` class → `Curl` or `CurlClient` (Est: 2h)
  - **Breaking change** - needs major version bump
  - Or add deprecation + alias

- [ ] Rename `setArg` → `set_arg` in curl.py (Est: 15min)
  - **Breaking change** or add alias

- [ ] Fix variable naming in trackor.py (Est: 30min)
  - `tmpFileName` → `tmp_file_name`
  - `FileName` → `file_name`
  - `FilePath` → `file_path`

### Documentation
- [ ] Improve docstring formatting in curl.py (Est: 20min)
  - Add proper sections: Args, Returns, Raises

- [ ] Fix docstring formatting in trackor.py (Est: 20min)
  - Inconsistent spacing and indentation

- [ ] Fix mixed string formatting (Est: 30min)
  - Use `.format()` consistently, not manual `+` concatenation

### Code Quality
- [ ] Make `_append_http_error()` static or refactor (Est: 10min)

- [ ] Improve regex in trackor.py GetFile `get_filename_from_cd()` (Est: 20min)
  - Current regex is fragile, handle edge cases better

- [ ] Fix line spacing issues (Est: 5min)
  - 3 blank lines between methods (should be 2)

- [ ] Standardize error messages (Est: 15min)
  - Consistent capitalization and punctuation

---

## 🧹 Code Smell Cleanup (0/8 complete) - 0%

### Import Issues
- [ ] Replace wildcard imports `from onevizion.util import *` (Est: 1h)
  - Explicit imports throughout codebase
  - **Could be breaking** if users rely on re-exports

- [ ] Remove unused imports flagged by tooling (Est: 15min)

### Architecture
- [ ] Replace magic attribute tuple in curl.py with class variable (Est: 20min)
  - Lines 150-153: tuple of attribute names

- [ ] Consider extracting request building logic to separate class (Est: 2h)
  - curl is doing too much

- [ ] Add type hints (Python 3.5+ compatible) (Est: 3h)
  - Would help catch issues statically

### Testing
- [ ] Add tests for new helper methods (Est: 1h)
  - `_build_fields_section()`
  - `_build_parents_section()`
  - `_execute_api_call()`
  - `_sleep_with_backoff()`
  - `_append_http_error()`

- [ ] Add tests for edge cases in validation (Est: 30min)

- [ ] Ensure test coverage for all error paths (Est: 1h)

---

## 📦 Technical Debt (0/6 complete) - 0%

- [ ] Remove deprecated Singleton class (for v2.0.0)
  - Already deprecated in this refactor

- [ ] Create migration guide for breaking changes (Est: 2h)

- [ ] Add CHANGELOG.md with all changes (Est: 30min)

- [ ] Consider adding pyproject.toml `[tool.pyright]` config (Est: 15min)
  - Address Pyright diagnostics systematically

- [ ] Review and update README.md examples (Est: 1h)
  - Ensure examples follow new best practices

- [ ] Add contributing guide with code style (Est: 1h)

---

## Time Estimates

| Priority | Remaining | Est. Time |
|----------|-----------|-----------|
| HIGH     | 8 tasks   | ~2h       |
| MEDIUM   | 10 tasks  | ~4h       |
| LOW      | 10 tasks  | ~3h       |
| SMELLS   | 8 tasks   | ~8h       |
| DEBT     | 6 tasks   | ~5h       |
| **TOTAL**| **42**    | **~22h**  |

---

## Milestones

### Milestone 1: Complete HIGH Priority (2h)
Ship with all critical/high issues resolved. Good stopping point.

### Milestone 2: + MEDIUM Priority (6h total)
Code is significantly cleaner, methods are well-structured.

### Milestone 3: + LOW Priority (9h total)  
PEP 8 compliant, well-documented, professional quality.

### Milestone 4: Full Clean (22h total)
Zero technical debt, modern architecture, fully typed, excellent test coverage.

---

## Breaking Changes to Track

These require major version bump (v2.0.0) or deprecation cycle:

1. `curl` class name → `Curl`
2. `jsonData` → `json_data`
3. `setArg` → `set_arg`
4. Wildcard imports removal
5. Remove Singleton class

## Quick Wins (Do These First)

1. ✅ Apply `_execute_api_call()` to remaining methods (45min, high impact)
2. Split `_validate_inputs()` (30min, cleaner code)
3. Extract `_build_read_url()` (30min, DRY)
4. Fix variable naming (30min, PEP 8)
5. Improve docstrings (40min, better DX)

**Total Quick Wins: ~3h for massive readability improvement**
