# Root Cause Analysis - Issue #29

**Issue**: Backend container fails to start with `ModuleNotFoundError: No module named 'slowapi'`
**Root Cause**: Missing dependency - `slowapi` was used in code but never added to `pyproject.toml`
**Severity**: Critical (blocks backend startup)
**Confidence**: High (direct evidence from code and git history)

## Evidence Chain

### The Path from Symptom to Cause

**SYMPTOM**: Backend container exits immediately on startup
↓ BECAUSE: Python import fails when loading `src/main.py`
  Evidence: Docker logs show:
  ```
  Traceback (most recent call last):
    File "<frozen runpy>", line 198, in _run_module_as_main
    File "<frozen runpy>", line 88, in _run_code
    File "/app/src/main.py", line 14, in <module>
      from slowapi.errors import RateLimitExceeded
  ModuleNotFoundError: No module named 'slowapi'
  ```

**WHY**: Python import fails for `slowapi.errors.RateLimitExceeded`
↓ BECAUSE: The `slowapi` package is not installed in the container
  Evidence: `src/main.py:14` - `from slowapi.errors import RateLimitExceeded`
  Evidence: `src/middleware/rate_limit.py:7-9` - Multiple slowapi imports:
  ```python
  from slowapi import Limiter
  from slowapi.util import get_remote_address
  from slowapi.errors import RateLimitExceeded
  ```

**WHY**: `slowapi` package is not installed
↓ BECAUSE: Package is not listed in project dependencies
  Evidence: `pyproject.toml` lines 11-41 - Complete dependencies list with NO `slowapi` entry:
  ```toml
  dependencies = [
      # Core framework
      "fastapi>=0.115.0",
      "uvicorn[standard]>=0.32.0",
      # AI Agent
      "pydantic-ai>=0.0.14",
      "anthropic>=0.42.0",
      # Database
      "sqlalchemy[asyncio]>=2.0.36",
      "asyncpg>=0.30.0",
      "alembic>=1.14.0",
      # Telegram Bot
      "python-telegram-bot>=22.5",
      # GitHub Integration
      "PyGithub>=2.5.0",
      "httpx>=0.28.0",
      # Web Interface Support
      "sse-starlette>=2.1.0",
      # Utilities
      "pydantic>=2.10.0",
      "pydantic-settings>=2.7.0",
      "python-dotenv>=1.0.0",
      "tenacity>=9.0.0",
      "python-multipart>=0.0.20",
  ]
  ```
  **MISSING**: No "slowapi" dependency

**WHY**: `slowapi` was never added to dependencies
↓ ROOT CAUSE: Production hardening commit (fe20dda) added rate limiting code using slowapi but forgot to update pyproject.toml
  Evidence:
  - Commit `fe20dda9ce54bccbc88297d579348655bdfe5dc0` (2026-01-03)
  - Commit message: "feat: Complete production hardening implementation (Issue #28)"
  - Added files: `src/middleware/rate_limit.py` with slowapi imports
  - Modified: `src/main.py` to import `slowapi.errors.RateLimitExceeded`
  - **NOT modified**: `pyproject.toml` (confirmed by git show - no dependency files changed)

### Git History Context

- **Introduced**: fe20dda9ce54bccbc88297d579348655bdfe5dc0
- **Commit message**: "feat: Complete production hardening implementation (Issue #28)"
- **Author**: Claude Code
- **Date**: 2026-01-03 (2 days ago)
- **Recent changes**: This is the only commit that introduced slowapi usage
- **Implication**: This is an **original bug** from the production hardening feature implementation. The code was added with the dependency missing from the start.

### Alternative Hypotheses Considered

**Hypothesis A: slowapi was installed but removed accidentally**
- ❌ RULED OUT: Git history shows pyproject.toml was never modified to include slowapi
- Evidence: `git log --oneline -- pyproject.toml` shows no commits adding slowapi

**Hypothesis B: Different package name or import path**
- ❌ RULED OUT: slowapi is the correct PyPI package name for the Limiter class being used
- Evidence: Official slowapi docs confirm: `from slowapi import Limiter`

**Hypothesis C: Optional dependency that should fail gracefully**
- ❌ RULED OUT: Rate limiting is imported at module level (line 14 of main.py), not in try/except
- Evidence: No error handling around the import statement

## Fix Specification

### What Needs to Change

Add `slowapi` to the project dependencies in `pyproject.toml`.

**File to modify**: `pyproject.toml`
**Location**: Dependencies list (lines 11-41)
**Change**: Add `slowapi` package with appropriate version constraint

### Implementation Guidance

```toml
# Current (missing slowapi):
dependencies = [
    # Core framework
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    # ...other deps...
]

# Required (add slowapi):
dependencies = [
    # Core framework
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "slowapi>=0.1.9",  # Rate limiting middleware
    # ...other deps...
]
```

**Key considerations for implementation:**

1. **Version constraint**: Use `>=0.1.9` to ensure compatibility with FastAPI's current version. The slowapi package is stable and actively maintained.

2. **Placement**: Add after `uvicorn` in the "Core framework" section since it's FastAPI middleware

3. **Rebuild required**: After adding the dependency:
   ```bash
   # Update lock file
   uv lock

   # Rebuild Docker containers
   docker compose build app
   docker compose up -d
   ```

4. **Verification**: Check that backend container starts successfully:
   ```bash
   docker ps --filter "name=backend"
   docker logs backend
   ```

### Files to Examine

- `pyproject.toml:11-41` - Add slowapi to dependencies list
- `src/middleware/rate_limit.py:7-9` - Confirms slowapi usage pattern
- `src/main.py:14` - Confirms slowapi import is required at startup

## Verification

**How to confirm the fix works:**

1. **Add dependency and rebuild**:
   ```bash
   cd /home/samuel/.archon/workspaces/project-manager
   # Edit pyproject.toml to add slowapi
   uv lock  # Update lock file
   docker compose build app
   docker compose up -d
   ```

2. **Expected outcome if fixed**:
   ```bash
   docker ps --filter "name=backend" --format "{{.Names}}\t{{.Status}}"
   # Should show: backend    Up X seconds (healthy)
   ```

3. **Verify no import errors**:
   ```bash
   docker logs backend
   # Should show FastAPI startup messages, not ModuleNotFoundError
   ```

4. **Test rate limiting functionality**:
   ```bash
   # Access any API endpoint and verify it responds
   curl http://localhost:8001/health
   # Should return 200 OK, not connection refused
   ```

## Summary

The backend container crashes immediately because commit `fe20dda` added rate limiting code using the `slowapi` library but forgot to add it to `pyproject.toml`. The fix is straightforward: add `"slowapi>=0.1.9"` to the dependencies list, rebuild the container, and verify startup succeeds.
