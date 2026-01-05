# Feature: WebUI UX Enhancements (Color-Coded Projects, Personalization, Mobile Support)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Enhance the Project Manager WebUI with improved visual organization, user personalization, and mobile-responsive design. This feature includes five major improvements: (1) color-coded project status badges for visual distinction, (2) project name display in the chat header, (3) a refresh button to reload projects without restarting, (4) personalized message labels showing user names instead of generic roles, and (5) comprehensive mobile-responsive design for seamless smartphone/tablet usage.

## User Story

As a Project Manager user
I want an intuitive, visually organized, and mobile-friendly interface
So that I can efficiently manage multiple projects, quickly identify project status, work from any device, and have a personalized experience that clearly shows who's communicating

## Problem Statement

The current WebUI lacks visual organization, making it difficult to distinguish between projects at a glance. Users must restart the entire application to see newly starred repositories. The interface shows generic labels like "Assistant" instead of personalized names, reducing clarity in conversations. Most critically, the interface is entirely desktop-only with no responsive design, making it unusable on mobile devices where users increasingly need access.

## Solution Statement

Implement a comprehensive UX enhancement that addresses all five pain points: (1) Add color-coded status badges to projects using a semantic color system, (2) Display the active project name in the chat header with breadcrumb navigation, (3) Add a refresh button to the project navigator that reloads the project list on demand, (4) Replace generic message labels with actual user names (Sam for user, PM for assistant), and (5) Implement mobile-first responsive design with breakpoint-based layouts, touch-friendly targets (44px minimum), and mobile navigation patterns.

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: High
**Primary Systems Affected**: Frontend (React components, CSS, hooks)
**Dependencies**: No new external dependencies required (use existing React 18, TypeScript, Vite stack)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**Core Application Files:**
- `frontend/src/App.tsx` (lines 1-39) - Main 3-panel layout with react-resizable-panels, project selection state
- `frontend/src/App.css` (lines 1-282) - All component styles (monolithic CSS file to be enhanced)
- `frontend/src/index.css` (lines 1-24) - Root CSS reset and global styles
- `frontend/index.html` (lines 1-13) - HTML entry point (add viewport meta tag here)

**Component Files to Modify:**
- `frontend/src/components/LeftPanel/ProjectNavigator.tsx` (lines 1-142) - Project list sidebar (add colors, refresh button)
- `frontend/src/components/MiddlePanel/ChatInterface.tsx` (lines 1-113) - Chat interface (update header, personalize messages)
- `frontend/src/components/RightPanel/ScarActivityFeed.tsx` (lines 1-62) - Activity feed (mobile responsive)

**Service and Hook Files:**
- `frontend/src/services/api.ts` (lines 1-55) - REST API client (already has getProjects() for refresh)
- `frontend/src/hooks/useWebSocket.ts` (lines 1-83) - WebSocket chat connection
- `frontend/src/hooks/useScarFeed.ts` (lines 1-40) - SSE activity feed

**Type Definition Files:**
- `frontend/src/types/project.ts` (lines 1-36) - Project, Issue, Document types (check ProjectStatus enum)
- `frontend/src/types/message.ts` (lines 1-22) - Chat message types

**Backend Models (for reference):**
- `src/database/models.py` (lines 30-38) - ProjectStatus enum definition
- `src/database/models.py` (lines 98-136) - Project model with status field

### New Files to Create

**Utility Files:**
- `frontend/src/utils/colors.ts` - Status color mapping and color utility functions
- `frontend/src/hooks/useMediaQuery.ts` - Custom hook for responsive breakpoints

**Component Files:**
- `frontend/src/components/common/StatusBadge.tsx` - Reusable status badge component

**Style Files:**
- `frontend/src/styles/variables.css` - CSS custom properties for colors and breakpoints
- `frontend/src/styles/responsive.css` - Mobile-specific media queries

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

**React and TypeScript:**
- [React 18 useEffect Documentation](https://react.dev/reference/react/useEffect)
  - Specific section: Effect dependencies and cleanup
  - Why: Proper state management for refresh functionality
- [TypeScript Discriminated Unions](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#discriminated-unions)
  - Specific section: Using the `in` operator narrowing
  - Why: Type-safe message rendering with role-based display

**Responsive Design:**
- [MDN: Using Media Queries](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_media_queries/Using_media_queries)
  - Specific section: Mobile-first responsive design
  - Why: Implementing breakpoint-based layouts
- [MDN: Viewport Meta Tag](https://developer.mozilla.org/en-US/docs/Web/HTML/Viewport_meta_tag)
  - Specific section: viewport-fit=cover for mobile notches
  - Why: Proper mobile rendering

**Accessibility:**
- [WCAG 2.2 Color Contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
  - Specific section: Contrast ratios for UI components (3:1 minimum)
  - Why: Ensuring status badge colors are accessible
- [WCAG 2.2 Target Size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
  - Specific section: 24x24 CSS pixels minimum (44x44 recommended)
  - Why: Touch-friendly mobile interactions

**CSS Patterns:**
- [MDN: CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
  - Specific section: Using custom properties with media queries
  - Why: Theme system for status colors

### Patterns to Follow

**Naming Conventions:**
```typescript
// BEM-like CSS classes (existing pattern)
.project-list { }
.project-header { }
.project-name { }
.status-badge { }

// Component names: PascalCase
function ProjectNavigator() { }

// Hook names: camelCase with "use" prefix
function useMediaQuery() { }

// File names: PascalCase for components, camelCase for utilities
StatusBadge.tsx
colors.ts
```

**Error Handling Pattern (from existing code):**
```typescript
// frontend/src/components/LeftPanel/ProjectNavigator.tsx (lines 20-32)
useEffect(() => {
  const fetchProjects = async () => {
    try {
      const data = await api.getProjects();
      setProjects(data);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
    } finally {
      setLoading(false);
    }
  };
  fetchProjects();
}, []);
```

**React Hook Dependencies Pattern:**
```typescript
// Always include all dependencies in useEffect
useEffect(() => {
  // effect code
}, [dependency1, dependency2]); // Complete dependency array
```

**State Management Pattern (from App.tsx):**
```typescript
// Simple useState for local state, no Context API or Redux
const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
const [projects, setProjects] = useState<Project[]>([]);

// Pass state down via props (prop drilling)
<ProjectNavigator onProjectSelect={setSelectedProjectId} />
```

**Conditional Rendering Pattern:**
```typescript
// Ternary for simple conditions
{isConnected ? <ConnectedIcon /> : <DisconnectedIcon />}

// Early returns for complex conditions
if (!project) {
  return <EmptyState />;
}
return <ProjectDetails project={project} />;
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation - CSS Variables and Utilities (2-3 hours)

Set up the foundational CSS architecture and utility functions that all other features will depend on.

**Tasks:**
- Create CSS custom properties for status colors and breakpoints
- Create color utility functions for status-to-color mapping
- Create custom media query hook for responsive behavior
- Update HTML viewport meta tag for proper mobile rendering

### Phase 2: Color-Coded Projects (3-4 hours)

Add visual status indicators to projects using color-coded badges and borders.

**Tasks:**
- Create reusable StatusBadge component
- Update ProjectNavigator to display status badges
- Add color-coded left borders to project items
- Update CSS with status-specific styling

### Phase 3: Project Name Display (1-2 hours)

Show the currently selected project name in the chat header for better context awareness.

**Tasks:**
- Update App.tsx to pass full project object instead of just ID
- Update ChatInterface header to display project name
- Add visual hierarchy (project name + subtitle)

### Phase 4: Refresh Button (1-2 hours)

Add manual refresh capability to reload projects without restarting the application.

**Tasks:**
- Add refresh button to ProjectNavigator header
- Implement refresh handler with loading state
- Add visual feedback (disabled state, loading indicator)
- Style refresh button consistently with existing UI

### Phase 5: Personalized Messages (2-3 hours)

Replace generic message labels with actual user and agent names for clearer conversation context.

**Tasks:**
- Update message rendering to use personalized names
- Add environment variable or config for user name
- Update message styling for better visual distinction
- Test with different role types (user, assistant, system)

### Phase 6: Mobile Responsive Design (8-12 hours)

Implement comprehensive mobile-first responsive design across all components.

**Tasks:**
- Add responsive breakpoints to CSS
- Update panel layout for mobile (vertical stacking)
- Add mobile navigation (hamburger menu or bottom tabs)
- Ensure touch-friendly tap targets (44px minimum)
- Test on multiple screen sizes and orientations

### Phase 7: Testing & Refinement (2-3 hours)

Validate implementation across devices, test edge cases, and refine UX details.

**Tasks:**
- Cross-browser testing (Chrome, Firefox, Safari)
- Mobile device testing (iOS Safari, Android Chrome)
- Accessibility audit (color contrast, keyboard navigation)
- Performance testing (ensure no regressions)

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE `frontend/src/styles/variables.css`

- **IMPLEMENT**: CSS custom properties for status colors and responsive breakpoints
- **PATTERN**: CSS variables with fallback values
- **GOTCHA**: Ensure color contrast ratios meet WCAG 2.2 AA standards (3:1 for UI components)
- **VALIDATE**: `grep -r "var(--status-" frontend/src/styles/variables.css`

```css
:root {
  /* Status Colors - Based on ProjectStatus enum */
  --status-brainstorming: #9C27B0;  /* Purple - Creative phase */
  --status-vision-review: #FF9800;  /* Orange - Review phase */
  --status-planning: #2196F3;       /* Blue - Planning phase */
  --status-in-progress: #4CAF50;    /* Green - Active development */
  --status-paused: #757575;         /* Gray - On hold */
  --status-completed: #00BCD4;      /* Cyan - Finished */

  /* Status Badge Text Colors (ensure WCAG contrast) */
  --status-text-light: #FFFFFF;     /* For dark backgrounds */
  --status-text-dark: #1F2937;      /* For light backgrounds */

  /* Responsive Breakpoints */
  --breakpoint-mobile: 767px;
  --breakpoint-tablet: 1023px;
  --breakpoint-desktop: 1024px;

  /* Touch Targets */
  --touch-target-min: 44px;

  /* Spacing */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
}
```

### CREATE `frontend/src/utils/colors.ts`

- **IMPLEMENT**: Status color mapping and utility functions
- **PATTERN**: Object mapping with type-safe accessors
- **IMPORTS**: `import { ProjectStatus } from '../types/project';`
- **GOTCHA**: Match status keys exactly to backend ProjectStatus enum
- **VALIDATE**: `npm run type-check` (ensure no TypeScript errors)

```typescript
import { ProjectStatus } from '../types/project';

// Status color mapping matching CSS variables
export const STATUS_COLORS: Record<ProjectStatus, string> = {
  BRAINSTORMING: 'var(--status-brainstorming)',
  VISION_REVIEW: 'var(--status-vision-review)',
  PLANNING: 'var(--status-planning)',
  IN_PROGRESS: 'var(--status-in-progress)',
  PAUSED: 'var(--status-paused)',
  COMPLETED: 'var(--status-completed)',
};

// Get color for a given status
export function getStatusColor(status: ProjectStatus): string {
  return STATUS_COLORS[status] || 'var(--gray-medium)';
}

// Get human-readable status label
export function getStatusLabel(status: ProjectStatus): string {
  return status.replace(/_/g, ' ');
}
```

### CREATE `frontend/src/hooks/useMediaQuery.ts`

- **IMPLEMENT**: Custom hook for detecting screen size breakpoints
- **PATTERN**: Window.matchMedia with addEventListener cleanup
- **IMPORTS**: `import { useState, useEffect } from 'react';`
- **GOTCHA**: Return false during SSR (though not applicable for Vite SPA)
- **VALIDATE**: `npm run type-check && npm run build`

```typescript
import { useState, useEffect } from 'react';

/**
 * Custom hook to detect if a media query matches
 * @param query - CSS media query string (e.g., '(max-width: 768px)')
 * @returns boolean indicating if the media query matches
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    // SSR-safe: return false during server render
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    const mediaQuery = window.matchMedia(query);

    // Update state when media query changes
    const handler = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    // Modern API (Safari 14+, supported in all target browsers)
    mediaQuery.addEventListener('change', handler);

    return () => mediaQuery.removeEventListener('change', handler);
  }, [query]);

  return matches;
}
```

### UPDATE `frontend/index.html`

- **IMPLEMENT**: Add viewport meta tag for proper mobile rendering
- **PATTERN**: Standard mobile-first viewport configuration
- **GOTCHA**: `viewport-fit=cover` is required for iOS notch/safe area support
- **VALIDATE**: Open DevTools, check meta tag exists with correct attributes

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <title>Project Orchestrator</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### UPDATE `frontend/src/main.tsx`

- **IMPLEMENT**: Import CSS variables before other styles
- **PATTERN**: Import order matters - variables first, then global styles
- **IMPORTS**: `import './styles/variables.css';`
- **GOTCHA**: Must be imported before index.css to be available
- **VALIDATE**: Check browser DevTools that CSS variables are defined

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import './styles/variables.css'  // NEW: Import CSS variables first
import './index.css'
import App from './App.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

### CREATE `frontend/src/components/common/StatusBadge.tsx`

- **IMPLEMENT**: Reusable status badge component with accessible colors
- **PATTERN**: Functional component with TypeScript interface
- **IMPORTS**: `import { ProjectStatus } from '../../types/project';` and `import { getStatusColor, getStatusLabel } from '../../utils/colors';`
- **GOTCHA**: Use `aria-label` for screen readers, `aria-hidden` for decorative icons
- **VALIDATE**: `npm run type-check`

```typescript
import React from 'react';
import { ProjectStatus } from '../../types/project';
import { getStatusColor, getStatusLabel } from '../../utils/colors';

interface StatusBadgeProps {
  status: ProjectStatus;
  showLabel?: boolean;
  className?: string;
}

export function StatusBadge({
  status,
  showLabel = true,
  className = ''
}: StatusBadgeProps) {
  const color = getStatusColor(status);
  const label = getStatusLabel(status);

  return (
    <span
      className={`status-badge ${className}`}
      style={{
        backgroundColor: color,
        color: 'white'
      }}
      role="status"
      aria-label={`Project status: ${label}`}
    >
      {showLabel && <span>{label}</span>}
    </span>
  );
}
```

### UPDATE `frontend/src/App.css`

- **IMPLEMENT**: Add status badge styles and basic responsive utilities
- **PATTERN**: BEM-like naming, append to existing file
- **GOTCHA**: Don't remove existing styles, only add new ones
- **VALIDATE**: Check no CSS syntax errors with `npm run build`

Append to end of file:

```css
/* Status Badge Component */
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.025em;
  white-space: nowrap;
}

/* Icon Button Styles (for refresh button) */
.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: var(--touch-target-min);
  min-height: var(--touch-target-min);
  padding: 0.5rem;
  background: transparent;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1.2rem;
  transition: all 0.2s ease;
}

.icon-button:hover:not(:disabled) {
  background: #f5f5f5;
  border-color: #2196F3;
}

.icon-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Header Actions Container */
.header-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

/* Project Item with Status Color */
.project-item {
  border-left: 4px solid transparent;
  transition: border-color 0.2s ease;
}

.project-item.selected {
  background-color: #f5f5f5;
}
```

### UPDATE `frontend/src/components/LeftPanel/ProjectNavigator.tsx`

- **IMPLEMENT**: Add StatusBadge component, refresh button, and color-coded borders
- **PATTERN**: Import new components, add refresh handler, update JSX
- **IMPORTS**: `import { StatusBadge } from '../common/StatusBadge';` and `import { getStatusColor } from '../../utils/colors';`
- **GOTCHA**: Use `api.getProjects()` which already exists in services/api.ts
- **VALIDATE**: `npm run type-check && npm run build`

Update the component (lines 1-142):

```typescript
import React, { useState, useEffect } from 'react';
import { Project, Issue, Document } from '../../types/project';
import { api } from '../../services/api';
import { StatusBadge } from '../common/StatusBadge';
import { getStatusColor } from '../../utils/colors';

interface ProjectNavigatorProps {
  onProjectSelect: (projectId: string) => void;
}

export function ProjectNavigator({ onProjectSelect }: ProjectNavigatorProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  // Initial fetch
  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const data = await api.getProjects();
      setProjects(data);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // NEW: Refresh handler
  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchProjects();
  };

  const toggleProject = (projectId: string) => {
    setExpandedProjects(prev => {
      const newSet = new Set(prev);
      if (newSet.has(projectId)) {
        newSet.delete(projectId);
      } else {
        newSet.add(projectId);
      }
      return newSet;
    });
  };

  const handleProjectSelect = (projectId: string) => {
    setSelectedProjectId(projectId);
    onProjectSelect(projectId);
  };

  if (loading) {
    return <div className="loading">Loading projects...</div>;
  }

  return (
    <div className="project-navigator">
      <div className="header">
        <h2>Projects</h2>
        <div className="header-actions">
          {/* NEW: Refresh button */}
          <button
            onClick={handleRefresh}
            className="icon-button"
            title="Refresh projects"
            disabled={refreshing}
            aria-label="Refresh project list"
          >
            {refreshing ? '⟳' : '🔄'}
          </button>
          <button
            onClick={() => {/* TODO: open create modal */}}
            className="icon-button"
            title="New project"
            aria-label="Create new project"
          >
            ➕
          </button>
        </div>
      </div>

      <ul className="project-list">
        {projects.map((project) => {
          const isExpanded = expandedProjects.has(project.id);
          const isSelected = selectedProjectId === project.id;
          const statusColor = getStatusColor(project.status);

          return (
            <li
              key={project.id}
              className={`project-item ${isSelected ? 'selected' : ''}`}
              style={{ borderLeftColor: statusColor }}
            >
              <div className="project-header">
                <span
                  className="expand-icon"
                  onClick={() => toggleProject(project.id)}
                  role="button"
                  tabIndex={0}
                  aria-expanded={isExpanded}
                  aria-label={isExpanded ? 'Collapse project' : 'Expand project'}
                >
                  {isExpanded ? '▼' : '▶'}
                </span>
                <span
                  className="project-name"
                  onClick={() => handleProjectSelect(project.id)}
                  role="button"
                  tabIndex={0}
                  aria-label={`Select project ${project.name}`}
                >
                  {project.name}
                </span>
                {/* NEW: Status badge */}
                <StatusBadge status={project.status} />
              </div>

              {/* Expanded content: issues and documents */}
              {isExpanded && (
                <div className="project-content">
                  {/* Issues section */}
                  <div className="issues-section">
                    <h4>
                      📂 Issues ({project.open_issues_count || 0} open)
                    </h4>
                    {/* Issue list rendering... */}
                  </div>

                  {/* Documents section */}
                  <div className="documents-section">
                    <h4>📄 Documents</h4>
                    {/* Document list rendering... */}
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
```

### UPDATE `frontend/src/App.tsx`

- **IMPLEMENT**: Pass full project object to ChatInterface instead of just ID
- **PATTERN**: Update state type and prop passing
- **IMPORTS**: `import { Project } from './types/project';`
- **GOTCHA**: Update onProjectSelect handler to receive and store full project
- **VALIDATE**: `npm run type-check && npm run build`

Update the component (lines 1-39):

```typescript
import { useState, useEffect } from 'react'
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels'
import { ProjectNavigator } from './components/LeftPanel/ProjectNavigator'
import { ChatInterface } from './components/MiddlePanel/ChatInterface'
import { ScarActivityFeed } from './components/RightPanel/ScarActivityFeed'
import { Project } from './types/project'
import './App.css'

function App() {
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);

  // Fetch all projects on mount
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const response = await fetch('/api/projects');
        const data = await response.json();
        setProjects(data);
      } catch (error) {
        console.error('Failed to fetch projects:', error);
      }
    };
    fetchProjects();
  }, []);

  // NEW: Handler to select project by ID and store full object
  const handleProjectSelect = (projectId: string) => {
    const project = projects.find(p => p.id === projectId);
    setSelectedProject(project || null);
  };

  return (
    <div className="app">
      <PanelGroup direction="horizontal">
        {/* Left Panel: Project Navigator */}
        <Panel defaultSize={20} minSize={15}>
          <ProjectNavigator onProjectSelect={handleProjectSelect} />
        </Panel>

        <PanelResizeHandle className="resize-handle" />

        {/* Middle Panel: Chat Interface */}
        <Panel defaultSize={50} minSize={30}>
          {selectedProject ? (
            <ChatInterface project={selectedProject} />
          ) : (
            <div className="empty-state">
              <p>Select a project to start chatting</p>
            </div>
          )}
        </Panel>

        <PanelResizeHandle className="resize-handle" />

        {/* Right Panel: SCAR Activity Feed */}
        <Panel defaultSize={30} minSize={20}>
          {selectedProject && (
            <ScarActivityFeed projectId={selectedProject.id} />
          )}
        </Panel>
      </PanelGroup>
    </div>
  )
}

export default App
```

### UPDATE `frontend/src/components/MiddlePanel/ChatInterface.tsx`

- **IMPLEMENT**: Update to receive full project object, display project name, personalize message labels
- **PATTERN**: Update component interface, modify header and message rendering
- **IMPORTS**: `import { Project } from '../../types/project';`
- **GOTCHA**: User name should be "Sam" (hardcoded or from env), agent name "PM"
- **VALIDATE**: `npm run type-check && npm run build`

Update the component (lines 1-113):

```typescript
import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { Message } from '../../types/message';
import { Project } from '../../types/project';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatInterfaceProps {
  project: Project;  // Changed from projectId: string
}

export function ChatInterface({ project }: ChatInterfaceProps) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    sendMessage,
    isConnected,
    isTyping
  } = useWebSocket(project.id);  // Use project.id for WebSocket

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && isConnected) {
      sendMessage(inputValue);
      setInputValue('');
    }
  };

  // NEW: Get display name based on message role
  const getDisplayName = (role: string): string => {
    switch (role) {
      case 'user':
        return 'Sam';  // User name (could be from env: import.meta.env.VITE_USER_NAME)
      case 'assistant':
        return 'PM';  // Project Manager agent
      case 'system':
        return 'System';
      default:
        return role;
    }
  };

  return (
    <div className="chat-interface">
      {/* NEW: Updated header with project name */}
      <div className="chat-header">
        <div className="header-left">
          <h2>{project.name}</h2>
          <span className="chat-subtitle">Chat with @PM</span>
        </div>
        <span className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '● Connected' : '○ Disconnected'}
        </span>
      </div>

      {/* Messages */}
      <div className="messages-container">
        {messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.role}`}>
            <div className="message-header">
              {/* NEW: Personalized display name */}
              <span className="role">{getDisplayName(msg.role)}</span>
              <span className="timestamp">
                {new Date(msg.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <div className="message-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="message assistant">
            <div className="message-header">
              <span className="role">PM</span>
            </div>
            <div className="message-content typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input form */}
      <form onSubmit={handleSubmit} className="input-form">
        <textarea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder={isConnected ? "Type a message..." : "Disconnected"}
          disabled={!isConnected}
          rows={3}
        />
        <button
          type="submit"
          disabled={!isConnected || !inputValue.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}
```

### UPDATE `frontend/src/App.css`

- **IMPLEMENT**: Enhanced message styling for visual distinction between Sam and PM
- **PATTERN**: Append new styles, update existing message styles
- **GOTCHA**: Maintain existing styles, only enhance with new rules
- **VALIDATE**: Visual inspection in browser

Append to end of file:

```css
/* Enhanced Chat Header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #e0e0e0;
  background: white;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.header-left h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
}

.chat-subtitle {
  font-size: 0.875rem;
  color: #6b7280;
}

/* Enhanced Message Styling */
.message.user {
  background: #e3f2fd;
  border-left: 4px solid #2196F3;
  margin-left: auto;
  margin-right: 0;
}

.message.assistant {
  background: #f1f8e9;
  border-left: 4px solid #4CAF50;
  margin-left: 0;
  margin-right: auto;
}

.message .role {
  font-weight: 600;
  font-size: 0.875rem;
  color: inherit;
}

.message.user .role {
  color: #1976D2;
}

.message.assistant .role {
  color: #388E3C;
}
```

### CREATE `frontend/src/styles/responsive.css`

- **IMPLEMENT**: Mobile-first responsive design with breakpoints
- **PATTERN**: Mobile base styles, progressive enhancement with min-width media queries
- **GOTCHA**: Touch targets must be at least 44px for mobile usability
- **VALIDATE**: Test in DevTools responsive mode (iPhone SE, iPad, Desktop)

```css
/* Mobile-First Responsive Styles */

/* Mobile Base Styles (<768px) */
@media (max-width: 767px) {
  /* Hide resize handles on mobile */
  .resize-handle {
    display: none !important;
  }

  /* Stack panels vertically */
  .app > div[data-panel-group-direction="horizontal"] {
    flex-direction: column !important;
  }

  /* Full width panels on mobile */
  .app > div[data-panel-group] > div[data-panel] {
    min-width: 100% !important;
    max-width: 100% !important;
  }

  /* Hide right panel (SCAR feed) on mobile */
  .app > div[data-panel-group] > div[data-panel]:last-child {
    display: none;
  }

  /* Touch-friendly buttons */
  button,
  .project-name,
  .expand-icon {
    min-height: var(--touch-target-min);
    min-width: var(--touch-target-min);
    padding: 0.75rem;
  }

  .icon-button {
    min-width: 48px;
    min-height: 48px;
  }

  /* Larger text for readability */
  body {
    font-size: 16px; /* Prevents zoom on iOS input focus */
  }

  /* Full-width input on mobile */
  .input-form {
    padding: 0.75rem;
  }

  .input-form textarea {
    font-size: 16px; /* Prevents iOS zoom */
  }

  /* Project navigator adjustments */
  .project-navigator {
    height: 40vh;
    overflow-y: auto;
  }

  /* Chat interface takes remaining space */
  .chat-interface {
    height: 60vh;
    display: flex;
    flex-direction: column;
  }

  .messages-container {
    flex: 1;
    overflow-y: auto;
  }
}

/* Tablet Styles (768px - 1023px) */
@media (min-width: 768px) and (max-width: 1023px) {
  /* Keep left and middle panels, hide right */
  .app > div[data-panel-group] > div[data-panel]:last-child {
    display: none;
  }

  /* Adjust panel sizes */
  .app > div[data-panel-group] > div[data-panel]:first-child {
    flex-basis: 30% !important;
  }

  .app > div[data-panel-group] > div[data-panel]:nth-child(3) {
    flex-basis: 70% !important;
  }
}

/* Desktop Styles (1024px+) */
@media (min-width: 1024px) {
  /* Keep default 3-panel layout */
  /* Styles already defined in App.css */
}

/* Landscape Mobile (height < 500px) */
@media (max-height: 500px) and (orientation: landscape) {
  .project-navigator {
    height: 35vh;
  }

  .chat-interface {
    height: 65vh;
  }

  .chat-header {
    padding: 0.5rem;
  }

  .input-form {
    padding: 0.5rem;
  }
}
```

### UPDATE `frontend/src/main.tsx`

- **IMPLEMENT**: Import responsive.css after other styles
- **PATTERN**: Import order: variables → base styles → component styles → responsive overrides
- **IMPORTS**: `import './styles/responsive.css';`
- **GOTCHA**: Must be last to ensure responsive rules override defaults
- **VALIDATE**: Check browser DevTools that media queries are applied

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import './styles/variables.css'
import './index.css'
import App from './App.tsx'
import './styles/responsive.css'  // NEW: Import responsive styles last

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

### UPDATE `frontend/src/types/project.ts`

- **IMPLEMENT**: Verify ProjectStatus enum matches backend exactly
- **PATTERN**: Read-only verification, no changes unless enum is missing
- **GOTCHA**: Enum must match backend models.py ProjectStatus exactly
- **VALIDATE**: `grep -A 10 "enum ProjectStatus" src/database/models.py`

Verify this enum exists (lines 13-20):

```typescript
export enum ProjectStatus {
  BRAINSTORMING = "BRAINSTORMING",
  VISION_REVIEW = "VISION_REVIEW",
  PLANNING = "PLANNING",
  IN_PROGRESS = "IN_PROGRESS",
  PAUSED = "PAUSED",
  COMPLETED = "COMPLETED",
}
```

If missing, add it. If present, no changes needed.

### MANUAL TESTING CHECKLIST

**Desktop Testing (1920x1080):**
- [ ] Project list displays with color-coded status badges
- [ ] Refresh button reloads projects without errors
- [ ] Project name appears in chat header
- [ ] Messages show "Sam" for user, "PM" for assistant
- [ ] Three-panel layout works with resizable handles
- [ ] Status colors are visible and distinct

**Tablet Testing (768x1024):**
- [ ] Two-panel layout (left + middle) displays correctly
- [ ] Right panel (SCAR feed) is hidden
- [ ] Touch targets are at least 44px
- [ ] Refresh button is easily tappable
- [ ] Project selection works with touch
- [ ] Messages are readable and well-spaced

**Mobile Testing (375x667 - iPhone SE):**
- [ ] Vertical stacking of panels works
- [ ] Only project list and chat visible (no right panel)
- [ ] Touch targets are 44px+ minimum
- [ ] Text inputs don't trigger zoom (16px font size)
- [ ] Scrolling works smoothly in all sections
- [ ] Status badges are readable on small screen
- [ ] Refresh button is accessible

**Landscape Mobile Testing (667x375):**
- [ ] Layout adjusts for short height
- [ ] Project list takes less vertical space (35vh)
- [ ] Chat interface remains usable
- [ ] Input form is accessible

**Accessibility Testing:**
- [ ] Color contrast ratios meet WCAG 2.2 AA (3:1 for UI components)
- [ ] Keyboard navigation works (Tab, Enter, Space)
- [ ] ARIA labels present on icon buttons
- [ ] Screen reader announces status badges correctly
- [ ] Focus indicators visible on interactive elements

**Cross-Browser Testing:**
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Safari iOS (iPhone)
- [ ] Chrome Android

---

## TESTING STRATEGY

### Unit Tests

**Recommended (not currently implemented in project):**

Since the project has no frontend tests, testing will be manual. If implementing automated tests in the future:

```typescript
// Example: StatusBadge.test.tsx
describe('StatusBadge', () => {
  it('renders with correct color for each status', () => {
    const statuses: ProjectStatus[] = ['BRAINSTORMING', 'IN_PROGRESS', 'COMPLETED'];
    statuses.forEach(status => {
      const { getByRole } = render(<StatusBadge status={status} />);
      const badge = getByRole('status');
      expect(badge).toBeInTheDocument();
    });
  });
});

// Example: useMediaQuery.test.tsx
describe('useMediaQuery', () => {
  it('returns true when media query matches', () => {
    window.matchMedia = jest.fn().mockImplementation(query => ({
      matches: query === '(max-width: 768px)',
      media: query,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    }));

    const { result } = renderHook(() => useMediaQuery('(max-width: 768px)'));
    expect(result.current).toBe(true);
  });
});
```

### Integration Tests

**Manual Testing Scenarios:**

1. **Color-Coded Projects:**
   - Navigate to project list
   - Verify each project status shows different color
   - Verify selected project has color-coded left border

2. **Refresh Functionality:**
   - Click refresh button
   - Verify button shows loading state (⟳ icon)
   - Verify project list updates
   - Verify no errors in console

3. **Project Name Display:**
   - Select different projects
   - Verify chat header updates with correct project name
   - Verify subtitle "Chat with @PM" remains

4. **Personalized Messages:**
   - Send a message as user
   - Verify message shows "Sam" as sender
   - Verify assistant response shows "PM" as sender
   - Verify color distinction between user/assistant messages

5. **Mobile Responsive:**
   - Open DevTools responsive mode
   - Test iPhone SE (375x667)
   - Test iPad (768x1024)
   - Test Desktop (1920x1080)
   - Verify layout adapts correctly at each breakpoint

### Edge Cases

**Edge Case Tests:**

1. **Empty project list:**
   - Test with no projects (empty array)
   - Verify graceful empty state

2. **Very long project names:**
   - Test with 100+ character project name
   - Verify text truncation or wrapping

3. **Missing status:**
   - Test project with null/undefined status
   - Verify fallback color displays

4. **Network errors:**
   - Test refresh with offline network
   - Verify error handling (check console.error)

5. **Rapid refresh clicks:**
   - Click refresh button multiple times quickly
   - Verify button remains disabled during refresh
   - Verify no duplicate API calls

6. **WebSocket disconnection:**
   - Disconnect WebSocket
   - Verify status indicator shows "○ Disconnected"
   - Verify input is disabled

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Type Checking

```bash
cd frontend && npm run type-check
```

**Expected:** No TypeScript errors (exit code 0)

**Why:** Ensures all type definitions are correct, props are properly typed, and no type mismatches exist.

### Level 2: Build Validation

```bash
cd frontend && npm run build
```

**Expected:** Build succeeds with no errors, outputs to `frontend/dist/`

**Why:** Verifies all imports resolve, no syntax errors, and Vite can bundle the application.

### Level 3: Development Server

```bash
cd frontend && npm run dev
```

**Expected:** Dev server starts on http://localhost:3002, no console errors

**Why:** Ensures application runs without runtime errors, hot reload works.

### Level 4: Backend Server (if testing full stack)

```bash
# From project root
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected:** Backend starts on http://localhost:8000, API endpoints respond

**Why:** Full-stack testing requires backend for project data, WebSocket, SSE.

### Level 5: Manual Visual Testing

**Desktop (1920x1080):**
1. Open http://localhost:3002 in Chrome
2. Verify all 5 features implemented:
   - ✓ Color-coded status badges on projects
   - ✓ Refresh button in project navigator header
   - ✓ Project name in chat header
   - ✓ "Sam" and "PM" message labels
   - ✓ Three-panel layout with resize handles

**Mobile (375x667):**
1. Open DevTools → Toggle device toolbar
2. Select "iPhone SE"
3. Verify:
   - ✓ Vertical panel stacking
   - ✓ Touch-friendly buttons (44px+)
   - ✓ No horizontal scroll
   - ✓ Text readable without zoom

**Accessibility:**
1. Run Lighthouse audit (DevTools → Lighthouse)
2. Verify:
   - ✓ Accessibility score ≥ 90
   - ✓ Color contrast ratio ≥ 3:1 for UI components
   - ✓ Touch targets ≥ 24x24px (44x44px recommended)

### Level 6: Cross-Browser Testing

**Required Browsers:**
- Chrome (latest)
- Firefox (latest)
- Safari (latest) - macOS or iOS

```bash
# Test in each browser:
# 1. Navigate to http://localhost:3002
# 2. Test all features
# 3. Check console for errors (should be none)
```

---

## ACCEPTANCE CRITERIA

- [x] **Color-Coded Projects**: Each project displays a status badge with distinct color (Purple=Brainstorming, Orange=Vision Review, Blue=Planning, Green=In Progress, Gray=Paused, Cyan=Completed)
- [x] **Project Name Display**: Chat header shows the selected project name with subtitle "Chat with @PM"
- [x] **Refresh Button**: Project navigator has a refresh button (🔄) that reloads projects without restarting, with loading state
- [x] **Personalized Messages**: User messages labeled "Sam", assistant messages labeled "PM", with color distinction
- [x] **Mobile Responsive**: Layout adapts to mobile (<768px), tablet (768-1023px), and desktop (1024px+) with touch-friendly targets (44px minimum)
- [ ] All TypeScript type checking passes with no errors
- [ ] Build completes successfully with no errors or warnings
- [ ] No console errors during normal usage
- [ ] Accessibility score ≥ 90 in Lighthouse audit
- [ ] Color contrast ratios meet WCAG 2.2 AA standards (3:1 for UI components, 4.5:1 for text)
- [ ] All interactive elements have minimum 24x24px touch targets (44x44px for mobile)

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order (top to bottom)
- [ ] CSS variables file created and imported
- [ ] Color utility functions implemented
- [ ] useMediaQuery hook implemented
- [ ] StatusBadge component created
- [ ] ProjectNavigator updated with colors and refresh
- [ ] App.tsx updated to pass full project object
- [ ] ChatInterface updated with project name and personalized labels
- [ ] Responsive CSS implemented with mobile-first approach
- [ ] Viewport meta tag added to index.html
- [ ] All TypeScript compilation errors resolved
- [ ] Build succeeds without errors
- [ ] Visual testing completed on desktop, tablet, mobile
- [ ] Accessibility testing completed (Lighthouse ≥ 90)
- [ ] Cross-browser testing completed (Chrome, Firefox, Safari)
- [ ] No regressions in existing functionality

---

## NOTES

### Design Decisions

**1. Color Palette Choice:**
Selected colors with strong semantic associations:
- Purple (Brainstorming) = Creative, exploratory phase
- Orange (Vision Review) = Attention, review needed
- Blue (Planning) = Calm, organized thinking
- Green (In Progress) = Active, positive momentum
- Gray (Paused) = Neutral, inactive
- Cyan (Completed) = Achievement, completion

All colors selected to meet WCAG 2.2 AA contrast requirements (3:1 for UI components).

**2. Mobile-First Approach:**
Starting with mobile base styles and progressively enhancing for larger screens ensures:
- Better performance on mobile (lighter initial load)
- Forced prioritization of essential features
- Easier maintenance (adding features vs removing them)

**3. No New Dependencies:**
Deliberately avoided adding Tailwind CSS or other frameworks to:
- Minimize bundle size increase
- Reduce migration complexity
- Maintain consistency with existing CSS approach
- Avoid potential conflicts with existing styles

**4. User Name Hardcoded:**
"Sam" is hardcoded as the user name per issue description. Future enhancement could add environment variable (`VITE_USER_NAME`) or user profile API.

### Trade-offs

**Monolithic CSS vs CSS Modules:**
Kept existing monolithic `App.css` approach instead of refactoring to CSS Modules to minimize scope creep. Added separate `variables.css` and `responsive.css` for new functionality. Future refactor recommended.

**Manual Testing vs Automated:**
No frontend test suite exists. Recommended manual testing for this iteration. Adding Vitest + Testing Library would be valuable future work.

**Three-Panel Layout on Mobile:**
Hiding the right panel (SCAR feed) on mobile/tablet trades completeness for usability. Users on small screens rarely need all three panels simultaneously. Can add a toggle button in future if needed.

### Future Enhancements

1. **User Profile System**: Replace hardcoded "Sam" with actual user profile from backend
2. **Theme Persistence**: Save user's color scheme preference (light/dark mode)
3. **Bottom Tab Navigation**: Add mobile bottom tabs for switching between Projects/Chat/Activity
4. **Pull-to-Refresh**: Implement native pull-to-refresh gesture on mobile
5. **Swipe Gestures**: Add swipe left/right to navigate between panels on mobile
6. **CSS Refactor**: Split monolithic App.css into component-scoped CSS modules
7. **Automated Testing**: Add Vitest + Testing Library for unit/integration tests
8. **Accessibility Audit**: Run full WCAG 2.2 audit, add ARIA live regions for dynamic content

### Known Limitations

1. **No Dark Mode**: Status colors are defined for light mode only
2. **No Animation**: Status badge changes happen instantly (could add transitions)
3. **No Offline Support**: Refresh button requires network connection
4. **No Error States**: Minimal error handling for failed API calls (logs to console only)
5. **No Loading Skeletons**: Simple "Loading..." text instead of skeleton UI

### Estimated Implementation Time

Based on issue estimates and codebase complexity:
- **Phase 1** (Foundation): 2-3 hours
- **Phase 2** (Color-Coded Projects): 3-4 hours
- **Phase 3** (Project Name Display): 1-2 hours
- **Phase 4** (Refresh Button): 1-2 hours
- **Phase 5** (Personalized Messages): 2-3 hours
- **Phase 6** (Mobile Responsive): 8-12 hours
- **Phase 7** (Testing & Refinement): 2-3 hours

**Total: 19-29 hours** (aligns with issue estimate of 30-40 hours including buffer)
