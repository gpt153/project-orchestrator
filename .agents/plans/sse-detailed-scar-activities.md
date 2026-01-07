# Feature: Enhanced SSE Feed with Detailed SCAR Execution Activities

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Enhance the SSE feed to display granular, real-time SCAR execution details by parsing SCAR's message output to extract individual tool invocations (bash commands, file operations, searches, edits) and stream them as separate activities. Currently, the SSE feed shows only high-level status updates like "PRIME: COMPLETED". Users need visibility into what SCAR is actually doing: "🔧 BASH: git ls-files", "📖 Reading README.md", "✏️ Editing src/main.py", etc., similar to Claude Code CLI's verbose output.

## User Story

As a Project Manager WebUI user
I want to see detailed, real-time SCAR execution output showing individual tool invocations with icons and collapsible details
So that I can understand exactly what operations SCAR is performing and track progress during long-running commands like `/command-invoke prime`

## Problem Statement

**Current State**:
- SSE feed shows only aggregated command status: "PRIME: COMPLETED"
- No visibility into individual tool invocations during execution
- SCAR output contains tool indicators (🔧 BASH, 📖 READ, etc.) but they're not parsed
- Users can't see incremental progress or understand what's happening during long commands

**Root Cause**:
- `ScarCommandExecution` stores only aggregated `output` text, not individual activities
- SSE feed service (`scar_feed_service.py`) creates one activity per execution, not per tool call
- No parsing logic to extract tool invocations from SCAR message strings
- No database model to store granular activities

**Desired State**:
- Parse SCAR messages to extract tool invocations as they arrive
- Store each tool invocation as a separate `ScarActivity` record
- Stream activities incrementally via SSE during execution
- Display activity-specific icons and formatting in frontend
- Support verbosity level 3 for maximum detail while maintaining backward compatibility at levels 1-2

## Solution Statement

Implement message parsing and granular activity streaming:

1. **Activity Model**: Create `ScarActivity` model to store individual tool invocations
2. **Message Parser**: Parse SCAR message text to extract tool calls (emoji-prefixed lines)
3. **Incremental Storage**: Create activities during execution as messages arrive
4. **Polling Enhancement**: Update SSE service to query and stream activities incrementally
5. **Frontend Icons**: Map activity types to emoji icons with collapsible details
6. **Backward Compatibility**: Activate detailed activities only at verbosity level 3

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: Medium
**Primary Systems Affected**: Database schema, SCAR executor, SSE feed service, Frontend component

**Dependencies**:
- Existing: `sqlalchemy[asyncio]`, `sse-starlette`, `httpx`
- No new dependencies required

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**SCAR Integration**:
- `src/scar/client.py` (lines 171-195) - Message polling pattern, `get_messages()` method
- `src/scar/types.py` (lines 23-30) - `ScarMessage` structure
- `src/services/scar_executor.py` (lines 98-156) - Execution flow, where to insert activity creation

**Database Layer**:
- `src/database/models.py` (lines 279-332) - `ScarCommandExecution` model, add `ScarActivity` and relationship
- `src/database/connection.py` (lines 14-25) - Async session maker pattern
- `src/database/migrations/versions/20260107_1131_add_conversation_topics.py` - Migration pattern example

**SSE Streaming**:
- `src/services/scar_feed_service.py` (lines 18-95) - Activity retrieval logic, needs refactor
- `src/api/sse.py` (lines 22-104) - SSE endpoint, verbosity parameter

**Frontend**:
- `frontend/src/components/RightPanel/ScarActivityFeed.tsx` (lines 46-56) - Icon mapping logic
- `frontend/src/hooks/useScarFeed.ts` (lines 11-45) - SSE consumption pattern

**Testing**:
- `tests/services/test_scar_executor.py` (lines 134-160) - Execution testing pattern

### New Files to Create

- `src/services/scar_message_parser.py` - Parse SCAR messages to extract tool invocations
- `src/database/migrations/versions/YYYYMMDD_HHMM_add_scar_activities.py` - Alembic migration
- `tests/unit/services/test_scar_message_parser.py` - Parser unit tests

### Relevant Documentation

**SCAR Message Format**:
- `.agents/reference/streaming-modes.md` (lines 68-87) - Tool call formatting: `🔧 BASH\ngit status`
- `.agents/examples/claude-telegram-bot/README.md` (lines 45-52) - Example SCAR output format

**Database Patterns**:
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) - Async session usage
- [Alembic Migrations](https://alembic.sqlalchemy.org/en/latest/tutorial.html) - Migration creation

**SSE Protocol**:
- [sse-starlette GitHub](https://github.com/sysid/sse-starlette) - EventSourceResponse patterns

### Patterns to Follow

**Async Session Pattern**:
```python
async with async_session_maker() as session:
    session.add(model)
    await session.commit()
    await session.refresh(model)
```

**Database Model Pattern**:
```python
class ScarActivity(Base):
    __tablename__ = "scar_activities"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    execution_id = Column(PGUUID(as_uuid=True), ForeignKey("scar_executions.id"), nullable=False)
    # ... other columns
    execution = relationship("ScarCommandExecution", back_populates="activities")
```

**Tool Message Format** (from SCAR):
```
🔧 BASH
git ls-files

📖 READ
Reading: src/main.py

✏️ EDIT
Editing: src/config.py
```

**Parsing Pattern**:
```python
def parse_scar_message(message: str) -> list[ParsedActivity]:
    """Extract tool invocations from SCAR message text"""
    activities = []
    lines = message.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('🔧 '):
            # Extract bash command from next line
            tool_name = line.split()[1] if len(line.split()) > 1 else "BASH"
            command = lines[i+1] if i+1 < len(lines) else ""
            activities.append(ParsedActivity(
                activity_type="bash_command",
                tool_name=tool_name.lower(),
                message=line,
                parameters={"command": command}
            ))
    return activities
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation - Database Schema and Parser

Create database model for activities and parser for extracting tool invocations from SCAR messages.

**Tasks**:
- Add `ScarActivity` model to database
- Create Alembic migration
- Implement message parser with emoji detection
- Write parser unit tests

### Phase 2: Incremental Activity Creation

Modify SCAR executor to create activities during execution as messages arrive.

**Tasks**:
- Update `execute_scar_command()` to poll messages incrementally
- Parse each new message and create activities
- Commit activities in real-time (not batched)
- Maintain backward compatibility (only store `output` if verbosity < 3)

### Phase 3: Enhanced SSE Feed

Update SSE service to query and stream activities instead of just executions.

**Tasks**:
- Refactor `get_recent_scar_activity()` to query `ScarActivity` table
- Implement timestamp-based polling for new activities
- Map activity types to frontend-compatible format
- Maintain backward compatibility for verbosity levels 1-2

### Phase 4: Frontend Enhancement

Update frontend to display activity-specific icons and formatting.

**Tasks**:
- Enhance icon mapping logic
- Add collapsible details for tool parameters
- Improve activity grouping by execution
- Test verbosity level switching

### Phase 5: Testing and Validation

Comprehensive testing of parsing, storage, and streaming.

**Tasks**:
- Unit tests for message parser
- Integration tests for activity creation
- E2E test for SSE feed with activities
- Manual testing with real SCAR commands

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE src/services/scar_message_parser.py

- **IMPLEMENT**: `ScarMessageParser` class with `parse_message()` method
- **PATTERN**: Regex-based parsing for emoji-prefixed lines
- **IMPORTS**: `re`, `typing`, `datetime`, `pydantic`
- **VALIDATE**: `uv run python -c "from src.services.scar_message_parser import ScarMessageParser; print('✓ Parser valid')"`

**Implementation**:
```python
"""
SCAR Message Parser for extracting tool invocations.

Parses SCAR output messages to extract individual tool calls (bash, read, write, edit, grep, glob, task).
"""

import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ParsedActivity(BaseModel):
    """Parsed activity from SCAR message"""
    activity_type: str = Field(..., description="Activity type: bash_command, file_read, file_write, etc.")
    tool_name: Optional[str] = Field(None, description="Tool name if applicable")
    message: str = Field(..., description="Human-readable message")
    parameters: dict = Field(default_factory=dict, description="Tool parameters (command, file_path, etc.)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ScarMessageParser:
    """Parse SCAR messages to extract tool invocations"""

    # Emoji to activity type mapping
    TOOL_EMOJIS = {
        "🔧": ("bash_command", "bash"),
        "📖": ("file_read", "read"),
        "✏️": ("file_edit", "edit"),
        "📝": ("file_write", "write"),
        "🔍": ("grep_search", "grep"),
        "📂": ("glob_search", "glob"),
        "🤖": ("task_spawn", "task"),
        "⚡": ("agent_response", None),
    }

    @classmethod
    def parse_message(cls, message: str, base_timestamp: Optional[datetime] = None) -> list[ParsedActivity]:
        """
        Parse SCAR message to extract tool invocations.

        Expected format:
        ```
        🔧 BASH
        git ls-files

        📖 READ
        Reading: src/main.py
        ```

        Args:
            message: Raw SCAR message text
            base_timestamp: Base timestamp for activities (defaults to now)

        Returns:
            List of parsed activities
        """
        if base_timestamp is None:
            base_timestamp = datetime.utcnow()

        activities = []
        lines = message.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check if line starts with known emoji
            for emoji, (activity_type, tool_name) in cls.TOOL_EMOJIS.items():
                if line.startswith(emoji):
                    # Extract tool name from line (e.g., "🔧 BASH" -> "BASH")
                    parts = line.split(maxsplit=1)
                    tool_display = parts[1] if len(parts) > 1 else ""

                    # Get next lines as parameters/content
                    content_lines = []
                    j = i + 1
                    while j < len(lines) and not any(lines[j].startswith(e) for e in cls.TOOL_EMOJIS):
                        if lines[j].strip():
                            content_lines.append(lines[j].strip())
                        j += 1

                    content = '\n'.join(content_lines) if content_lines else ""

                    # Build parameters based on activity type
                    parameters = {}
                    if activity_type == "bash_command":
                        parameters = {"command": content}
                    elif activity_type in ("file_read", "file_write", "file_edit"):
                        # Extract file path (e.g., "Reading: src/main.py" or just "src/main.py")
                        file_match = re.search(r"(?:Reading|Writing|Editing):\s*(.+)", content)
                        if file_match:
                            parameters = {"file_path": file_match.group(1)}
                        elif content:
                            parameters = {"file_path": content}
                    elif activity_type in ("grep_search", "glob_search"):
                        parameters = {"pattern": content}

                    # Create activity with microsecond offset for ordering
                    activity = ParsedActivity(
                        activity_type=activity_type,
                        tool_name=tool_name,
                        message=f"{line}: {content[:100]}" if content else line,
                        parameters=parameters,
                        timestamp=base_timestamp.replace(microsecond=len(activities))
                    )
                    activities.append(activity)

                    # Skip processed lines
                    i = j - 1
                    break

            i += 1

        return activities
```

**GOTCHA**: Emoji detection requires exact match (including Unicode normalization)
**VALIDATE**: `uv run python -c "from src.services.scar_message_parser import ScarMessageParser; print('✓ Parser imported')"`

### UPDATE src/database/models.py - Add ScarActivity model

- **ADD** after line 332:
```python
class ScarActivity(Base):
    """Individual SCAR tool invocation activities for granular tracking"""

    __tablename__ = "scar_activities"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    execution_id = Column(PGUUID(as_uuid=True), ForeignKey("scar_executions.id"), nullable=False)
    activity_type = Column(String(50), nullable=False)  # bash_command, file_read, file_write, etc.
    tool_name = Column(String(50), nullable=True)  # bash, read, write, edit, grep, glob, task
    message = Column(Text, nullable=False)  # Human-readable message
    parameters = Column(JSONB, nullable=True)  # Tool parameters (command, file_path, pattern, etc.)
    output = Column(Text, nullable=True)  # Tool output if available
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    execution = relationship("ScarCommandExecution", back_populates="activities")

    def __repr__(self) -> str:
        return f"<ScarActivity(id={self.id}, type={self.activity_type}, tool={self.tool_name})>"
```

- **UPDATE** `ScarCommandExecution` class (around line 298): Add relationship
```python
# Add this line in ScarCommandExecution class
activities = relationship("ScarActivity", back_populates="execution", cascade="all, delete-orphan")
```

**GOTCHA**: Must add relationship to BOTH models for bidirectional access
**VALIDATE**: `uv run python -c "from src.database.models import ScarActivity; print('✓ Model valid')"`

### CREATE Migration - Add scar_activities table

- **RUN**: `cd /workspace/project-manager && alembic revision --autogenerate -m "Add scar_activities table for granular tool tracking"`
- **VERIFY**: Migration file created in `src/database/migrations/versions/`
- **REVIEW**: Ensure migration includes:
  - Table creation with all columns
  - Foreign key to `scar_executions.id` with ON DELETE CASCADE
  - Indexes on `execution_id` and `timestamp` for efficient queries
- **RUN**: `alembic upgrade head`
- **VALIDATE**: `uv run python -c "from sqlalchemy import inspect; from src.database.connection import sync_engine; print('Tables:', inspect(sync_engine).get_table_names()); assert 'scar_activities' in inspect(sync_engine).get_table_names(); print('✓ Migration applied')"`

**GOTCHA**: Alembic autogenerate may not detect relationships - verify foreign keys manually
**PATTERN**: Follow `20260107_1131_add_conversation_topics.py` migration structure

### UPDATE src/services/scar_executor.py - Create activities incrementally

- **REFACTOR** `execute_scar_command()` function (lines 49-234)
- **ADD** imports:
```python
from src.services.scar_message_parser import ScarMessageParser
from src.database.models import ScarActivity
```
- **MODIFY** execution flow to poll messages incrementally and create activities
- **PATTERN**: Poll every 2 seconds, parse new messages, create activities, commit immediately

**New Implementation** (replace lines 98-156):
```python
# Track last processed message count for incremental polling
previous_message_count = 0
all_messages = []

while True:
    # Check timeout
    elapsed = (datetime.utcnow() - start_time).total_seconds()
    if elapsed >= settings.scar_timeout_seconds:
        raise TimeoutError(f"Command timed out after {elapsed:.1f}s")

    # Get current messages
    messages = await client.get_messages(conversation_id)
    current_count = len(messages)

    # Process new messages
    if current_count > previous_message_count:
        new_messages = messages[previous_message_count:]
        all_messages.extend(new_messages)
        previous_message_count = current_count

        # Parse and create activities for each new message
        for msg in new_messages:
            activities = ScarMessageParser.parse_message(msg.message, msg.timestamp)
            for activity in activities:
                scar_activity = ScarActivity(
                    execution_id=execution.id,
                    activity_type=activity.activity_type,
                    tool_name=activity.tool_name,
                    message=activity.message,
                    parameters=activity.parameters,
                    timestamp=activity.timestamp,
                )
                session.add(scar_activity)

        # Commit activities immediately for real-time SSE
        await session.commit()

        # Check for completion (no new messages for 2 consecutive polls)
        stable_count = 0
    else:
        stable_count += 1

    if stable_count >= 2:
        break

    await asyncio.sleep(2.0)

# Aggregate output
output = "\n".join(msg.message for msg in all_messages)
```

**GOTCHA**: Must `await session.commit()` after each batch of activities for real-time visibility
**VALIDATE**: `uv run python -c "from src.services.scar_executor import execute_scar_command; print('✓ Executor imports valid')"`

### UPDATE src/services/scar_feed_service.py - Query activities

- **REFACTOR** `get_recent_scar_activity()` function (lines 18-95)
- **PATTERN**: Query `ScarActivity` table when verbosity >= 3, else use old logic
- **ADD** imports:
```python
from src.database.models import ScarActivity
```

**New Implementation**:
```python
async def get_recent_scar_activity(
    session: AsyncSession, project_id: UUID, limit: int = 50, verbosity_level: int = 2
) -> List[Dict]:
    """
    Get recent SCAR activity for a project.

    Verbosity levels:
    - 1 (low): Command-level status only
    - 2 (medium): Command status + output lines
    - 3 (high): Granular tool invocations
    """
    if verbosity_level >= 3:
        # High verbosity: Query ScarActivity table for granular activities
        query = (
            select(ScarActivity)
            .join(ScarCommandExecution, ScarActivity.execution_id == ScarCommandExecution.id)
            .where(ScarCommandExecution.project_id == project_id)
            .order_by(ScarActivity.timestamp.desc())
            .limit(limit)
        )

        result = await session.execute(query)
        activities = result.scalars().all()

        return [{
            "id": str(activity.id),
            "timestamp": activity.timestamp.isoformat(),
            "source": "scar",
            "activity_type": activity.activity_type,
            "tool_name": activity.tool_name,
            "message": activity.message,
            "parameters": activity.parameters or {},
            "output": activity.output,
        } for activity in reversed(activities)]

    else:
        # Low/Medium verbosity: Use existing logic (command-level)
        query = (
            select(ScarCommandExecution)
            .where(ScarCommandExecution.project_id == project_id)
            .order_by(desc(ScarCommandExecution.started_at))
            .limit(limit)
        )

        result = await session.execute(query)
        executions = result.scalars().all()

        activity_list = []
        for execution in reversed(executions):
            base_timestamp = execution.started_at or execution.completed_at or datetime.utcnow()
            base_timestamp_native = datetime.fromisoformat(base_timestamp.isoformat())

            activity_list.append({
                "id": str(execution.id),
                "timestamp": base_timestamp_native.isoformat(),
                "source": "scar",
                "message": f"{execution.command_type.value}: {execution.status.value}",
                "phase": execution.phase.name if execution.phase else None,
            })

            # If verbosity >= 2, add output lines as detail activities
            if verbosity_level >= 2 and execution.output:
                lines = execution.output.split("\n")
                for i, line in enumerate(lines):
                    if line.strip() and len(line.strip()) >= 3:
                        detail_timestamp = base_timestamp_native.replace(microsecond=i)
                        activity_list.append({
                            "id": f"{execution.id}-detail-{i}",
                            "timestamp": detail_timestamp.isoformat(),
                            "source": "scar-detail",
                            "message": line.strip(),
                            "phase": execution.phase.name if execution.phase else None,
                        })

        return activity_list
```

**GOTCHA**: Must maintain backward compatibility for verbosity levels 1-2
**VALIDATE**: `uv run python -c "from src.services.scar_feed_service import get_recent_scar_activity; print('✓ Feed service valid')"`

### UPDATE src/services/scar_feed_service.py - Stream activities incrementally

- **REFACTOR** `stream_scar_activity()` function (lines 98-180)
- **PATTERN**: Poll for new activities based on timestamp, handle verbosity level 3

**Updated Implementation**:
```python
async def stream_scar_activity(
    session: AsyncSession, project_id: UUID, verbosity_level: int = 2
) -> AsyncGenerator[Dict, None]:
    """Stream SCAR activity updates in real-time"""
    logger.info(f"Starting SCAR activity stream for project {project_id}, verbosity={verbosity_level}")

    last_timestamp = None

    # Get initial activities
    activities = await get_recent_scar_activity(session, project_id, limit=10, verbosity_level=verbosity_level)
    if activities:
        last_timestamp = activities[-1]["timestamp"]
        for activity in activities:
            yield activity

    # Poll for new activities
    while True:
        await asyncio.sleep(2)

        if verbosity_level >= 3:
            # Poll ScarActivity table
            if last_timestamp:
                last_dt = datetime.fromisoformat(last_timestamp)
                query = (
                    select(ScarActivity)
                    .join(ScarCommandExecution, ScarActivity.execution_id == ScarCommandExecution.id)
                    .where(
                        ScarCommandExecution.project_id == project_id,
                        ScarActivity.timestamp > last_dt,
                    )
                    .order_by(ScarActivity.timestamp.asc())
                )
            else:
                query = (
                    select(ScarActivity)
                    .join(ScarCommandExecution, ScarActivity.execution_id == ScarCommandExecution.id)
                    .where(ScarCommandExecution.project_id == project_id)
                    .order_by(ScarActivity.timestamp.desc())
                    .limit(1)
                )

            result = await session.execute(query)
            new_activities = result.scalars().all()

            for activity in new_activities:
                activity_dict = {
                    "id": str(activity.id),
                    "timestamp": activity.timestamp.isoformat(),
                    "source": "scar",
                    "activity_type": activity.activity_type,
                    "tool_name": activity.tool_name,
                    "message": activity.message,
                    "parameters": activity.parameters or {},
                    "output": activity.output,
                }
                last_timestamp = activity_dict["timestamp"]
                yield activity_dict

        else:
            # Poll ScarCommandExecution table (existing logic)
            if last_timestamp:
                last_dt = datetime.fromisoformat(last_timestamp)
                query = (
                    select(ScarCommandExecution)
                    .where(
                        ScarCommandExecution.project_id == project_id,
                        ScarCommandExecution.started_at > last_dt,
                    )
                    .order_by(ScarCommandExecution.started_at.asc())
                )
            else:
                query = (
                    select(ScarCommandExecution)
                    .where(ScarCommandExecution.project_id == project_id)
                    .order_by(desc(ScarCommandExecution.started_at))
                    .limit(1)
                )

            result = await session.execute(query)
            new_executions = result.scalars().all()

            for execution in new_executions:
                activity_dict = {
                    "id": str(execution.id),
                    "timestamp": execution.started_at.isoformat() if execution.started_at else datetime.utcnow().isoformat(),
                    "source": "scar",
                    "message": f"{execution.command_type.value}: {execution.status.value}",
                    "phase": execution.phase.name if execution.phase else None,
                }
                last_timestamp = activity_dict["timestamp"]
                yield activity_dict
```

**GOTCHA**: Must handle both verbosity levels with different query logic
**VALIDATE**: `uv run python -c "from src.services.scar_feed_service import stream_scar_activity; print('✓ Stream function valid')"`

### UPDATE frontend/src/components/RightPanel/ScarActivityFeed.tsx - Enhanced icons

- **REFACTOR** `getSourceColor()` and icon mapping (lines 18-56)
- **ADD** activity type detection
- **PATTERN**: Map `activity_type` field to specific icons

**Enhanced Implementation**:
```typescript
const getActivityIcon = (activity: ScarActivity) => {
  // Use activity_type if available (verbosity 3)
  if (activity.activity_type) {
    switch (activity.activity_type) {
      case 'bash_command': return '🔧';
      case 'file_read': return '📖';
      case 'file_write': return '📝';
      case 'file_edit': return '✏️';
      case 'grep_search': return '🔍';
      case 'glob_search': return '📂';
      case 'task_spawn': return '🤖';
      case 'agent_response': return '⚡';
      default: return '•';
    }
  }

  // Fallback: Parse message content (verbosity 1-2)
  const msg = activity.message.toLowerCase();
  if (msg.includes('bash:') || msg.includes('git ') || msg.includes('npm ')) return '🔧';
  if (msg.includes('read') || msg.includes('reading')) return '📖';
  if (msg.includes('write') || msg.includes('writing')) return '📝';
  if (msg.includes('edit')) return '✏️';
  if (msg.includes('search') || msg.includes('grep')) return '🔍';
  return '•';
};

// Add collapsible details for parameters
const ActivityDetails: React.FC<{ activity: ScarActivity }> = ({ activity }) => {
  const [expanded, setExpanded] = useState(false);

  if (!activity.parameters || Object.keys(activity.parameters).length === 0) {
    return null;
  }

  return (
    <div className="activity-details">
      <button onClick={() => setExpanded(!expanded)}>
        {expanded ? '▼' : '▶'} Details
      </button>
      {expanded && (
        <pre className="parameters">
          {JSON.stringify(activity.parameters, null, 2)}
        </pre>
      )}
    </div>
  );
};
```

**GOTCHA**: Must handle both old format (message parsing) and new format (activity_type field)
**VALIDATE**: Manual testing in browser after backend implementation

### CREATE tests/unit/services/test_scar_message_parser.py - Parser tests

- **IMPLEMENT**: Comprehensive unit tests for message parser
- **PATTERN**: Parametrized tests for each tool type
- **VALIDATE**: `pytest tests/unit/services/test_scar_message_parser.py -v`

**Test Implementation**:
```python
"""Tests for SCAR message parser"""

import pytest
from datetime import datetime
from src.services.scar_message_parser import ScarMessageParser, ParsedActivity


class TestScarMessageParser:

    def test_parse_bash_command(self):
        """Test parsing bash command"""
        message = "🔧 BASH\ngit ls-files"
        activities = ScarMessageParser.parse_message(message)

        assert len(activities) == 1
        assert activities[0].activity_type == "bash_command"
        assert activities[0].tool_name == "bash"
        assert activities[0].parameters["command"] == "git ls-files"

    def test_parse_file_read(self):
        """Test parsing file read"""
        message = "📖 READ\nReading: src/main.py"
        activities = ScarMessageParser.parse_message(message)

        assert len(activities) == 1
        assert activities[0].activity_type == "file_read"
        assert activities[0].tool_name == "read"
        assert activities[0].parameters["file_path"] == "src/main.py"

    def test_parse_multiple_activities(self):
        """Test parsing multiple activities"""
        message = """🔧 BASH
git status

📖 READ
Reading: README.md

✏️ EDIT
Editing: src/config.py"""

        activities = ScarMessageParser.parse_message(message)

        assert len(activities) == 3
        assert activities[0].activity_type == "bash_command"
        assert activities[1].activity_type == "file_read"
        assert activities[2].activity_type == "file_edit"

    def test_parse_empty_message(self):
        """Test parsing empty message"""
        activities = ScarMessageParser.parse_message("")
        assert len(activities) == 0

    def test_parse_message_without_emojis(self):
        """Test parsing message without tool emojis"""
        message = "Just some regular text"
        activities = ScarMessageParser.parse_message(message)
        assert len(activities) == 0

    @pytest.mark.parametrize("emoji,expected_type,expected_tool", [
        ("🔧", "bash_command", "bash"),
        ("📖", "file_read", "read"),
        ("✏️", "file_edit", "edit"),
        ("📝", "file_write", "write"),
        ("🔍", "grep_search", "grep"),
        ("📂", "glob_search", "glob"),
        ("🤖", "task_spawn", "task"),
        ("⚡", "agent_response", None),
    ])
    def test_all_emoji_types(self, emoji, expected_type, expected_tool):
        """Test all supported emoji types"""
        message = f"{emoji} TEST\nSome content"
        activities = ScarMessageParser.parse_message(message)

        assert len(activities) == 1
        assert activities[0].activity_type == expected_type
        assert activities[0].tool_name == expected_tool
```

**VALIDATE**: `pytest tests/unit/services/test_scar_message_parser.py -v --tb=short`

### UPDATE tests/services/test_scar_executor.py - Test activity creation

- **ADD** test for activity creation during execution
- **PATTERN**: Mock SCAR client, verify activities in database

**New Test**:
```python
@pytest.mark.asyncio
async def test_execute_command_creates_activities(db_session, mocker):
    """Test that command execution creates granular activities"""
    # Create project
    project = Project(
        name="Test Project",
        status=ProjectStatus.PLANNING,
        github_repo_url="https://github.com/test/repo",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Mock SCAR client to return messages with tool indicators
    mock_messages = [
        ScarMessage(
            message="🔧 BASH\ngit status",
            timestamp=datetime.utcnow(),
            direction="sent"
        ),
        ScarMessage(
            message="📖 READ\nReading: README.md",
            timestamp=datetime.utcnow(),
            direction="sent"
        ),
    ]

    mocker.patch.object(
        ScarClient,
        'wait_for_completion',
        return_value=mock_messages
    )

    # Execute command
    result = await execute_scar_command(db_session, project.id, ScarCommand.PRIME)

    assert result.success is True

    # Query activities
    from src.database.models import ScarActivity
    activity_query = select(ScarActivity).join(ScarCommandExecution)
    activity_result = await db_session.execute(activity_query)
    activities = activity_result.scalars().all()

    assert len(activities) >= 2
    assert any(a.activity_type == "bash_command" for a in activities)
    assert any(a.activity_type == "file_read" for a in activities)
```

**VALIDATE**: `pytest tests/services/test_scar_executor.py::test_execute_command_creates_activities -v`

---

## TESTING STRATEGY

### Unit Tests

**Parser Tests** (`tests/unit/services/test_scar_message_parser.py`):
- All emoji types (bash, read, write, edit, grep, glob, task, response)
- Multiple activities in one message
- Edge cases (empty message, no emojis, malformed input)
- Parameter extraction accuracy
- Coverage target: ≥ 95%

**Model Tests**:
- `ScarActivity` CRUD operations
- Relationship with `ScarCommandExecution`
- Cascade delete behavior

### Integration Tests

**Executor Tests** (`tests/services/test_scar_executor.py`):
- Activity creation during execution
- Incremental commit behavior
- Backward compatibility (verbosity levels 1-2)

**Feed Service Tests**:
- Query activities at verbosity level 3
- Timestamp-based polling
- Activity ordering

### Manual Testing

**SSE Feed Testing**:
1. Start backend: `uv run uvicorn src.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Create project with GitHub repo
4. Execute `/command-invoke prime`
5. Switch verbosity to "High" in UI
6. Verify activities stream in real-time with icons
7. Test verbosity level switching (Low → Medium → High)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Import Validation (CRITICAL)

```bash
uv run python -c "from src.services.scar_message_parser import ScarMessageParser; print('✓ Parser imports valid')"
uv run python -c "from src.database.models import ScarActivity; print('✓ Model imports valid')"
uv run python -c "from src.services.scar_feed_service import get_recent_scar_activity, stream_scar_activity; print('✓ Feed service imports valid')"
```

**Expected:** No ModuleNotFoundError or ImportError

### Level 2: Database Migration

```bash
alembic upgrade head
uv run python -c "from sqlalchemy import inspect; from src.database.connection import sync_engine; assert 'scar_activities' in inspect(sync_engine).get_table_names(); print('✓ Migration applied')"
```

**Expected:** Table `scar_activities` exists with correct schema

### Level 3: Unit Tests

```bash
pytest tests/unit/services/test_scar_message_parser.py -v
```

**Expected:** All parser tests pass (≥8 tests)

### Level 4: Integration Tests

```bash
pytest tests/services/test_scar_executor.py -v
```

**Expected:** All executor tests pass including new activity creation test

### Level 5: Full Test Suite

```bash
pytest tests/ -v --tb=short
```

**Expected:** All tests pass, no regressions

### Level 6: SSE Feed Manual Test

```bash
# Terminal 1: Start backend
uv run uvicorn src.main:app --reload

# Terminal 2: Test SSE endpoint
curl -N "http://localhost:8000/api/sse/scar/{project_id}?verbosity=3"
```

**Expected:** SSE stream connects, activities flow as JSON

---

## ACCEPTANCE CRITERIA

- [ ] `ScarActivity` model created with proper indexes and relationships
- [ ] `ScarMessageParser` correctly parses all tool types (bash, read, write, edit, grep, glob, task)
- [ ] Activities created incrementally during SCAR command execution
- [ ] Activities committed immediately for real-time SSE visibility
- [ ] SSE feed queries `ScarActivity` table at verbosity level 3
- [ ] SSE feed maintains backward compatibility at verbosity levels 1-2
- [ ] Frontend displays activity-specific icons based on `activity_type`
- [ ] Frontend shows collapsible details for tool parameters
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage ≥ 90% for parser module
- [ ] Integration tests verify end-to-end activity creation and streaming
- [ ] No regressions in existing SCAR execution functionality

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order (top to bottom)
- [ ] Each task validated immediately after completion
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Database migration runs cleanly (up and down)
- [ ] Manual SSE feed testing confirms real-time streaming
- [ ] Verbosity level switching works correctly (1, 2, 3)
- [ ] Frontend displays activities with correct icons
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability

---

## NOTES

### Design Decisions

**Why parse text messages instead of structured API?**
- SCAR Test Adapter API returns plain text messages, not structured tool invocations
- Emoji-based parsing is reliable because SCAR follows consistent formatting patterns
- Alternative would require SCAR API changes (out of scope for this feature)

**Why separate ScarActivity table?**
- Enables efficient timestamp-based polling for SSE
- Allows rich frontend rendering (icons, parameters, collapsible details)
- Simplifies debugging (each tool invocation is a separate record)
- Scales better than parsing aggregated text on every SSE poll

**Why verbosity level 3 for detailed activities?**
- Backward compatibility: existing users expect levels 1-2 behavior
- Performance: granular activities increase database writes and SSE payload size
- User choice: power users opt-in to verbosity level 3 when they need detail

**Why incremental commits during execution?**
- Real-time visibility: activities appear in SSE feed as they happen
- Matches Claude Code CLI UX: users see progress incrementally
- Trade-off: More database transactions, but acceptable for user experience

### Trade-offs

**Pros**:
- ✅ Granular visibility into SCAR execution
- ✅ Real-time activity streaming
- ✅ Activity history preserved in database
- ✅ Backward compatible
- ✅ No SCAR API changes required

**Cons**:
- ⚠️ Text parsing is less robust than structured API
- ⚠️ Increased database writes (one insert per activity)
- ⚠️ Emoji detection could break if SCAR changes format
- ⚠️ Larger SSE payload at verbosity level 3

### Future Enhancements

**Possible improvements** (out of scope for this feature):
- Activity grouping by execution in frontend
- Activity search/filter by tool type
- Activity replay (re-run specific tool invocations)
- SCAR API enhancement to provide structured tool events (eliminates parsing)
- WebSocket alternative to SSE for bidirectional communication

### Research Sources

- `.agents/reference/streaming-modes.md` - SCAR tool formatting patterns
- `.agents/examples/claude-telegram-bot/README.md` - Example SCAR output
- `src/scar/client.py` - SCAR HTTP API patterns
- `src/database/models.py` - Database model conventions
- `src/services/scar_feed_service.py` - SSE feed patterns
