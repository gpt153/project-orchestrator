# Feature: Stream Detailed SCAR Execution Output to SSE Feed

The following plan should be complete, but it's important that you validate documentation and codebase patterns before implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files etc.

## Feature Description

Transform the SSE (Server-Sent Events) activity feed to display detailed, real-time SCAR execution output similar to Claude Code CLI's verbose mode. Currently, the feed shows only high-level status updates (e.g., "PRIME: COMPLETED"). The enhanced feed will stream granular execution details including:

- Individual bash commands executed with their parameters and output
- File read operations with file paths
- Glob pattern searches and matching file lists
- Grep operations with search patterns and match counts
- Edit operations showing files being modified
- Tool invocation sequences with full parameters
- Progress indicators during long-running operations
- Error details and stack traces when operations fail

This provides users with full transparency into SCAR's execution, matching the detailed output experience of Claude Code CLI.

## User Story

As a Project Manager WebUI user
I want to see detailed, step-by-step SCAR execution output in the SSE activity feed
So that I can understand exactly what operations SCAR is performing (bash commands, file reads, searches, etc.) and monitor real-time progress like Claude Code CLI shows

## Problem Statement

**Current Behavior:**
- SSE feed shows only coarse-grained status: "PRIME: RUNNING" → "PRIME: COMPLETED"
- No visibility into individual tool invocations (bash, file reads, grep, glob, edit)
- SCAR output is stored as a monolithic text blob in `ScarCommandExecution.output`
- Users cannot see what SCAR is actually doing during execution
- No progress indicators during long operations (prime, validate)
- Recent attempt (commit 06ca5d0) split output by lines but didn't parse tool types

**Root Cause:**
- `ScarClient.wait_for_completion()` polls SCAR API every 2 seconds and returns all messages at end
- `execute_scar_command()` simply joins all message text with newlines: `"\n".join(msg.message for msg in messages)`
- `scar_feed_service.py` tries to split output by lines but has no structured activity data
- No parsing of SCAR message content to extract individual tool invocations

**Desired Behavior:**
- SSE feed shows every tool invocation as it happens (Bash, Read, Grep, Glob, Edit)
- Real-time streaming of command execution output (<1s latency from SCAR to UI)
- File operations visible with paths and snippets
- Search operations show patterns and match counts
- Structured activity data (type, command, parameters, output)
- Users get Claude Code CLI-level execution transparency

## Solution Statement

Implement a **message parsing and real-time streaming architecture** that:

1. **Enhanced SCAR Polling**: Increase poll frequency from 2s to 0.5s, stream messages incrementally during execution
2. **Message Parsing Service**: Parse SCAR message text to extract individual tool invocations using regex patterns
3. **Activity Storage**: Create `ScarActivity` model to store granular operations with type, details, output
4. **Real-time Streaming**: Stream parsed activities to SSE feed as they're detected (not batch at end)
5. **Frontend Enhancement**: Display activities with operation-specific icons and collapsible output

**Key Constraint**: SCAR Test Adapter API does NOT support native streaming (WebSocket/SSE). It uses HTTP polling (`GET /test/messages/:id`) that returns accumulated messages. Therefore we must:
- Poll more frequently (0.5s vs 2s) to reduce latency
- Parse accumulated text to extract individual operations
- Stream parsed operations incrementally to SSE clients
- Infer operation types from message text patterns (regex)

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: High
**Primary Systems Affected**:
- SCAR client polling (`src/scar/client.py`)
- SCAR message parsing (NEW: `src/scar/message_parser.py`)
- Database models (`src/database/models.py` - new `ScarActivity` table)
- SCAR executor (`src/services/scar_executor.py`)
- SSE feed service (`src/services/scar_feed_service.py`)
- SSE API endpoint (`src/api/sse.py`)

**Dependencies**:
- `sse-starlette==2.1.0` (existing)
- `sqlalchemy[asyncio]>=2.0.36` (existing)
- `pydantic>=2.10.0` (existing)
- `httpx>=0.28.0` (existing)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**SCAR Integration Layer:**
- `src/scar/client.py` (lines 213-289) - **Why**: Polling logic (`wait_for_completion`), currently 2s interval, need to add incremental streaming
- `src/scar/types.py` (complete) - **Why**: `ScarMessage` structure with `message`, `timestamp`, `direction` fields
- `src/services/scar_executor.py` (lines 98-156) - **Why**: Command execution flow, where polling happens and output is aggregated

**SSE Streaming Layer:**
- `src/services/scar_feed_service.py` (lines 67-84, 90-149) - **Why**: Current polling-based streaming, naive line splitting at verbosity >= 2
- `src/api/sse.py` (lines 22-104) - **Why**: SSE endpoint, EventSourceResponse configuration, event format

**Database Layer:**
- `src/database/models.py` (lines 248-301) - **Why**: `ScarCommandExecution` model, need to add `ScarActivity` model after it
- `src/database/connection.py` - **Why**: Async session configuration

**Testing Patterns:**
- `tests/services/test_scar_executor.py` - **Why**: Test patterns for async command execution with mocked SCAR
- `tests/unit/scar/test_client.py` - **Why**: Test patterns for SCAR client polling

### New Files to Create

- `src/scar/message_parser.py` - Message parsing service to extract tool invocations from SCAR text
- `src/database/migrations/versions/XXX_add_scar_activity_table.py` - Alembic migration for `scar_activities` table
- `tests/scar/test_message_parser.py` - Unit tests for message parser with various message formats

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

**External Documentation:**
- [Server-Sent Events API](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
  - Section: Event stream format, named events
  - **Why**: Required for proper SSE event structuring
- [sse-starlette Documentation](https://github.com/sysid/sse-starlette)
  - Section: EventSourceResponse usage, event formatting
  - **Why**: Library-specific streaming patterns

**Project Documentation:**
- `.agents/reference/database-schema.md` - Database schema conventions
- `.agents/plans/enhance-sse-detailed-output.md` - Previous detailed planning (reference for context)

### Patterns to Follow

**Error Handling Pattern** (from `src/services/scar_executor.py:158-233`):
```python
try:
    # Execute operation
    result = await operation()
except httpx.ConnectError as e:
    logger.error(f"SCAR connection failed: {e}")
    execution.status = ExecutionStatus.FAILED
    await session.commit()
    return CommandResult(success=False, error="SCAR not available", ...)
except TimeoutError as e:
    logger.error(f"Operation timed out: {e}")
    execution.status = ExecutionStatus.FAILED
except Exception as e:
    logger.error(f"Unexpected error: {e}", extra={"error_type": type(e).__name__})
```

**Logging Pattern** (from `src/services/scar_executor.py:108-111`):
```python
logger.info(
    "Executing SCAR command: {command.value}",
    extra={"project_id": str(project_id), "command": command.value}
)
```

**Database Timestamp Comparison** (from `src/services/scar_feed_service.py:130-138`):
```python
last_dt = datetime.fromisoformat(last_timestamp)
query = (
    select(ScarCommandExecution)
    .where(
        ScarCommandExecution.project_id == project_id,
        ScarCommandExecution.started_at > last_dt,
    )
    .order_by(ScarCommandExecution.started_at.asc())
)
```

**SSE Event Format** (from `src/api/sse.py:68-80`):
```python
# Named event with JSON data
yield {
    "event": "activity",
    "data": json.dumps({
        "id": str(activity.id),
        "timestamp": activity.timestamp.isoformat(),
        "source": "scar",
        "message": "Executing bash command",
        "phase": activity.phase
    })
}

# Heartbeat event
yield {
    "event": "heartbeat",
    "data": json.dumps({"status": "alive", "timestamp": datetime.utcnow().isoformat()})
}
```

**Naming Conventions:**
- **Functions**: `snake_case` (e.g., `parse_message`, `extract_tool_calls`)
- **Classes**: `PascalCase` (e.g., `ScarMessageParser`, `ActivityEvent`)
- **Enums**: `PascalCase` class, `UPPER_SNAKE_CASE` values (e.g., `ActivityType.BASH_COMMAND`)
- **Database Models**: `PascalCase` (e.g., `ScarActivity`)
- **Database Tables**: `snake_case` (e.g., `scar_activities`)

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation - Message Parsing Service

Create the core message parsing infrastructure to extract tool invocations from SCAR message text.

**Tasks:**
- Design `ActivityType` enum for different operation types (bash, read, grep, glob, edit, etc.)
- Create `ActivityEvent` Pydantic model for parsed activities
- Implement `ScarMessageParser` class with regex patterns for each tool type
- Write comprehensive unit tests for parser with various message formats

### Phase 2: Database Schema Enhancement

Add database support for storing granular activities.

**Tasks:**
- Create `ScarActivity` model in `src/database/models.py`
- Add relationship to `ScarCommandExecution` (one-to-many)
- Create Alembic migration to add `scar_activities` table
- Add indexes for efficient querying (execution_id, project_id + timestamp)

### Phase 3: Enhanced SCAR Polling

Modify SCAR client to poll more frequently and stream messages incrementally during execution.

**Tasks:**
- Reduce `wait_for_completion()` poll interval from 2s to 0.5s
- Add `stream_messages_incremental()` method that yields new messages as they arrive
- Update typing imports to support `AsyncGenerator`
- Test polling behavior with mocked SCAR responses

### Phase 4: Integrated Parsing and Storage

Integrate message parsing with command execution and database storage.

**Tasks:**
- Update `execute_scar_command()` to use incremental streaming instead of batch wait
- Parse each new message and create `ScarActivity` records
- Commit activities immediately (not batched) for SSE feed to pick up
- Maintain backward compatibility (still aggregate full output text)

### Phase 5: Real-time SSE Streaming

Update SSE feed service to stream detailed activities in real-time.

**Tasks:**
- Modify `stream_scar_activity()` to query both `ScarCommandExecution` and `ScarActivity`
- Reduce SSE polling from 2s to 0.5s to match SCAR polling
- Add verbosity filtering (level 3 = detailed activities)
- Emit activity events with type, details, output fields

### Phase 6: Testing and Validation

Comprehensive testing across all layers.

**Tasks:**
- Unit tests for `ScarMessageParser` (all activity types, edge cases)
- Integration tests for `execute_scar_command()` with activity parsing
- End-to-end tests for SSE feed with verbosity levels
- Manual testing with actual SCAR commands

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE `src/scar/message_parser.py`

- **IMPLEMENT**: Activity type enum and message parsing logic
- **PATTERN**: Enum pattern from `src/database/models.py` (lines 29-94)
- **IMPORTS**:
  ```python
  import re
  from enum import Enum
  from typing import Optional
  from pydantic import BaseModel, Field
  ```
- **GOTCHA**: SCAR messages are unstructured text, not JSON. Use regex patterns to extract tool calls. Patterns may not match all message formats, so provide fallback to generic "agent_response" type.
- **VALIDATE**: `uv run python -c "from src.scar.message_parser import ScarMessageParser, ActivityType; print('✓ Parser imports valid')"`

**Implementation Details:**

```python
"""
Message parser for extracting structured activities from SCAR text output.
"""
import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ActivityType(str, Enum):
    """Types of SCAR activities that can be extracted from messages"""
    BASH_COMMAND = "bash_command"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_EDIT = "file_edit"
    GREP_SEARCH = "grep_search"
    GLOB_PATTERN = "glob_pattern"
    TOOL_INVOCATION = "tool_invocation"
    AGENT_RESPONSE = "agent_response"
    ERROR = "error"
    PROGRESS = "progress"


class ActivityEvent(BaseModel):
    """Parsed activity event from SCAR message"""
    type: ActivityType
    timestamp: str  # ISO 8601 format
    description: str  # Human-readable description
    details: dict = Field(default_factory=dict)  # Activity-specific data
    output: Optional[str] = None  # Command output or result


class ScarMessageParser:
    """Parses SCAR message text to extract individual tool invocations and activities"""

    # Regex patterns for different tool types
    # Pattern: Running command: `git status` or Executing: `npm install`
    BASH_PATTERN = re.compile(r'(?:Running command|Executing|Bash):\s*`([^`]+)`')

    # Pattern: Reading file: `src/main.py`
    READ_PATTERN = re.compile(r'(?:Reading file|Read):\s*`([^`]+)`')

    # Pattern: Writing file: `output.txt` or Created file: `new.py`
    WRITE_PATTERN = re.compile(r'(?:Writing file|Created file|Write):\s*`([^`]+)`')

    # Pattern: Editing: `src/config.py`
    EDIT_PATTERN = re.compile(r'(?:Editing|Edit|Modified):\s*`([^`]+)`')

    # Pattern: Searching: pattern "class Project" in `src/models.py`
    GREP_PATTERN = re.compile(r'(?:Searching|Grep):\s*pattern\s*["\']([^"\']+)["\'].*in\s*`([^`]+)`')

    # Pattern: Finding files: pattern "**/*.py"
    GLOB_PATTERN = re.compile(r'(?:Finding files|Glob):\s*pattern\s*["\']([^"\']+)["\']')

    # Pattern: Tool: <ToolName> with <params>
    TOOL_PATTERN = re.compile(r'Tool:\s*(\w+)(?:\s+with\s+(.+))?')

    # Pattern: Error: <message> or Failed: <message>
    ERROR_PATTERN = re.compile(r'(?:Error|Failed|Exception):\s*(.+)', re.IGNORECASE)

    # Pattern: Progress indicators (percentage, "Done", "Complete")
    PROGRESS_PATTERN = re.compile(r'(?:(\d+)%|Done|Complete|Finished)', re.IGNORECASE)

    @staticmethod
    def parse_message(message: str, timestamp: str) -> list[ActivityEvent]:
        """
        Parse a SCAR message to extract individual activities.

        Args:
            message: Raw message text from SCAR
            timestamp: Message timestamp (ISO 8601)

        Returns:
            List of extracted activity events (may be empty for whitespace-only messages)
        """
        # Strip whitespace
        message = message.strip()

        # Skip empty messages
        if not message:
            return []

        activities: list[ActivityEvent] = []

        # Extract bash commands
        for match in ScarMessageParser.BASH_PATTERN.finditer(message):
            activities.append(ActivityEvent(
                type=ActivityType.BASH_COMMAND,
                timestamp=timestamp,
                description="Executing bash command",
                details={"command": match.group(1)},
                output=None
            ))

        # Extract file reads
        for match in ScarMessageParser.READ_PATTERN.finditer(message):
            activities.append(ActivityEvent(
                type=ActivityType.FILE_READ,
                timestamp=timestamp,
                description="Reading file",
                details={"file_path": match.group(1)},
                output=None
            ))

        # Extract file writes
        for match in ScarMessageParser.WRITE_PATTERN.finditer(message):
            activities.append(ActivityEvent(
                type=ActivityType.FILE_WRITE,
                timestamp=timestamp,
                description="Writing file",
                details={"file_path": match.group(1)},
                output=None
            ))

        # Extract file edits
        for match in ScarMessageParser.EDIT_PATTERN.finditer(message):
            activities.append(ActivityEvent(
                type=ActivityType.FILE_EDIT,
                timestamp=timestamp,
                description="Editing file",
                details={"file_path": match.group(1)},
                output=None
            ))

        # Extract grep searches
        for match in ScarMessageParser.GREP_PATTERN.finditer(message):
            activities.append(ActivityEvent(
                type=ActivityType.GREP_SEARCH,
                timestamp=timestamp,
                description="Searching for pattern",
                details={
                    "pattern": match.group(1),
                    "target": match.group(2)
                },
                output=None
            ))

        # Extract glob patterns
        for match in ScarMessageParser.GLOB_PATTERN.finditer(message):
            activities.append(ActivityEvent(
                type=ActivityType.GLOB_PATTERN,
                timestamp=timestamp,
                description="Finding files with pattern",
                details={"pattern": match.group(1)},
                output=None
            ))

        # Extract tool invocations
        for match in ScarMessageParser.TOOL_PATTERN.finditer(message):
            tool_name = match.group(1)
            tool_params = match.group(2) if match.group(2) else None
            activities.append(ActivityEvent(
                type=ActivityType.TOOL_INVOCATION,
                timestamp=timestamp,
                description=f"Tool invocation: {tool_name}",
                details={
                    "tool": tool_name,
                    "params": tool_params
                },
                output=None
            ))

        # Extract errors
        for match in ScarMessageParser.ERROR_PATTERN.finditer(message):
            activities.append(ActivityEvent(
                type=ActivityType.ERROR,
                timestamp=timestamp,
                description="Error occurred",
                details={"error_message": match.group(1)},
                output=None
            ))

        # Extract progress indicators
        for match in ScarMessageParser.PROGRESS_PATTERN.finditer(message):
            progress_value = match.group(1) if match.group(1) else match.group(0)
            activities.append(ActivityEvent(
                type=ActivityType.PROGRESS,
                timestamp=timestamp,
                description="Progress update",
                details={"progress": progress_value},
                output=None
            ))

        # If no specific patterns matched, create generic activity
        if not activities:
            # Truncate long messages
            display_message = message[:200] + ("..." if len(message) > 200 else "")
            activities.append(ActivityEvent(
                type=ActivityType.AGENT_RESPONSE,
                timestamp=timestamp,
                description="Agent response",
                details={},
                output=display_message
            ))

        return activities
```

---

### UPDATE `src/database/models.py`

- **ADD**: `ScarActivity` model after `ScarCommandExecution` (after line 301)
- **UPDATE**: Add `activities` relationship to `ScarCommandExecution` class
- **PATTERN**: Mirror `ScarCommandExecution` structure (lines 248-301)
- **IMPORTS**: No new imports needed (all exist)
- **GOTCHA**: Use `JSONB` column type for `details` field to store flexible JSON data. Use `relationship` with `back_populates` for bidirectional navigation.
- **VALIDATE**: `uv run python -c "from src.database.models import ScarActivity; print('✓ ScarActivity model valid')"`

**Implementation Details:**

Add after `ScarCommandExecution` class (after line 301):

```python
class ScarActivity(Base):
    """Tracks individual SCAR activities (tool calls, operations)"""

    __tablename__ = "scar_activities"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    execution_id = Column(PGUUID(as_uuid=True), ForeignKey("scar_executions.id"), nullable=False)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    activity_type = Column(String(50), nullable=False)  # bash_command, file_read, etc.
    description = Column(Text, nullable=False)  # Human-readable description
    details = Column(JSONB, nullable=True)  # Activity-specific data (command, file_path, etc.)
    output = Column(Text, nullable=True)  # Command output or result
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    execution = relationship("ScarCommandExecution", back_populates="activities")
    project = relationship("Project")

    @property
    def source(self):
        """Activity source is always SCAR"""
        return "scar"

    def __repr__(self) -> str:
        return f"<ScarActivity(id={self.id}, type={self.activity_type}, timestamp={self.timestamp})>"
```

Update `ScarCommandExecution` class to add relationship (around line 267, before `@property` definitions):

```python
# Add this inside ScarCommandExecution class
activities = relationship(
    "ScarActivity", back_populates="execution", cascade="all, delete-orphan"
)
```

---

### CREATE Alembic Migration `src/database/migrations/versions/XXX_add_scar_activity_table.py`

- **IMPLEMENT**: Alembic migration to create `scar_activities` table with indexes
- **PATTERN**: Follow existing migration files in `src/database/migrations/versions/`
- **IMPORTS**:
  ```python
  from alembic import op
  import sqlalchemy as sa
  from sqlalchemy.dialects.postgresql import UUID, JSONB
  from datetime import datetime
  ```
- **GOTCHA**: Use `UUID(as_uuid=True)` for UUID columns. Add `server_default=sa.func.now()` for timestamp. Create indexes for efficient queries.
- **VALIDATE**: `uv run alembic upgrade head` (should apply migration successfully)

**Implementation Steps:**

1. Generate migration stub:
```bash
uv run alembic revision -m "add_scar_activity_table"
```

2. Edit the generated file with:

```python
"""add_scar_activity_table

Revision ID: <generated>
Revises: <previous_revision>
Create Date: 2026-01-06

Adds scar_activities table for storing granular SCAR execution activities.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '<generated>'
down_revision = '<previous_revision>'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'scar_activities',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('execution_id', UUID(as_uuid=True), sa.ForeignKey('scar_executions.id'), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('activity_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('details', JSONB(), nullable=True),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Add index on execution_id for faster queries by execution
    op.create_index(
        'idx_scar_activities_execution_id',
        'scar_activities',
        ['execution_id']
    )

    # Add composite index on project_id + timestamp for SSE feed queries
    op.create_index(
        'idx_scar_activities_project_timestamp',
        'scar_activities',
        ['project_id', 'timestamp']
    )


def downgrade() -> None:
    op.drop_index('idx_scar_activities_project_timestamp')
    op.drop_index('idx_scar_activities_execution_id')
    op.drop_table('scar_activities')
```

---

### UPDATE `src/scar/client.py`

- **REFACTOR**: Reduce poll interval from 2.0s to 0.5s (line 214)
- **ADD**: `stream_messages_incremental()` method that yields new messages as they arrive
- **PATTERN**: Follow async generator pattern, similar to existing `wait_for_completion()`
- **IMPORTS**: Add `from typing import AsyncGenerator` to existing imports
- **GOTCHA**: Must track `previous_message_count` to avoid re-yielding messages. Completion detection still requires 2 stable polls.
- **VALIDATE**: `uv run python -c "from src.scar.client import ScarClient; print('✓ ScarClient updated')"`

**Implementation Details:**

1. Update `wait_for_completion()` default poll interval (line 214):
```python
async def wait_for_completion(
    self, conversation_id: str, timeout: Optional[float] = None, poll_interval: float = 0.5  # CHANGED: 2.0 → 0.5
) -> list[ScarMessage]:
```

2. Add new method after `wait_for_completion()` (around line 290):

```python
async def stream_messages_incremental(
    self,
    conversation_id: str,
    timeout: Optional[float] = None,
    poll_interval: float = 0.5,
) -> AsyncGenerator[ScarMessage, None]:
    """
    Stream SCAR messages incrementally as they arrive.

    Unlike wait_for_completion which returns all messages at the end,
    this yields new messages as they're detected during polling.

    Args:
        conversation_id: Conversation ID to poll
        timeout: Max wait time in seconds (defaults to self.timeout_seconds)
        poll_interval: Seconds between polls (default: 0.5)

    Yields:
        ScarMessage: New messages as they arrive

    Raises:
        TimeoutError: If no completion detected within timeout
        httpx.HTTPError: If request fails
    """
    if timeout is None:
        timeout = float(self.timeout_seconds)

    logger.info(
        "Starting incremental message stream",
        extra={
            "conversation_id": conversation_id,
            "timeout": timeout,
            "poll_interval": poll_interval,
        },
    )

    start_time = asyncio.get_event_loop().time()
    previous_message_count = 0
    stable_count = 0

    while True:
        # Check timeout
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            raise TimeoutError(
                f"Message stream timed out after {elapsed:.1f}s "
                f"(timeout: {timeout}s, conversation: {conversation_id})"
            )

        # Get current messages
        messages = await self.get_messages(conversation_id)
        current_count = len(messages)

        logger.debug(
            f"Poll: {current_count} messages ({elapsed:.1f}s elapsed)",
            extra={"conversation_id": conversation_id, "message_count": current_count},
        )

        # Yield only NEW messages
        if current_count > previous_message_count:
            new_messages = messages[previous_message_count:]
            for msg in new_messages:
                yield msg

            previous_message_count = current_count
            stable_count = 0
        else:
            stable_count += 1

        # Check for completion (2 stable polls with no new messages)
        if stable_count >= 2:
            logger.info(
                "Message stream completed",
                extra={
                    "conversation_id": conversation_id,
                    "message_count": current_count,
                    "duration": elapsed,
                },
            )
            return

        # Wait before next poll
        await asyncio.sleep(poll_interval)
```

3. Update imports at top of file:
```python
from typing import AsyncGenerator, Optional  # Add AsyncGenerator to existing imports
```

---

### UPDATE `src/services/scar_executor.py`

- **REFACTOR**: Replace `wait_for_completion()` with `stream_messages_incremental()` for real-time parsing
- **ADD**: Import `ScarMessageParser` and `ScarActivity`
- **ADD**: Parse each message and create `ScarActivity` records immediately
- **PATTERN**: Follow existing error handling and logging patterns
- **IMPORTS**:
  ```python
  from src.scar.message_parser import ScarMessageParser, ActivityEvent
  from src.database.models import ScarActivity
  ```
- **GOTCHA**: Must commit activities immediately (not batched) so SSE feed can query them. Still aggregate full output text for backward compatibility.
- **VALIDATE**: `uv run python -m pytest tests/services/test_scar_executor.py::test_execute_prime_command -v`

**Implementation Details:**

Replace the message waiting and aggregation section (lines 113-128) with:

```python
# OLD CODE (lines 117-128):
#     messages = await client.wait_for_completion(
#         conversation_id, timeout=settings.scar_timeout_seconds
#     )
#     output = "\n".join(msg.message for msg in messages)

# NEW CODE:
        # Stream messages incrementally and parse activities in real-time
        all_messages = []

        async for msg in client.stream_messages_incremental(
            conversation_id, timeout=settings.scar_timeout_seconds
        ):
            all_messages.append(msg)

            # Parse message for activities
            activities = ScarMessageParser.parse_message(
                msg.message,
                msg.timestamp.isoformat()
            )

            # Store each activity in database
            for activity_event in activities:
                activity = ScarActivity(
                    execution_id=execution.id,
                    project_id=project_id,
                    activity_type=activity_event.type.value,
                    description=activity_event.description,
                    details=activity_event.details,
                    output=activity_event.output,
                    timestamp=datetime.fromisoformat(activity_event.timestamp),
                )
                session.add(activity)

            # Commit activities immediately for SSE feed to pick up
            await session.commit()

        # Aggregate output from all messages (backward compatibility)
        output = "\n".join(msg.message for msg in all_messages)
```

Add imports at top of file (after existing imports):
```python
from src.scar.message_parser import ScarMessageParser
from src.database.models import ScarActivity
```

---

### UPDATE `src/services/scar_feed_service.py`

- **REFACTOR**: Query both `ScarCommandExecution` and `ScarActivity` for streaming
- **ADD**: Reduce poll interval from 2s to 0.5s to match SCAR polling
- **ADD**: Stream detailed activities when verbosity >= 3
- **PATTERN**: Follow existing async generator pattern
- **IMPORTS**: Add `from src.database.models import ScarActivity` to existing imports
- **GOTCHA**: Activities should only stream at verbosity level 3. Must query by `project_id` AND `timestamp > last_timestamp` for incremental streaming.
- **VALIDATE**: Manual testing with SSE endpoint

**Implementation Details:**

Replace `stream_scar_activity()` function (lines 90-168) with:

```python
async def stream_scar_activity(
    session: AsyncSession, project_id: UUID, verbosity_level: int = 2
) -> AsyncGenerator[Dict, None]:
    """
    Stream SCAR activity updates in real-time.

    Streams both:
    - ScarCommandExecution records (verbosity 1-2): High-level command status
    - ScarActivity records (verbosity 3): Detailed individual operations

    Args:
        session: Database session
        project_id: Project UUID
        verbosity_level: Verbosity level (1=low, 2=medium, 3=high)

    Yields:
        Activity dictionaries as they occur
    """
    logger.info(
        f"Starting SCAR activity stream for project {project_id} (verbosity: {verbosity_level})"
    )

    last_execution_timestamp = None
    last_activity_timestamp = None

    # Get initial command executions (verbosity 1-2)
    executions = await get_recent_scar_activity(
        session, project_id, limit=10, verbosity_level=verbosity_level
    )
    if executions:
        last_execution_timestamp = executions[-1]["timestamp"]
        for execution in executions:
            yield execution

    # Get initial detailed activities (verbosity 3)
    if verbosity_level >= 3:
        query = (
            select(ScarActivity)
            .where(ScarActivity.project_id == project_id)
            .order_by(ScarActivity.timestamp.desc())
            .limit(20)
        )
        result = await session.execute(query)
        activities = list(reversed(result.scalars().all()))

        if activities:
            last_activity_timestamp = activities[-1].timestamp.isoformat()
            for activity in activities:
                yield {
                    "id": str(activity.id),
                    "timestamp": activity.timestamp.isoformat(),
                    "source": "scar",
                    "message": activity.description,
                    "type": activity.activity_type,
                    "details": activity.details,
                    "output": activity.output,
                }

    # Poll for new activities
    while True:
        await asyncio.sleep(0.5)  # CHANGED: 2s → 0.5s to match SCAR polling

        # Query for new command executions (verbosity 1-2)
        if verbosity_level <= 2:
            if last_execution_timestamp:
                last_dt = datetime.fromisoformat(last_execution_timestamp)
                query = (
                    select(ScarCommandExecution)
                    .where(
                        ScarCommandExecution.project_id == project_id,
                        ScarCommandExecution.started_at > last_dt,
                    )
                    .order_by(ScarCommandExecution.started_at.asc())
                )

                result = await session.execute(query)
                new_executions = result.scalars().all()

                for execution in new_executions:
                    execution_dict = {
                        "id": str(execution.id),
                        "timestamp": execution.started_at.isoformat(),
                        "source": "scar",
                        "message": (
                            f"{execution.command_type.value}: {execution.status.value}"
                            if execution.status
                            else execution.command_type.value
                        ),
                        "phase": execution.phase.name if execution.phase else None,
                    }
                    last_execution_timestamp = execution_dict["timestamp"]
                    yield execution_dict

        # Query for new detailed activities (verbosity 3)
        if verbosity_level >= 3:
            if last_activity_timestamp:
                last_dt = datetime.fromisoformat(last_activity_timestamp)
            else:
                # First query, use current time
                last_dt = datetime.utcnow()

            query = (
                select(ScarActivity)
                .where(
                    ScarActivity.project_id == project_id,
                    ScarActivity.timestamp > last_dt,
                )
                .order_by(ScarActivity.timestamp.asc())
            )

            result = await session.execute(query)
            new_activities = result.scalars().all()

            for activity in new_activities:
                activity_dict = {
                    "id": str(activity.id),
                    "timestamp": activity.timestamp.isoformat(),
                    "source": "scar",
                    "message": activity.description,
                    "type": activity.activity_type,
                    "details": activity.details,
                    "output": activity.output,
                }
                last_activity_timestamp = activity_dict["timestamp"]
                yield activity_dict
```

Add import at top of file:
```python
from src.database.models import ScarActivity, ScarCommandExecution  # Add ScarActivity
```

---

### CREATE `tests/scar/test_message_parser.py`

- **IMPLEMENT**: Comprehensive unit tests for `ScarMessageParser`
- **PATTERN**: Follow pytest patterns from `tests/services/test_scar_executor.py`
- **IMPORTS**:
  ```python
  import pytest
  from src.scar.message_parser import ScarMessageParser, ActivityType, ActivityEvent
  ```
- **GOTCHA**: Test both positive cases (patterns match) and negative cases (no patterns, fallback to generic)
- **VALIDATE**: `uv run python -m pytest tests/scar/test_message_parser.py -v`

**Implementation Details:**

```python
"""
Tests for SCAR message parser.
"""
import pytest

from src.scar.message_parser import ActivityEvent, ActivityType, ScarMessageParser


def test_parse_bash_command():
    """Test parsing bash command from message"""
    message = "Running command: `git status`"
    timestamp = "2026-01-06T10:00:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 1
    assert activities[0].type == ActivityType.BASH_COMMAND
    assert activities[0].details["command"] == "git status"
    assert activities[0].description == "Executing bash command"
    assert activities[0].timestamp == timestamp


def test_parse_file_read():
    """Test parsing file read operation"""
    message = "Reading file: `src/main.py`"
    timestamp = "2026-01-06T10:01:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 1
    assert activities[0].type == ActivityType.FILE_READ
    assert activities[0].details["file_path"] == "src/main.py"
    assert activities[0].description == "Reading file"


def test_parse_file_write():
    """Test parsing file write operation"""
    message = "Writing file: `output.txt`"
    timestamp = "2026-01-06T10:02:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 1
    assert activities[0].type == ActivityType.FILE_WRITE
    assert activities[0].details["file_path"] == "output.txt"


def test_parse_file_edit():
    """Test parsing file edit operation"""
    message = "Editing: `src/config.py`"
    timestamp = "2026-01-06T10:03:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 1
    assert activities[0].type == ActivityType.FILE_EDIT
    assert activities[0].details["file_path"] == "src/config.py"


def test_parse_grep_search():
    """Test parsing grep search operation"""
    message = 'Searching: pattern "class Project" in `src/database/models.py`'
    timestamp = "2026-01-06T10:04:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 1
    assert activities[0].type == ActivityType.GREP_SEARCH
    assert activities[0].details["pattern"] == "class Project"
    assert activities[0].details["target"] == "src/database/models.py"


def test_parse_glob_pattern():
    """Test parsing glob pattern operation"""
    message = 'Finding files: pattern "**/*.py"'
    timestamp = "2026-01-06T10:05:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 1
    assert activities[0].type == ActivityType.GLOB_PATTERN
    assert activities[0].details["pattern"] == "**/*.py"


def test_parse_tool_invocation():
    """Test parsing tool invocation"""
    message = "Tool: Bash with git status"
    timestamp = "2026-01-06T10:06:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 1
    assert activities[0].type == ActivityType.TOOL_INVOCATION
    assert activities[0].details["tool"] == "Bash"
    assert activities[0].details["params"] == "git status"


def test_parse_error():
    """Test parsing error message"""
    message = "Error: File not found at path /src/missing.py"
    timestamp = "2026-01-06T10:07:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 1
    assert activities[0].type == ActivityType.ERROR
    assert "File not found" in activities[0].details["error_message"]


def test_parse_progress():
    """Test parsing progress indicator"""
    message = "Processing files: 75% complete"
    timestamp = "2026-01-06T10:08:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 1
    assert activities[0].type == ActivityType.PROGRESS
    assert activities[0].details["progress"] == "75"


def test_parse_multiple_operations():
    """Test parsing message with multiple operations"""
    message = """
    Reading file: `src/config.py`
    Running command: `ls -la`
    Editing: `src/main.py`
    """
    timestamp = "2026-01-06T10:09:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 3
    types = [a.type for a in activities]
    assert ActivityType.FILE_READ in types
    assert ActivityType.BASH_COMMAND in types
    assert ActivityType.FILE_EDIT in types


def test_parse_no_patterns_fallback():
    """Test parsing message with no recognizable patterns falls back to agent_response"""
    message = "This is a generic response from the agent about project structure."
    timestamp = "2026-01-06T10:10:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 1
    assert activities[0].type == ActivityType.AGENT_RESPONSE
    assert "generic response" in activities[0].output


def test_parse_empty_message():
    """Test parsing empty message returns no activities"""
    message = ""
    timestamp = "2026-01-06T10:11:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 0


def test_parse_whitespace_only_message():
    """Test parsing whitespace-only message returns no activities"""
    message = "   \n\t   "
    timestamp = "2026-01-06T10:12:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 0


def test_parse_long_message_truncates_output():
    """Test that long messages are truncated in agent_response output"""
    message = "A" * 250  # 250 characters
    timestamp = "2026-01-06T10:13:00Z"

    activities = ScarMessageParser.parse_message(message, timestamp)

    assert len(activities) == 1
    assert activities[0].type == ActivityType.AGENT_RESPONSE
    assert len(activities[0].output) == 203  # 200 chars + "..."
    assert activities[0].output.endswith("...")
```

---

### RUN Database Migration

- **EXECUTE**: Apply Alembic migration to create `scar_activities` table
- **PATTERN**: Standard Alembic upgrade command
- **VALIDATE**:
  ```bash
  uv run alembic upgrade head
  uv run python -c "from src.database.models import ScarActivity; print('✓ Migration applied')"
  ```
- **GOTCHA**: Ensure PostgreSQL database is running and accessible. Check connection string in `.env`.

**Commands:**

```bash
# Apply migration
uv run alembic upgrade head

# Verify table exists
uv run python -c "from sqlalchemy import inspect; from src.database.connection import engine; import asyncio; async def check(): async with engine.connect() as conn: insp = inspect(conn); tables = await conn.run_sync(lambda c: inspect(c).get_table_names()); print(f'✓ scar_activities table exists: {\"scar_activities\" in tables}'); asyncio.run(check())"
```

---

## TESTING STRATEGY

### Unit Tests

**Coverage Target**: 85%+ for new code

**Test Files:**
- `tests/scar/test_message_parser.py` - Parser logic with all activity types, edge cases, fallbacks
- `tests/unit/scar/test_client.py` - Update tests for new `stream_messages_incremental()` method

**Key Test Scenarios:**
- Message parsing with each activity type (bash, read, write, edit, grep, glob, tool, error, progress)
- Message parsing with multiple operations in one message
- Message parsing with no recognizable patterns (fallback to agent_response)
- Empty and whitespace-only messages
- Long messages (truncation behavior)
- Incremental streaming with new messages arriving over time
- Completion detection (2 stable polls with no new messages)

### Integration Tests

**Test Files:**
- `tests/services/test_scar_executor.py` - Verify activities are created during command execution

**Test Scenarios:**
- Execute SCAR command and verify `ScarActivity` records are created
- Verify activities are committed immediately (not batched)
- Test that full output text is still aggregated for backward compatibility
- Test timeout behavior with incremental streaming
- Test connection error handling during streaming

### Manual Testing

**Prerequisites:**
- PostgreSQL database running
- SCAR service running and accessible
- Project Manager backend running: `uv run uvicorn src.main:app --reload`
- Frontend running (if testing UI): `cd frontend && npm run dev`

**Test Scenarios:**

1. **Verbosity Level 1 (Low)**: Only major events
   - Send message requesting SCAR command (e.g., "Prime the codebase")
   - Verify SSE feed shows: "PRIME: RUNNING" → "PRIME: COMPLETED"
   - No detailed activities visible

2. **Verbosity Level 2 (Medium)**: Command executions
   - Same test as Level 1
   - Verify command status updates appear

3. **Verbosity Level 3 (High)**: All detailed activities
   - Send message requesting SCAR command
   - Verify SSE feed shows:
     - Individual bash commands (e.g., "Executing bash command: git ls-files")
     - File read operations (e.g., "Reading file: src/main.py")
     - Grep searches if applicable
     - Progress indicators
   - Verify activities appear in real-time (<1s latency)
   - Verify activities have `type`, `details`, `output` fields

4. **Real-time Streaming**: Verify <1s latency
   - Start long-running SCAR command (e.g., validate)
   - Observe activities appearing incrementally (not all at once after completion)
   - Verify poll interval is 0.5s (activities should appear every ~0.5-1s)

5. **Database Verification**: Check stored activities
   - After SCAR command completes, query database:
     ```sql
     SELECT * FROM scar_activities WHERE project_id = '<project_id>' ORDER BY timestamp DESC LIMIT 20;
     ```
   - Verify activity_type, description, details, output fields are populated

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Import Validation (CRITICAL)

**Verify all imports resolve before running tests:**

```bash
uv run python -c "from src.main import app; print('✓ All imports valid')"
```

**Expected**: "✓ All imports valid" (no ModuleNotFoundError or ImportError)

**Why**: Catches incorrect imports immediately. If this fails, fix imports before proceeding.

### Level 2: Database Migration

**Apply migration:**

```bash
uv run alembic upgrade head
```

**Expected**: Migration applies successfully, no errors

**Verify table exists:**

```bash
uv run python -c "from src.database.models import ScarActivity, ScarCommandExecution; print('✓ ScarActivity model imports'); print('✓ Relationships configured')"
```

**Expected**: Both messages print successfully

### Level 3: Unit Tests

**Run message parser tests:**

```bash
uv run python -m pytest tests/scar/test_message_parser.py -v
```

**Expected**: All tests pass (100% coverage for parser)

**Run SCAR executor tests:**

```bash
uv run python -m pytest tests/services/test_scar_executor.py -v
```

**Expected**: All existing tests pass (may need to update mocks for new incremental streaming)

### Level 4: Type Checking

**Run mypy type checking:**

```bash
uv run mypy src/scar/message_parser.py src/scar/client.py src/services/scar_executor.py src/services/scar_feed_service.py --no-error-summary 2>&1 | head -50
```

**Expected**: No type errors (or only minor warnings)

### Level 5: Linting

**Run ruff linting:**

```bash
uv run ruff check src/scar/message_parser.py src/scar/client.py src/services/scar_executor.py src/services/scar_feed_service.py src/database/models.py
```

**Expected**: No linting errors

**Auto-fix issues if any:**

```bash
uv run ruff check --fix src/
```

### Level 6: Manual End-to-End Testing

**Start backend:**

```bash
uv run uvicorn src.main:app --reload
```

**Test SSE endpoint (separate terminal):**

```bash
# Replace <project_id> with actual project UUID
curl -N "http://localhost:8000/api/sse/scar/<project_id>?verbosity=3"
```

**Expected**: SSE stream opens, heartbeat events arrive every 30s

**Trigger SCAR command and observe:**
- Send message via Telegram bot or web UI to trigger SCAR command
- Observe SSE stream showing detailed activities in real-time
- Verify `type`, `details`, `output` fields are present at verbosity=3

### Level 7: Database Query Validation

**After running SCAR command, verify activities were stored:**

```sql
-- Connect to PostgreSQL database
SELECT
    activity_type,
    description,
    details,
    timestamp
FROM scar_activities
WHERE project_id = '<project_id>'
ORDER BY timestamp DESC
LIMIT 10;
```

**Expected**: Multiple activity rows with different types (bash_command, file_read, etc.)

---

## ACCEPTANCE CRITERIA

- [ ] Feature implements detailed SCAR activity streaming (bash, file reads, grep, glob, edit, etc.)
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage ≥85% for new code (message parser)
- [ ] Integration tests verify activities created during execution
- [ ] Code follows project conventions (snake_case functions, PascalCase classes, proper typing)
- [ ] No regressions in existing functionality (verbosity 1-2 still works)
- [ ] Database migration applies successfully (`scar_activities` table created with indexes)
- [ ] SSE feed streams activities in real-time (<1s latency from SCAR to UI)
- [ ] Activities have structured data: `type`, `details`, `output` fields
- [ ] Verbosity filtering works (level 3 = detailed activities, level 1-2 = executions only)
- [ ] Backward compatibility maintained (`ScarCommandExecution.output` still aggregated)
- [ ] Manual testing confirms activities appear incrementally (not batched after completion)
- [ ] Performance is acceptable (0.5s polling doesn't overload database)

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order (top to bottom)
- [ ] Each task validated immediately after implementation
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit tests for parser and executor)
- [ ] No linting or type checking errors
- [ ] Manual end-to-end testing confirms feature works
- [ ] Database migration tested on clean database
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability
- [ ] SSE feed performance verified (multiple concurrent connections)

---

## NOTES

### Design Trade-offs

**Polling vs. True Streaming:**
- **Constraint**: SCAR Test Adapter API does NOT support true streaming (WebSocket/SSE)
- **Solution**: Enhanced polling with 0.5s interval and incremental message processing
- **Trade-off**: Minimum 0.5s latency vs instant streaming (acceptable for MVP)

**Message Parsing Approach:**
- **Constraint**: SCAR messages are unstructured text, not structured JSON/events
- **Solution**: Regex-based parsing to extract tool invocations
- **Limitation**: May miss operations if message format changes in SCAR
- **Mitigation**: Comprehensive test coverage, fallback to generic "agent_response" type, regex patterns can be extended

**Database Storage:**
- **Decision**: Store all activities in `scar_activities` table
- **Benefit**: Historical view, replay capabilities, verbosity filtering, structured queries
- **Cost**: Increased database storage (~50-200 activities per command execution)
- **Optimization**: Add retention policy later if needed (e.g., delete activities >30 days old)

**Backward Compatibility:**
- **Maintained**: `ScarCommandExecution.output` still stores full aggregated text
- **Benefit**: Existing code relying on `execution.output` continues to work
- **New Capability**: `execution.activities` relationship provides structured access

### Future Enhancements

**Real Streaming** (if SCAR adds WebSocket support):
- Replace polling with WebSocket subscription
- Eliminate 0.5s latency for instant activity delivery
- Reduce database query load (push-based vs pull-based)

**Advanced Filtering:**
- Filter SSE feed by activity type (show only bash commands, hide file reads)
- Search activities by keyword or pattern
- Highlight errors and warnings in red

**Activity Replay:**
- Replay SCAR execution step-by-step for debugging
- "Time travel" through past executions
- Export execution trace as JSON for sharing

**Performance Optimizations:**
- Virtual scrolling in frontend for large activity lists
- Activity aggregation (combine related operations: "Read 15 files")
- Lazy loading of output (fetch on expand)
- Batch activity inserts (trade latency for throughput)

### Breaking Changes

**None** - This is a pure enhancement. Existing verbosity levels 1-2 continue to work as before. Verbosity level 3 adds new detailed streaming without affecting lower levels.

### Migration Notes

**Database Migration Required**: Run `uv run alembic upgrade head` before deploying

**Backward Compatibility**:
- Existing `ScarCommandExecution` records continue to work
- New `ScarActivity` table is additive (adds capabilities, doesn't replace)
- API endpoint `/api/sse/scar/{project_id}` remains unchanged (verbosity parameter extended)

**Rollback Plan**: If issues occur, run `uv run alembic downgrade -1` to remove `scar_activities` table and revert code changes

---

## RESEARCH VALIDATION

**External API Verification**: Not applicable - no new external dependencies added. Using existing `sse-starlette` and `sqlalchemy` libraries.

**Existing Research Reports**: No prior research reports found in `.agents/report/`. Reviewed existing plan at `.agents/plans/enhance-sse-detailed-output.md` for context and patterns.

**Documentation Consulted:**
- [Server-Sent Events API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) - SSE event stream format
- [sse-starlette GitHub](https://github.com/sysid/sse-starlette) - FastAPI SSE library usage patterns
- Project codebase patterns (error handling, logging, database models)

---

## REVISION HISTORY

- **2026-01-06**: Initial plan created for feature branch `feature-sse-detailed-execution-output`
- **Target Completion**: 2026-01-07
- **Estimated Effort**: 6-8 hours (1 developer)
- **Complexity Assessment**: High (8/10 confidence for one-pass implementation success)
