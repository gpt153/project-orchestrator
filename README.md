# Project Orchestrator

> AI agent that helps non-coders build software projects by managing workflow between users and SCAR

## What Is This?

An AI-powered project management agent that translates natural language conversations into structured development workflows. Built to help non-technical people turn their ideas into working software.

## Vision

See the complete vision document: [`.agents/visions/project-orchestrator.md`](.agents/visions/project-orchestrator.md)

## Status

🚧 **In Development** - Currently implementing web interface

## Quick Start

### Backend API

1. Install Python dependencies (requires Python 3.11+):
   ```bash
   pip install -e .
   ```

2. Set up your environment:
   ```bash
   cp .env.example .env
   # Edit .env with your database URL
   ```

3. Run the backend server:
   ```bash
   python -m src.main
   ```

The API will be available at `http://localhost:8000`

### Frontend Web UI

1. Install Node.js dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

The web UI will be available at `http://localhost:5173`

### Features

- **Backend API**: FastAPI-based REST API with WebSocket and SSE support
- **Web Interface** (In Progress):
  - Left Panel: Project navigator with tree structure
  - Middle Panel: Chat interface with @po (no @mention required)
  - Right Panel: Real-time SCAR activity feed

## How It Works

```
You (natural language)
  ↓
Project Orchestrator (this project)
  ↓
SCAR (remote coding agent)
  ↓
Working Code
```

## Development Workflow

1. **Vision** → `.agents/visions/` - Non-technical project description
2. **PRD** → `docs/PRD.md` - Detailed requirements
3. **Plan** → `.agents/plans/` - Technical implementation plan
4. **Execute** → Actual code implementation

## Repository Structure

```
.agents/
├── visions/           # Non-technical vision documents
├── plans/             # Technical implementation plans
└── commands/          # Custom workflow commands
src/
├── api/               # FastAPI endpoints (REST, WebSocket, SSE)
├── database/          # SQLAlchemy models and connection
├── services/          # Business logic and service layer
└── main.py            # FastAPI application entry point
frontend/
├── src/
│   ├── components/    # React components (3-panel layout)
│   ├── hooks/         # Custom React hooks (WebSocket, SSE)
│   ├── services/      # API client services
│   └── types/         # TypeScript type definitions
└── package.json       # Node.js dependencies
tests/                 # Pytest tests for backend
```

## Contributing

This is a learning project built using AI-assisted development. Watch the Issues tab to see how it's built!

## License

MIT
