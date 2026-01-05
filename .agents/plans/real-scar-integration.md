# Feature: Real SCAR Integration - Replace Simulated Execution

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Replace the simulated SCAR execution in Project Manager with actual integration to SCAR's HTTP Test Adapter API. This enables PM to actually control SCAR and execute development commands instead of returning fake responses.

This is the CORE functionality of the Project Manager - enabling PM to actually communicate with SCAR, send commands, and receive real output from actual development operations.

## User Story

As a **non-technical user** interacting with Project Manager
I want PM to **actually control SCAR to execute development commands**
So that **my software projects are built with real code changes, not simulated responses**

## Problem Statement

Currently, PM simulates all SCAR command execution through `_simulate_scar_execution()` which returns hardcoded fake responses. Users think PM is building their project, but nothing is actually happening in SCAR. PM cannot fulfill its purpose as a project management agent because it has no way to actually control the underlying development automation system (SCAR).

## Solution Statement

Implement a real HTTP client that communicates with SCAR's Test Adapter API endpoints (`POST /test/message`, `GET /test/messages/:id`, `DELETE /test/messages/:id`). This allows PM to send commands to SCAR, receive actual output streaming, and track real execution status.

## Feature Metadata

**Feature Type**: Enhancement (replacing stub with real implementation)
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- SCAR executor service (`src/services/scar_executor.py`)
- SCAR client module (`src/scar/` - new)
- Database models (may need session/execution tracking updates)
- Configuration (`src/config.py`)

**Dependencies**:
- `httpx` (already in dependencies for async HTTP)
- SCAR instance running and accessible (environment configuration)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/services/scar_executor.py` (lines 1-264) - Why: Current simulated implementation that needs replacement
- `src/database/models.py` (lines 77-95) - Why: CommandType and ExecutionStatus enums, ScarCommandExecution model
- `src/config.py` - Why: Configuration patterns for environment variables
- `tests/services/test_scar_executor.py` (lines 1-160) - Why: Existing test patterns to maintain compatibility
- `pyproject.toml` (lines 1-84) - Why: Dependencies and project configuration

### New Files to Create

- `src/scar/client.py` - HTTP client for SCAR Test Adapter API
- `src/scar/types.py` - Type definitions for SCAR requests/responses
- `tests/unit/scar/test_client.py` - Unit tests for SCAR client
- `tests/integration/test_scar_integration.py` - Integration tests with real/mocked SCAR

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- **SCAR Test Adapter Documentation** (from SCAR's CLAUDE.md):
  - Test adapter endpoints: POST /test/message, GET /test/messages/:id, DELETE /test/messages/:id
  - Message format: `{"conversationId": "pm-project-{id}", "message": "/command-invoke {command} {args}"}`
  - Response format: `{"conversationId": "...", "messages": [{"message": "...", "timestamp": "...", "direction": "sent"}]}`

- **SCAR Command System** (from SCAR's CLAUDE.md):
  - Commands: `/command-invoke prime`, `/command-invoke plan-feature-github`, `/command-invoke execute-github`, `/command-invoke validate`
  - Commands expect natural language arguments after command name
  - Output streaming: SCAR may send multiple messages for a single command (progress updates)

### Patterns to Follow

**Naming Conventions:**
```python
# Snake case for functions and variables
async def execute_scar_command(session: AsyncSession, ...) -> CommandResult:
    pass

# PascalCase for classes
class ScarClient:
    pass

# SCREAMING_SNAKE_CASE for constants
SCAR_BASE_URL = "http://localhost:3000"
SCAR_TIMEOUT_SECONDS = 300
```

**Error Handling:**
```python
# From existing codebase pattern
try:
    # Execute operation
    result = await client.send_command(...)
except httpx.TimeoutException as e:
    # Log with context
    # Return structured error
    return CommandResult(
        success=False,
        output="",
        error=f"SCAR command timed out: {str(e)}",
        duration_seconds=duration
    )
except Exception as e:
    # Generic catch-all
    # Always log before returning
    # Return user-friendly error
    pass
```

**Async Patterns:**
```python
# Use async context managers for HTTP clients
async with httpx.AsyncClient(timeout=timeout) as client:
    response = await client.post(url, json=data)

# Always await database commits
await session.commit()
await session.refresh(execution)
```

**Configuration Pattern:**
```python
# From src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    scar_base_url: str = "http://localhost:3000"
    scar_timeout_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Configuration & Types)

Set up SCAR client configuration and type definitions before implementing actual HTTP communication.

**Tasks:**

1. **UPDATE** `src/config.py`
   - **IMPLEMENT**: Add SCAR configuration to Settings class
   - **FIELDS**: `scar_base_url`, `scar_timeout_seconds`, `scar_conversation_prefix`
   - **DEFAULTS**: `http://localhost:3000`, `300`, `pm-project-`
   - **VALIDATE**: Configuration loads from environment variables

2. **CREATE** `src/scar/types.py`
   - **IMPLEMENT**: Pydantic models for SCAR API types
   - **MODELS**: `ScarMessage`, `ScarMessageResponse`, `ScarMessagesResponse`
   - **PATTERN**: Use Pydantic BaseModel with type annotations
   - **VALIDATE**: `uv run python -c "from src.scar.types import ScarMessage; print('✓ Types valid')"`

### Phase 2: Core HTTP Client Implementation

Build the HTTP client that communicates with SCAR's Test Adapter API.

**Tasks:**

1. **CREATE** `src/scar/client.py`
   - **IMPLEMENT**: `ScarClient` class with async HTTP methods
   - **METHODS**:
     - `async send_command(project_id, command, args) -> str` - Send command, return conversationId
     - `async get_messages(conversation_id) -> list[ScarMessage]` - Fetch bot responses
     - `async clear_messages(conversation_id) -> None` - Clear conversation
     - `async wait_for_completion(conversation_id, timeout) -> list[ScarMessage]` - Poll until done
   - **IMPORTS**: `httpx`, `asyncio`, `src.config.Settings`, `src.scar.types`
   - **PATTERN**: Use async context manager for httpx.AsyncClient
   - **GOTCHA**: SCAR may send multiple messages per command (streaming) - aggregate all
   - **GOTCHA**: Conversation ID format is `pm-project-{uuid}` - ensure consistency
   - **VALIDATE**: `uv run python -c "from src.scar.client import ScarClient; print('✓ Client imports valid')"`

2. **IMPLEMENT** Message polling logic in `ScarClient`
   - **METHOD**: `async _poll_until_complete(conversation_id, timeout, poll_interval=2.0)`
   - **LOGIC**: Poll GET /test/messages/:id every 2 seconds until new messages stop appearing
   - **TIMEOUT**: Raise TimeoutError if no completion after `timeout` seconds
   - **COMPLETION DETECTION**: No new messages for 2 consecutive polls = done
   - **GOTCHA**: Don't poll too frequently (avoid hammering SCAR) - 2 second intervals

### Phase 3: Integration with Executor Service

Replace simulated execution with real SCAR client calls.

**Tasks:**

1. **UPDATE** `src/services/scar_executor.py`
   - **REMOVE**: `async def _simulate_scar_execution()` function (lines 146-202)
   - **ADD**: Import `ScarClient` from `src.scar.client`
   - **REPLACE**: In `execute_scar_command()`, replace simulation call with real client call
   - **PATTERN**:
     ```python
     # Build SCAR command string
     command_str = f"/command-invoke {command.value}"
     if args:
         # Quote args to handle spaces
         args_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in args)
         command_str += f" {args_str}"

     # Send to SCAR
     client = ScarClient(settings)
     conversation_id = await client.send_command(project_id, command_str)

     # Wait for completion
     messages = await client.wait_for_completion(conversation_id, timeout=settings.scar_timeout_seconds)

     # Aggregate output
     output = "\n".join(msg.message for msg in messages)
     ```
   - **IMPORTS**: `from src.scar.client import ScarClient`, `from src.config import get_settings`
   - **GOTCHA**: Handle SCAR connection errors gracefully (SCAR might not be running)
   - **VALIDATE**: `uv run python -c "from src.services.scar_executor import execute_scar_command; print('✓ Imports valid')"`

2. **ADD** Error handling for SCAR unavailability
   - **IMPLEMENT**: Catch `httpx.ConnectError` when SCAR is not running
   - **ERROR MESSAGE**: "SCAR is not available. Ensure SCAR is running at {base_url}"
   - **STATUS**: Mark execution as FAILED in database
   - **PATTERN**: Log error, update execution record, return CommandResult with error

### Phase 4: Testing & Validation

Comprehensive test coverage for real SCAR integration.

**Tasks:**

1. **CREATE** `tests/unit/scar/test_client.py`
   - **IMPLEMENT**: Unit tests for ScarClient using `respx` to mock HTTP
   - **TESTS**:
     - `test_send_command_success()` - Verify POST request format
     - `test_get_messages()` - Verify GET response parsing
     - `test_wait_for_completion_single_message()` - Simple case
     - `test_wait_for_completion_streaming()` - Multiple messages aggregated
     - `test_timeout_error()` - Polling exceeds timeout
     - `test_connection_error()` - SCAR not running
   - **PATTERN**: Use `respx` library for mocking HTTP (from project dependencies)
   - **VALIDATE**: `uv run pytest tests/unit/scar/test_client.py -v`

2. **CREATE** `tests/integration/test_scar_integration.py`
   - **IMPLEMENT**: Integration tests that verify PM ↔ SCAR communication flow
   - **TESTS**:
     - `test_execute_prime_with_mock_scar()` - End-to-end prime command
     - `test_execute_plan_with_mock_scar()` - End-to-end plan command
     - `test_scar_unavailable_handling()` - Graceful degradation
   - **PATTERN**: Use `respx` to mock SCAR responses realistically
   - **MOCK RESPONSES**: Return actual SCAR-like output (from SCAR's test patterns)
   - **VALIDATE**: `uv run pytest tests/integration/test_scar_integration.py -v`

3. **UPDATE** `tests/services/test_scar_executor.py`
   - **MODIFY**: Existing tests to work with real client (use `respx` mocking)
   - **ENSURE**: All existing tests still pass
   - **PATTERN**: Mock `ScarClient` methods in test fixtures
   - **VALIDATE**: `uv run pytest tests/services/test_scar_executor.py -v`

4. **CREATE** `.env.example` updates
   - **ADD**: SCAR configuration variables with comments
   - **EXAMPLE**:
     ```
     # SCAR Integration
     SCAR_BASE_URL=http://localhost:3000  # SCAR Test Adapter base URL
     SCAR_TIMEOUT_SECONDS=300  # Max wait time for SCAR command completion
     SCAR_CONVERSATION_PREFIX=pm-project-  # Conversation ID prefix
     ```

---

## TESTING STRATEGY

### Unit Tests

**Scope**: Test individual SCAR client methods in isolation

**Approach**:
- Use `respx` library to mock HTTP requests/responses
- Test all success paths and error conditions
- Verify correct request formatting and response parsing
- Mock time.sleep in polling tests to avoid delays

**Fixtures**:
```python
@pytest.fixture
def mock_scar_api(respx_mock):
    """Mock SCAR Test Adapter API"""
    # POST /test/message
    respx_mock.post("http://localhost:3000/test/message").mock(
        return_value=httpx.Response(200, json={"success": True, "conversationId": "pm-project-123"})
    )

    # GET /test/messages/:id
    respx_mock.get("http://localhost:3000/test/messages/pm-project-123").mock(
        return_value=httpx.Response(200, json={
            "conversationId": "pm-project-123",
            "messages": [
                {"message": "Primed successfully", "timestamp": "2024-01-01T00:00:00Z", "direction": "sent"}
            ]
        })
    )

    return respx_mock
```

### Integration Tests

**Scope**: Test full PM → SCAR → PM flow with mocked SCAR responses

**Approach**:
- Use database fixtures from conftest.py
- Mock SCAR API with realistic multi-message responses
- Test command execution, polling, and output aggregation
- Verify database execution records are created correctly

### Edge Cases

**Cases to test**:
1. SCAR returns empty message list (no output)
2. SCAR connection refused (not running)
3. SCAR timeout (command takes too long)
4. SCAR returns error in message content
5. Multiple PM projects calling SCAR concurrently (conversation ID isolation)
6. Network errors mid-polling (retry logic)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Import Validation (CRITICAL)

**Verify all imports resolve before running tests:**

```bash
uv run python -c "from src.main import app; print('✓ All imports valid')"
```

**Expected:** "✓ All imports valid" (no ModuleNotFoundError or ImportError)

**Why:** Catches incorrect package imports immediately. If this fails, fix imports before proceeding.

### Level 2: Syntax & Style

```bash
# Run Ruff linter
uv run ruff check src/ tests/

# Run Black formatter check
uv run black --check src/ tests/

# Type checking with mypy (if enabled)
uv run mypy src/
```

**Expected:** No linting errors, no formatting issues

### Level 3: Unit Tests

```bash
# Run all unit tests
uv run pytest tests/unit/ -v

# Run SCAR-specific tests
uv run pytest tests/unit/scar/ -v

# Run with coverage
uv run pytest tests/unit/ --cov=src.scar --cov-report=term-missing
```

**Expected:** All tests passing, 90%+ coverage on src.scar module

### Level 4: Integration Tests

```bash
# Run integration tests
uv run pytest tests/integration/ -v

# Run full test suite
uv run pytest tests/ -v --cov=src --cov-report=html
```

**Expected:** All tests passing, coverage report shows comprehensive coverage

### Level 5: Manual Validation

**Prerequisites:**
1. SCAR instance running on `http://localhost:3000` (or configured URL)
2. PostgreSQL database running
3. Environment variables configured

**Test Flow:**

```bash
# 1. Start PM API server
uv run python -m src.main

# 2. In another terminal, trigger SCAR command via PM API or Telegram
# (Use existing PM endpoints or create test script)

# 3. Verify in PM database that execution was tracked
psql $DATABASE_URL -c "SELECT * FROM scar_command_executions ORDER BY started_at DESC LIMIT 5;"

# 4. Check SCAR received the command
curl http://localhost:3000/test/messages/pm-project-{uuid}
```

**Expected:**
- PM successfully sends command to SCAR
- SCAR executes command and returns real output
- PM receives output and stores in database
- Execution record shows COMPLETED status with real output

### Level 6: Additional Validation (Optional)

**If MCP servers or additional CLI tools are available:**

```bash
# Test SCAR command manually
curl -X POST http://localhost:3000/test/message \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-manual","message":"/status"}'

# Retrieve response
curl http://localhost:3000/test/messages/test-manual | jq

# Cleanup
curl -X DELETE http://localhost:3000/test/messages/test-manual
```

---

## ACCEPTANCE CRITERIA

- [x] Feature implements actual HTTP communication with SCAR Test Adapter API
- [x] All validation commands pass with zero errors
- [x] Unit test coverage ≥ 90% for `src/scar/` module
- [x] Integration tests verify end-to-end PM → SCAR flow
- [x] Code follows project conventions (async patterns, error handling, type hints)
- [x] No regressions in existing `scar_executor` tests
- [x] Configuration properly loads SCAR settings from environment
- [x] Graceful error handling when SCAR is unavailable
- [x] Documentation updated (README.md, .env.example)
- [x] Manual testing confirms PM can actually control SCAR

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order (Phase 1 → Phase 4)
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms feature works with real SCAR instance
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability
- [ ] Pull request created with clear description

---

## NOTES

**Design Decisions:**

1. **HTTP vs Subprocess**: Chose HTTP Test Adapter API over subprocess CLI because:
   - SCAR is designed as a long-running service with HTTP endpoints
   - HTTP allows PM to run on different host than SCAR (future scalability)
   - Test Adapter is explicitly designed for programmatic integration
   - Cleaner error handling and output parsing

2. **Polling vs WebSockets**: Chose polling for MVP because:
   - SCAR Test Adapter doesn't currently expose WebSocket/SSE endpoints
   - Polling is simpler to implement and test
   - 2-second intervals are acceptable for command execution latency
   - Future enhancement: Add WebSocket support when SCAR provides it

3. **Conversation ID Format**: `pm-project-{uuid}` pattern ensures:
   - No conflicts with other SCAR users/platforms
   - Easy to trace PM-initiated commands in SCAR logs
   - UUID matches PM's project.id for consistency

4. **Timeout Strategy**: 300 second (5 minute) default timeout because:
   - SCAR plan-feature commands can take 2-3 minutes with research
   - SCAR execute commands can take 3-4 minutes for complex features
   - Configurable via env var for different use cases

**Trade-offs:**

- **Polling Overhead**: 2-second polling adds latency but ensures we don't miss messages
- **Blocking Execution**: Commands block until complete (vs background jobs) for MVP simplicity
- **Error Recovery**: No automatic retry logic yet - rely on user to re-invoke

**Future Enhancements:**

1. Add streaming response support (WebSocket/SSE when SCAR implements)
2. Background job processing for long-running commands
3. Retry logic with exponential backoff
4. Command queue for multiple concurrent projects
5. SCAR health check endpoint integration
6. Better progress tracking (parse SCAR's intermediate messages)

**Security Considerations:**

- SCAR Test Adapter has no authentication (designed for single-user local dev)
- In production, SCAR should be on same host/VPC as PM (not exposed to internet)
- Validate project ownership before sending commands to prevent SCAR abuse
- Sanitize command arguments to prevent injection attacks

**Performance Notes:**

- HTTP requests add ~50-100ms overhead vs direct function calls
- Polling every 2 seconds for average 30-second command = ~15 requests
- Keep-alive connections reduce overhead
- Consider connection pooling if PM scales to many concurrent projects
