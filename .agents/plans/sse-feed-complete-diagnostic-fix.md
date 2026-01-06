# Feature: SSE Feed Complete Diagnostic Fix

The following plan should be complete, but it's important that you validate documentation and codebase patterns before implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files.

## Feature Description

Fix the persistent SSE (Server-Sent Events) activity feed issue where users cannot see real-time SCAR command execution in the WebUI, despite:
- Backend logs showing successful SCAR executions
- Database records confirming ScarCommandExecution entries
- Previous fixes for timestamp comparison (PR #46) and event listeners (PR #48)

Issue #45 reports the problem persists even after these fixes, indicating a deeper integration issue between the PM agent, SCAR executor, SSE feed service, and frontend hooks.

## User Story

As a user of the Project Manager WebUI
I want to see real-time SCAR command execution activity streaming in the right pane
So that I can monitor what SCAR is doing as it analyzes code, creates plans, and implements features

## Problem Statement

**Current State:**
- User sends message: "analyze the codebase"
- PM agent responds with analysis results
- Right pane SSE feed remains completely EMPTY (no activity shown)
- Backend logs show SCAR execution: "Executing SCAR command: prime" → "SCAR command completed successfully"
- Database has ScarCommandExecution records with COMPLETED status

**Root Cause Hypothesis:**
Based on Issue #45 evidence and RCA report, the problem likely involves:
1. **Agent Tool Invocation**: PM may not consistently invoke execute_scar tool for analysis requests
2. **Database Transaction Isolation**: ScarCommandExecution records may not be visible to SSE polling query
3. **SSE Polling Logic**: Despite timestamp fix, polling may have race conditions or session isolation issues
4. **Frontend Connection**: EventSource may connect before initial activities exist, missing them entirely

**Critical Unknown:** Which component(s) in the chain are failing?

## Solution Statement

Implement comprehensive end-to-end diagnostic logging and targeted fixes:
1. Add detailed logging at EVERY integration point (agent → executor → database → SSE → frontend)
2. Create diagnostic script to validate database visibility and SSE query correctness
3. Fix identified issues in agent prompts, database sessions, or SSE polling logic
4. Add integration test that validates complete flow from agent tool call to frontend reception

## Feature Metadata

**Feature Type**: Bug Fix / Diagnostic Enhancement
**Estimated Complexity**: Medium-High
**Primary Systems Affected**:
- Agent orchestrator (`src/agent/orchestrator_agent.py`)
- Agent prompts (`src/agent/prompts.py`)
- SCAR executor service (`src/services/scar_executor.py`)
- SSE feed service (`src/services/scar_feed_service.py`)
- SSE API endpoint (`src/api/sse.py`)
- Frontend SSE hook (`frontend/src/hooks/useScarFeed.ts`)
- Database connection (`src/database/connection.py`)

**Dependencies**:
- `sse-starlette==2.1.0`
- `sqlalchemy[asyncio]>=2.0.36`
- `pydantic-ai>=0.0.14`
- `fastapi>=0.115.0`
- `asyncpg>=0.30.0`

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**Agent Layer:**
- `src/agent/orchestrator_agent.py` (lines 269-316) - execute_scar tool definition
  - **Why**: Validates tool is registered and callable
- `src/agent/prompts.py` (lines 1-99) - ORCHESTRATOR_SYSTEM_PROMPT
  - **Why**: Check if prompt guides agent to use execute_scar for "analyze" requests
- `src/agent/tools.py` - AgentDependencies and helper functions
  - **Why**: Understand dependency injection pattern

**Execution Layer:**
- `src/services/scar_executor.py` (lines 49-233) - execute_scar_command function
  - **Why**: Creates ScarCommandExecution, commits to DB, critical integration point
- `src/scar/client.py` - ScarClient implementation
  - **Why**: Understand SCAR API communication

**SSE Streaming Layer:**
- `src/services/scar_feed_service.py` (lines 71-149) - stream_scar_activity generator
  - **Why**: Polling logic that detects new activities (FIXED timestamp comparison in PR #46)
- `src/api/sse.py` (lines 22-104) - SSE endpoint
  - **Why**: EventSourceResponse implementation, session management

**Database Layer:**
- `src/database/models.py` (lines 248-301) - ScarCommandExecution model
  - **Why**: Understand @property methods for source, message, verbosity_level
- `src/database/connection.py` - async_session_maker configuration
  - **Why**: Check expire_on_commit setting and session isolation

**Frontend Layer:**
- `frontend/src/hooks/useScarFeed.ts` - EventSource hook
  - **Why**: Verify event listener for 'activity' events (FIXED in PR #48)
- `frontend/src/components/RightPanel/ScarActivityFeed.tsx` - Display component
  - **Why**: Understand rendering logic

### Recent Fixes (Already Applied)

**PR #46 (Commit d928ef6)**: Fixed SSE polling timestamp comparison
- **Problem**: Used UUID comparison (UUIDs not chronological)
- **Solution**: Changed to `started_at > last_dt`
- **Status**: ✅ Merged

**PR #48 (Commit 8d8ceb3)**: Fixed frontend event listener
- **Problem**: Listened for unnamed message events instead of named 'activity' events
- **Solution**: Added `eventSource.addEventListener('activity', ...)`
- **Status**: ✅ Merged

**PR #41 (Commit 00f82a5)**: Added direct SCAR execution tool
- **Feature**: Added execute_scar tool to orchestrator_agent
- **Status**: ✅ Merged

### Issue #45 Evidence

**User Report**:
- User: "analyze the codebase"
- PM responds with detailed analysis
- Right pane: COMPLETELY EMPTY

**Backend Logs (14:24)**:
```
2026-01-06 14:24:15 - Executing SCAR command: prime
2026-01-06 14:24:15 - SCAR command sent successfully
2026-01-06 14:24:21 - SCAR command completed successfully
```

**Database Query Result**:
```sql
SELECT started_at, command_type, status FROM scar_executions
WHERE project_id = '4d5457c9-4cd2-4bba-9b95-5fc84d3c126d'
ORDER BY started_at DESC LIMIT 3;

         started_at         | command_type |  status
----------------------------+--------------+-----------
 2026-01-06 14:34:34.704289 | PRIME        | COMPLETED  ✅
 2026-01-06 14:34:28.314875 | PRIME        | COMPLETED  ✅
 2026-01-06 14:24:36.036443 | PRIME        | COMPLETED  ✅
```

**Conclusion**: Data exists in database but SSE feed doesn't show it to user.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

**SSE Protocol:**
- [MDN EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
  - Section: Named events with addEventListener
  - **Why**: Validates frontend event listener pattern
- [sse-starlette Documentation](https://github.com/sysid/sse-starlette)
  - Section: Event generator pattern
  - **Why**: Confirms EventSourceResponse usage is correct

**SQLAlchemy Async:**
- [SQLAlchemy 2.0 Async Sessions](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#asyncio-session)
  - Section: Session isolation and expire_on_commit
  - **Why**: Understand transaction visibility and session lifecycle

**PydanticAI Tools:**
- [PydanticAI Documentation - Tools](https://ai.pydantic.dev/tools/)
  - Section: Tool registration and invocation
  - **Why**: Validate execute_scar tool is properly registered

### Patterns to Follow

**Logging Pattern** (from CLAUDE.md):
```python
logger.info(
    "Human-readable message",
    extra={"key1": value1, "key2": value2}
)
```

**Async Session Pattern** (from scar_executor.py):
```python
async with async_session_maker() as session:
    # Operations
    await session.commit()
    await session.refresh(obj)
```

**Error Handling Pattern** (from scar_executor.py):
```python
try:
    # Operation
    execution.status = ExecutionStatus.RUNNING
    await session.commit()
    # ... work ...
    execution.status = ExecutionStatus.COMPLETED
    await session.commit()
except SpecificError as e:
    logger.error("Context message", extra={"error": str(e)})
    execution.status = ExecutionStatus.FAILED
    await session.commit()
    return CommandResult(success=False, error=str(e), ...)
```

---

## IMPLEMENTATION PLAN

### Phase 1: Diagnostic Instrumentation

Add comprehensive logging to identify WHERE the chain breaks.

**Objective**: Log every step from agent tool call → database commit → SSE query → frontend reception

### Phase 2: Root Cause Identification

Run diagnostic script and analyze logs to pinpoint exact failure point.

**Objective**: Determine which component(s) are failing

### Phase 3: Targeted Fixes

Implement fixes based on Phase 2 findings.

**Objective**: Fix identified issues without breaking working components

### Phase 4: Integration Testing

Create end-to-end test that validates complete flow.

**Objective**: Prevent regression, ensure fix works for all SCAR commands

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute tasks sequentially. Each task has validation commands.

### Phase 1: Diagnostic Instrumentation

#### TASK 1: ADD diagnostic logging to orchestrator_agent execute_scar tool

- **FILE**: `src/agent/orchestrator_agent.py`
- **LOCATION**: Lines 269-316 (execute_scar tool function)
- **IMPLEMENT**: Add detailed logging BEFORE and AFTER execute_scar_command call
- **PATTERN**: Use logger.info with extra dict (line 308 already has pattern)
- **CODE**:
```python
@orchestrator_agent.tool
async def execute_scar(
    ctx: RunContext[AgentDependencies], command: str, args: list[str] | None = None
) -> dict:
    # ... existing docstring ...

    # ADD: Log tool invocation
    logger.info(
        "🔧 DIAGNOSTIC: execute_scar tool INVOKED",
        extra={
            "project_id": str(ctx.deps.project_id),
            "command": command,
            "args": args,
            "session_id": id(ctx.deps.session)
        }
    )

    # ... existing validation ...

    # ADD: Log before executor call
    logger.info(
        "📞 DIAGNOSTIC: Calling execute_scar_command service",
        extra={
            "project_id": str(ctx.deps.project_id),
            "scar_command": scar_cmd.value
        }
    )

    result = await execute_scar_command(ctx.deps.session, ctx.deps.project_id, scar_cmd, args or [])

    # ADD: Log after executor call
    logger.info(
        "✅ DIAGNOSTIC: execute_scar_command returned",
        extra={
            "project_id": str(ctx.deps.project_id),
            "success": result.success,
            "duration": result.duration_seconds
        }
    )

    return { ... }
```
- **VALIDATE**: `uv run python -c "from src.agent.orchestrator_agent import execute_scar; print('✓ Tool imports correctly')"`

#### TASK 2: ADD diagnostic logging to scar_executor.execute_scar_command

- **FILE**: `src/services/scar_executor.py`
- **LOCATION**: Lines 49-233 (execute_scar_command function)
- **IMPLEMENT**: Add logging for database operations
- **CODE**:
```python
async def execute_scar_command(...) -> CommandResult:
    # ... existing project fetch ...

    # AFTER line 93 (session.add(execution)):
    logger.info(
        "💾 DIAGNOSTIC: ScarCommandExecution created (NOT YET COMMITTED)",
        extra={
            "execution_id": str(execution.id),
            "project_id": str(project_id),
            "command": command.value,
            "status": execution.status.value
        }
    )

    await session.commit()

    # ADD: After commit
    logger.info(
        "✅ DIAGNOSTIC: ScarCommandExecution COMMITTED to database",
        extra={
            "execution_id": str(execution.id),
            "project_id": str(project_id),
            "started_at": execution.started_at.isoformat() if execution.started_at else None
        }
    )

    await session.refresh(execution)

    # ... rest of execution ...

    # AFTER line 138 (execution.output = output):
    logger.info(
        "💾 DIAGNOSTIC: Updating execution to COMPLETED (NOT YET COMMITTED)",
        extra={
            "execution_id": str(execution.id),
            "status": ExecutionStatus.COMPLETED.value
        }
    )

    await session.commit()

    # ADD: After final commit
    logger.info(
        "✅ DIAGNOSTIC: Execution COMPLETED and COMMITTED",
        extra={
            "execution_id": str(execution.id),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None
        }
    )
```
- **VALIDATE**: `uv run python -c "from src.services.scar_executor import execute_scar_command; print('✓ Imports correctly')"`

#### TASK 3: ADD diagnostic logging to SSE feed service polling

- **FILE**: `src/services/scar_feed_service.py`
- **LOCATION**: Lines 71-149 (stream_scar_activity function)
- **IMPLEMENT**: Log every poll cycle and query results
- **CODE**:
```python
async def stream_scar_activity(...) -> AsyncGenerator[Dict, None]:
    logger.info(f"Starting SCAR activity stream for project {project_id}")

    last_timestamp = None

    # Get initial activities
    activities = await get_recent_scar_activity(...)

    # ADD: Log initial load
    logger.info(
        "📊 DIAGNOSTIC: Initial activities loaded",
        extra={
            "project_id": str(project_id),
            "count": len(activities),
            "last_timestamp": activities[-1]["timestamp"] if activities else None
        }
    )

    if activities:
        last_timestamp = activities[-1]["timestamp"]
        for activity in activities:
            yield activity

    # Poll for new activities
    while True:
        await asyncio.sleep(2)

        # ADD: Log poll cycle
        logger.debug(
            "🔄 DIAGNOSTIC: Polling for new activities",
            extra={
                "project_id": str(project_id),
                "last_timestamp": last_timestamp
            }
        )

        # ... existing query ...

        result = await session.execute(query)
        new_activities = result.scalars().all()

        # ADD: Log query results
        if new_activities:
            logger.info(
                "🆕 DIAGNOSTIC: New activities detected",
                extra={
                    "project_id": str(project_id),
                    "count": len(new_activities),
                    "new_ids": [str(a.id) for a in new_activities]
                }
            )

        for activity in new_activities:
            # ... existing serialization ...

            # ADD: Log before yield
            logger.info(
                "📤 DIAGNOSTIC: Yielding activity to SSE stream",
                extra={
                    "execution_id": str(activity.id),
                    "timestamp": activity_dict["timestamp"]
                }
            )

            last_timestamp = activity_dict["timestamp"]
            yield activity_dict
```
- **VALIDATE**: `uv run python -c "from src.services.scar_feed_service import stream_scar_activity; print('✓ Imports correctly')"`

#### TASK 4: ADD diagnostic logging to SSE endpoint

- **FILE**: `src/api/sse.py`
- **LOCATION**: Lines 22-104 (sse_scar_activity endpoint)
- **IMPLEMENT**: Log connection lifecycle
- **CODE**:
```python
@router.get("/sse/scar/{project_id}")
async def sse_scar_activity(...):
    logger.info(f"SSE connection established for project {project_id} (verbosity: {verbosity})")

    async def event_generator():
        try:
            async with async_session_maker() as session:
                # ADD: Log session creation
                logger.info(
                    "🔌 DIAGNOSTIC: SSE session created",
                    extra={
                        "project_id": str(project_id),
                        "session_id": id(session),
                        "verbosity": verbosity
                    }
                )

                activity_stream = stream_scar_activity(session, project_id, verbosity_level=verbosity)

                # ... existing heartbeat tracking ...

                try:
                    async for activity in activity_stream:
                        # ADD: Log before send
                        logger.debug(
                            "📡 DIAGNOSTIC: Sending SSE event to client",
                            extra={
                                "project_id": str(project_id),
                                "activity_id": activity.get("id"),
                                "message": activity.get("message")[:50] if activity.get("message") else None
                            }
                        )

                        yield {"event": "activity", "data": json.dumps(activity)}

                        # ... existing heartbeat logic ...
```
- **VALIDATE**: `uv run python -c "from src.api.sse import router; print('✓ SSE router imports correctly')"`

#### TASK 5: CREATE diagnostic script to validate database visibility

- **FILE**: `scripts/diagnose_sse_feed.py` (NEW FILE)
- **IMPLEMENT**: Script that simulates SSE polling and validates query results
- **CODE**:
```python
"""
Diagnostic script to validate SSE feed database queries.

Usage:
    uv run python scripts/diagnose_sse_feed.py <project_id>
"""
import asyncio
import sys
from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, select

from src.database.connection import async_session_maker
from src.database.models import ScarCommandExecution


async def diagnose_sse_feed(project_id: UUID):
    """Run diagnostic checks on SSE feed database queries."""

    print(f"🔍 Diagnosing SSE feed for project {project_id}\n")

    async with async_session_maker() as session:
        # Check 1: Total executions
        query = select(ScarCommandExecution).where(
            ScarCommandExecution.project_id == project_id
        )
        result = await session.execute(query)
        all_executions = result.scalars().all()

        print(f"✅ Total ScarCommandExecution records: {len(all_executions)}")

        if not all_executions:
            print("❌ No executions found for this project!")
            return

        # Check 2: Recent executions (what SSE should show initially)
        recent_query = (
            select(ScarCommandExecution)
            .where(ScarCommandExecution.project_id == project_id)
            .order_by(desc(ScarCommandExecution.started_at))
            .limit(10)
        )
        result = await session.execute(recent_query)
        recent = result.scalars().all()

        print(f"\n📊 Recent 10 executions (ordered by started_at DESC):")
        for i, exec in enumerate(recent, 1):
            print(f"  {i}. {exec.id} | {exec.started_at} | {exec.command_type.value} | {exec.status.value}")

        # Check 3: Simulate polling query (timestamp comparison)
        if recent:
            last_timestamp = recent[-1].started_at
            print(f"\n🔄 Simulating SSE polling query (activities AFTER {last_timestamp}):")

            poll_query = (
                select(ScarCommandExecution)
                .where(
                    ScarCommandExecution.project_id == project_id,
                    ScarCommandExecution.started_at > last_timestamp
                )
                .order_by(ScarCommandExecution.started_at.asc())
            )
            result = await session.execute(poll_query)
            newer = result.scalars().all()

            if newer:
                print(f"  ✅ Found {len(newer)} activities newer than {last_timestamp}")
                for exec in newer:
                    print(f"    - {exec.id} | {exec.started_at} | {exec.command_type.value}")
            else:
                print(f"  ℹ️  No activities newer than {last_timestamp}")

        # Check 4: Validate @property methods
        print(f"\n🏷️  Validating ScarCommandExecution @property methods:")
        test_exec = recent[0]
        print(f"  - source: {test_exec.source}")
        print(f"  - message: {test_exec.message[:50]}..." if test_exec.message else "None")
        print(f"  - verbosity_level: {test_exec.verbosity_level}")

        # Check 5: Session isolation check
        print(f"\n🔒 Session isolation check:")
        print(f"  - Session ID: {id(session)}")
        print(f"  - expire_on_commit: {session.expire_on_commit}")

        print("\n✅ Diagnostic complete!")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/diagnose_sse_feed.py <project_id>")
        sys.exit(1)

    project_id = UUID(sys.argv[1])
    asyncio.run(diagnose_sse_feed(project_id))
```
- **VALIDATE**: `uv run python -c "import scripts.diagnose_sse_feed; print('✓ Script imports correctly')"`

### Phase 2: Root Cause Identification

#### TASK 6: RUN diagnostic script and collect logs

- **EXECUTE**:
```bash
# Get a project ID from database
uv run python -c "import asyncio; from src.database.connection import async_session_maker; from sqlalchemy import select; from src.database.models import Project; async def get_id(): async with async_session_maker() as s: r = await s.execute(select(Project).limit(1)); p = r.scalar_one_or_none(); print(p.id if p else 'NO PROJECTS'); asyncio.run(get_id())"

# Run diagnostic with that project ID
uv run python scripts/diagnose_sse_feed.py <project_id>
```
- **ANALYZE**: Review output to validate:
  - [ ] Database has ScarCommandExecution records
  - [ ] Timestamp comparison query returns expected results
  - [ ] @property methods work correctly
  - [ ] Session isolation settings are correct

#### TASK 7: TRIGGER SCAR execution and monitor logs

- **EXECUTE**:
```bash
# Start backend with debug logging
export LOG_LEVEL=DEBUG
uv run uvicorn src.main:app --reload --port 8000 &

# Monitor logs in real-time
tail -f logs/app.log | grep DIAGNOSTIC
```
- **TEST**: Via WebUI or API, send message "analyze the codebase"
- **OBSERVE**: Check for each diagnostic log:
  - [ ] 🔧 execute_scar tool INVOKED
  - [ ] 📞 Calling execute_scar_command service
  - [ ] 💾 ScarCommandExecution created
  - [ ] ✅ ScarCommandExecution COMMITTED
  - [ ] ✅ Execution COMPLETED and COMMITTED
  - [ ] 📊 Initial activities loaded (SSE connection)
  - [ ] 🆕 New activities detected (SSE polling)
  - [ ] 📤 Yielding activity to SSE stream
  - [ ] 📡 Sending SSE event to client

#### TASK 8: IDENTIFY failure point from diagnostic logs

- **ANALYZE**: Based on which diagnostic logs appear vs missing, determine failure point:
  - **Missing 🔧 tool INVOKED**: Agent not calling execute_scar → Fix prompts
  - **Missing 💾 COMMITTED**: Database transaction failing → Fix executor
  - **Missing 🆕 New activities detected**: SSE query not finding records → Fix polling query or session isolation
  - **Missing 📡 Sending SSE event**: Generator not yielding → Fix stream logic
  - **All logs present but frontend empty**: Frontend issue → Fix EventSource
- **DOCUMENT**: Create `.agents/diagnostics/sse-feed-failure-point.txt` with findings

### Phase 3: Targeted Fixes

#### TASK 9: FIX identified issues (conditional on Phase 2 findings)

**If agent not calling tool:**

- **FILE**: `src/agent/prompts.py`
- **UPDATE**: Line 49 (exception for "analyze codebase")
- **CHANGE**: Make it more explicit
```python
- Exception: If user says "analyze the codebase" or similar → call execute_scar("prime")
+ Exception: If user says "analyze the codebase", "analyze", "prime", "load codebase" → IMMEDIATELY call execute_scar("prime") without asking
```

**If database session isolation:**

- **FILE**: `src/database/connection.py`
- **CHECK**: expire_on_commit setting
- **FIX**: Ensure `expire_on_commit=False` for SSE sessions
```python
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # ✅ Must be False for SSE to work
)
```

**If SSE polling query:**

- **FILE**: `src/services/scar_feed_service.py`
- **UPDATE**: Line 116 query (already fixed in PR #46, but validate it's correct)
- **VALIDATE**: Ensure using `started_at > last_dt` not `id > last_id`

**If frontend EventSource:**

- **FILE**: `frontend/src/hooks/useScarFeed.ts`
- **UPDATE**: Line 24 (already fixed in PR #48, but validate)
- **VALIDATE**: Ensure using `addEventListener('activity', ...)` not `onmessage`

#### TASK 10: ADD database commit flush to ensure visibility

- **FILE**: `src/services/scar_executor.py`
- **UPDATE**: After line 94 (await session.commit())
- **ADD**: Explicit flush to ensure immediate visibility
```python
await session.commit()
await session.flush()  # Ensure immediately visible to other sessions
```
- **RATIONALE**: Some async session configurations may buffer commits
- **VALIDATE**: `uv run python -c "from src.services.scar_executor import execute_scar_command; print('✓')"`

### Phase 4: Integration Testing

#### TASK 11: CREATE integration test for complete SSE flow

- **FILE**: `tests/integration/test_sse_feed_integration.py` (NEW FILE)
- **IMPLEMENT**: End-to-end test from agent tool call to SSE stream reception
- **PATTERN**: Mirror existing test patterns from `tests/services/test_scar_executor.py`
- **CODE**:
```python
"""
Integration test for SSE feed end-to-end flow.

Tests the complete chain:
1. Agent calls execute_scar tool
2. ScarCommandExecution created in database
3. SSE feed service detects new execution
4. SSE endpoint streams event to client
"""
import asyncio
import json

import pytest
from pydantic_ai import RunContext

from src.agent.orchestrator_agent import execute_scar
from src.agent.tools import AgentDependencies
from src.database.models import Project, ProjectStatus
from src.services.scar_feed_service import stream_scar_activity


@pytest.mark.asyncio
async def test_sse_feed_shows_scar_execution(db_session):
    """Test that SCAR execution appears in SSE feed within 5 seconds."""

    # 1. Create test project
    project = Project(
        name="SSE Test Project",
        status=ProjectStatus.PLANNING,
        github_repo_url="https://github.com/test/repo"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # 2. Call execute_scar tool (simulating agent invocation)
    deps = AgentDependencies(session=db_session, project_id=project.id)

    # Mock RunContext
    class MockRunContext:
        def __init__(self, deps):
            self.deps = deps

    ctx = MockRunContext(deps)

    # Execute PRIME command via tool
    result = await execute_scar(ctx, command="prime", args=None)

    assert result["success"] is True, f"SCAR execution failed: {result.get('error')}"

    # 3. Verify ScarCommandExecution was created
    from src.database.models import ScarCommandExecution
    from sqlalchemy import select

    query = select(ScarCommandExecution).where(
        ScarCommandExecution.project_id == project.id
    )
    db_result = await db_session.execute(query)
    executions = db_result.scalars().all()

    assert len(executions) > 0, "No ScarCommandExecution records found after execute_scar"

    # 4. Create SSE stream (simulating SSE endpoint)
    activity_stream = stream_scar_activity(db_session, project.id, verbosity_level=2)

    # 5. Collect activities from stream (with timeout)
    activities = []

    async def collect_activities():
        async for activity in activity_stream:
            activities.append(activity)
            if len(activities) >= len(executions):
                break

    try:
        await asyncio.wait_for(collect_activities(), timeout=5.0)
    except asyncio.TimeoutError:
        pytest.fail(f"SSE stream did not yield activities within 5 seconds. Got {len(activities)}/{len(executions)}")

    # 6. Validate activities match executions
    assert len(activities) == len(executions), \
        f"SSE stream yielded {len(activities)} activities but {len(executions)} executions exist"

    # Validate activity structure
    first_activity = activities[0]
    assert "id" in first_activity
    assert "timestamp" in first_activity
    assert "source" in first_activity
    assert "message" in first_activity
    assert first_activity["source"] == "scar"
```
- **VALIDATE**: `uv run pytest tests/integration/test_sse_feed_integration.py -v`

#### TASK 12: RUN full test suite

- **EXECUTE**:
```bash
# Run all tests
uv run pytest tests/ -v

# Check coverage
uv run pytest tests/ --cov=src --cov-report=term-missing
```
- **EXPECTED**: All tests pass, including new integration test
- **VALIDATE**: Coverage ≥ 80% for modified files

---

## TESTING STRATEGY

### Level 1: Import Validation (CRITICAL)

**Verify all imports resolve:**
```bash
uv run python -c "from src.agent.orchestrator_agent import execute_scar; from src.services.scar_executor import execute_scar_command; from src.services.scar_feed_service import stream_scar_activity; from src.api.sse import router; print('✓ All imports valid')"
```
**Expected**: "✓ All imports valid"

### Level 2: Unit Tests

**Test individual components:**
```bash
uv run pytest tests/services/test_scar_executor.py -v
uv run pytest tests/agent/test_orchestrator_agent.py -v
```
**Expected**: All existing tests continue to pass

### Level 3: Integration Tests

**Test end-to-end SSE flow:**
```bash
uv run pytest tests/integration/test_sse_feed_integration.py -v
```
**Expected**: New integration test passes, validates complete flow

### Level 4: Manual Validation

**Test in live environment:**

1. Start backend: `uv run uvicorn src.main:app --reload --port 8000`
2. Open WebUI at http://localhost:3000
3. Send message: "analyze the codebase"
4. **VERIFY**:
   - [ ] PM responds with analysis
   - [ ] Right pane SSE feed shows "prime" activity within 2 seconds
   - [ ] Activity includes timestamp, source="scar", message
5. Check backend logs for all DIAGNOSTIC messages
6. Run diagnostic script: `uv run python scripts/diagnose_sse_feed.py <project_id>`

### Level 5: Diagnostic Script

**Validate database queries:**
```bash
# Get project ID
PROJECT_ID=$(uv run python -c "import asyncio; from src.database.connection import async_session_maker; from sqlalchemy import select; from src.database.models import Project; async def get_id(): async with async_session_maker() as s: r = await s.execute(select(Project).limit(1)); p = r.scalar_one_or_none(); print(p.id if p else ''); asyncio.run(get_id())")

# Run diagnostic
uv run python scripts/diagnose_sse_feed.py $PROJECT_ID
```
**Expected**: Script shows executions, query results, @property values

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Import Validation (CRITICAL)
```bash
uv run python -c "from src.agent.orchestrator_agent import execute_scar; from src.services.scar_executor import execute_scar_command; from src.services.scar_feed_service import stream_scar_activity; from src.api.sse import router; print('✓ All imports valid')"
```

### Level 2: Syntax & Style
```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
```

### Level 3: Unit Tests
```bash
uv run pytest tests/services/test_scar_executor.py -v
uv run pytest tests/agent/ -v
uv run pytest tests/ -v --maxfail=1
```

### Level 4: Integration Tests
```bash
uv run pytest tests/integration/test_sse_feed_integration.py -v
```

### Level 5: Diagnostic Validation
```bash
PROJECT_ID=$(uv run python -c "import asyncio; from src.database.connection import async_session_maker; from sqlalchemy import select; from src.database.models import Project; async def get_id(): async with async_session_maker() as s: r = await s.execute(select(Project).limit(1)); p = r.scalar_one_or_none(); print(p.id if p else ''); asyncio.run(get_id())")
uv run python scripts/diagnose_sse_feed.py $PROJECT_ID
```

### Level 6: Manual E2E Test
```bash
# Terminal 1: Start backend with debug logging
export LOG_LEVEL=DEBUG
uv run uvicorn src.main:app --reload --port 8000

# Terminal 2: Monitor diagnostic logs
tail -f logs/app.log | grep DIAGNOSTIC

# Terminal 3: Start frontend (if applicable)
cd frontend && npm run dev

# Browser: Open http://localhost:3000, send "analyze the codebase", verify SSE feed populates
```

---

## ACCEPTANCE CRITERIA

- [ ] Diagnostic logging captures every integration point (agent → executor → DB → SSE → frontend)
- [ ] Diagnostic script validates database queries work correctly
- [ ] Root cause identified and documented in `.agents/diagnostics/sse-feed-failure-point.txt`
- [ ] Targeted fixes implemented based on diagnostic findings
- [ ] Integration test validates complete SSE flow from tool call to stream
- [ ] All unit tests pass (no regressions)
- [ ] Manual testing shows SSE feed populates within 2 seconds of SCAR execution
- [ ] Backend logs show all DIAGNOSTIC checkpoints when user triggers SCAR command
- [ ] Frontend receives and displays activities in real-time
- [ ] Issue #45 reproduction scenario now works correctly

---

## COMPLETION CHECKLIST

- [ ] Phase 1 complete: All diagnostic logging added
- [ ] Phase 2 complete: Root cause identified via diagnostics
- [ ] Phase 3 complete: Targeted fixes implemented
- [ ] Phase 4 complete: Integration test created and passing
- [ ] All validation commands executed successfully
- [ ] Manual E2E test confirms SSE feed works
- [ ] Diagnostic script runs without errors
- [ ] Code reviewed for quality and maintainability
- [ ] No linting or type checking errors
- [ ] Backend logs show complete diagnostic flow
- [ ] Issue #45 marked as resolved

---

## NOTES

**Why Diagnostic-First Approach:**
- Issue #45 persists despite 2 targeted fixes (PR #46, #48)
- Indicates problem is NOT where we think it is
- Comprehensive logging will reveal actual failure point
- Prevents more guesswork fixes that don't solve root cause

**Why Integration Test:**
- Unit tests alone missed this issue
- Need end-to-end validation from agent tool call to SSE reception
- Test acts as regression prevention for future changes

**Potential Root Causes (to investigate):**
1. Agent prompt doesn't trigger execute_scar for "analyze" requests
2. Database session isolation prevents SSE from seeing committed records
3. Race condition: SSE connects BEFORE first execution, polls miss timing
4. Frontend EventSource reconnection resets last_timestamp incorrectly
5. SQLAlchemy session caching returns stale results

**Success Metric:** User sends "analyze the codebase" → SSE feed shows activity within 2 seconds
