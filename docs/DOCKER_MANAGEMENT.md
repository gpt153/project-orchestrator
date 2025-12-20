# Docker Management with SCAR

SCAR can manage production Docker containers for your projects, allowing you to deploy, monitor, and control your applications directly from Telegram or GitHub.

## Overview

The Docker integration enables SCAR to:
- 📊 Check production container status
- 📜 View container logs in real-time
- 🔄 Restart containers safely
- 🚀 Deploy workspace changes to production

## How It Works

1. **SCAR has Docker access** - The SCAR container has access to the host Docker socket
2. **Project configuration** - Projects are mapped in `.scar-projects.json`
3. **Workspace → Production** - SCAR edits code in `/workspace`, deploys to production directories

## Setup

### 1. Docker Socket Access

The SCAR container needs access to the Docker socket. This is configured in `docker-compose.yml`:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
group_add:
  - "108"  # docker group on host
```

### 2. Project Configuration

Create or edit `/workspace/.scar-projects.json`:

```json
{
  "project-orchestrator": {
    "workspace": "/workspace/project-orchestrator",
    "production": "/home/samuel/po",
    "compose_project": "po",
    "containers": ["backend", "po-postgres-1", "po-redis-1"],
    "primary_container": "backend"
  },
  "health-agent": {
    "workspace": "/workspace/health-agent",
    "production": "/home/samuel/odin-health",
    "compose_project": "odin-health",
    "containers": ["odin-health-agent", "odin-health-postgres"],
    "primary_container": "odin-health-agent"
  }
}
```

**Configuration fields:**
- `workspace` - Path to workspace directory (where SCAR edits code)
- `production` - Path to production directory (where containers run from)
- `compose_project` - Docker Compose project name
- `containers` - List of container names to manage
- `primary_container` - Main application container (used for logs by default)

## Available Commands

### `/docker_status [project]`

Check the status of all production containers for a project.

**Usage:**
```
/docker_status
/docker_status project-orchestrator
/docker_status health-agent
```

**Output:**
- Container status (running/stopped)
- Health status
- Uptime
- Port mappings
- Image name
- Production vs workspace paths

**Example:**
```
📊 Project-Orchestrator - Production Status

backend (primary)
✅ Status: Running
💚 Health: Healthy
⏱️ Uptime: 2h 15m
🔌 Ports: 8001→8000/tcp
🐳 Image: po-app

po-postgres-1
✅ Status: Running
💚 Health: Healthy
⏱️ Uptime: 2h 15m

💡 Production: /home/samuel/po
📁 Workspace: /workspace/project-orchestrator
```

### `/docker_logs [project] [lines]`

View logs from a project's primary container.

**Usage:**
```
/docker_logs                    # Default: project-orchestrator, 50 lines
/docker_logs project-orchestrator 100
/docker_logs health-agent 200
```

**Parameters:**
- `project` - Project name (default: project-orchestrator)
- `lines` - Number of log lines (default: 50)

**Output:**
- Timestamped container logs
- Both stdout and stderr
- Formatted in code blocks

**Example:**
```
📜 backend - Last 50 lines

[2025-12-20 15:30:11] INFO: Server started on port 8000
[2025-12-20 15:30:15] INFO: Database connected
[2025-12-20 15:35:22] ERROR: Task failed: Connection timeout
[2025-12-20 15:35:23] INFO: Retry attempt 1/3
```

### `/docker_restart [project]`

Restart all containers for a project with confirmation.

**Usage:**
```
/docker_restart
/docker_restart project-orchestrator
```

**Flow:**
1. Shows confirmation with container list
2. Waits for user to type `yes`
3. Restarts containers sequentially
4. Reports success/failure for each

**Example:**
```
⚠️ Restart Production Containers

Project: project-orchestrator

Containers to restart:
- backend
- po-postgres-1
- po-redis-1

⏱️ Estimated downtime: 10-30 seconds

Type `yes` to confirm
```

After confirmation:
```
🔄 Restarting containers...
✅ backend restarted
✅ po-postgres-1 restarted
✅ po-redis-1 restarted

✅ All containers healthy. Production is live.
```

### `/docker_deploy [project]`

Deploy workspace changes to production with rebuild and restart.

**Usage:**
```
/docker_deploy
/docker_deploy project-orchestrator
```

**Flow:**
1. Shows confirmation with source/target paths
2. Waits for user to type `yes`
3. Syncs files from workspace → production
4. Rebuilds Docker image (if Dockerfile/dependencies changed)
5. Restarts containers with new code
6. Reports deployment status

**What gets deployed:**
- All code changes
- Configuration files
- Dependencies (triggers rebuild)

**What's excluded:**
- `.git` directory
- `__pycache__` directories
- `*.pyc` files

**Example:**
```
🚀 Deploy Workspace → Production

Source: /workspace/project-orchestrator
Target: /home/samuel/po

Steps:
1. Copy changes to production
2. Rebuild container (if needed)
3. Restart services

Type `yes` to deploy
```

After confirmation:
```
📦 Copying files...
🔨 Building new image...
🔄 Restarting containers...
✅ Deployment complete!

Backend: Running (3s uptime)
Check status: /docker_status
```

## Typical Workflow

### 1. Fix a Bug

```
You: @scar fix the timeout bug in project-orchestrator
SCAR: [analyzes code, makes fix in /workspace/project-orchestrator]
      ✅ Bug fixed in workspace

You: /docker_status
SCAR: 📊 Project Orchestrator
      ⚠️ Container: Running (OLD VERSION)
      💡 Workspace has uncommitted changes

You: /docker_deploy
SCAR: [confirmation prompt]

You: yes
SCAR: 🚀 Deploying...
      ✅ Complete! Backend restarted with new code

You: /docker_logs 20
SCAR: [Shows logs with bug fixed]
```

### 2. Check Production Status

```
You: /docker_status
SCAR: [Shows all container statuses]

You: /docker_logs 100
SCAR: [Shows recent logs]
```

### 3. Emergency Restart

```
You: /docker_restart
SCAR: [Confirmation prompt]

You: yes
SCAR: [Restarts all containers]
      ✅ All containers healthy
```

## Safety Features

### Confirmation Required
- `/docker_restart` requires typing "yes"
- `/docker_deploy` requires typing "yes"
- Prevents accidental production changes

### Health Checks
- Deployment verifies container health after restart
- Reports any containers that fail to start
- Shows uptime to confirm restart

### Rollback Capability
If deployment fails:
1. Production directory still has working code
2. Can manually restart previous version
3. Workspace changes are preserved

## Troubleshooting

### Docker Not Available

**Error:** `docker: command not found`

**Solution:**
1. Rebuild SCAR container (includes Docker CLI now)
2. Check Dockerfile has Docker installation
3. Restart SCAR

### Permission Denied

**Error:** `Permission denied accessing /var/run/docker.sock`

**Solution:**
1. Check docker-compose.yml has:
   ```yaml
   volumes:
     - /var/run/docker.sock:/var/run/docker.sock
   group_add:
     - "108"  # docker group ID
   ```
2. Verify group ID matches host docker group
3. Restart SCAR

### Container Not Found

**Error:** `Container 'backend' not found`

**Solution:**
1. Check container name in `.scar-projects.json`
2. Verify container is running on host
3. Use exact container name from `docker ps`

### Project Not Found

**Error:** `Project 'foo' not found in configuration`

**Solution:**
1. Add project to `/workspace/.scar-projects.json`
2. Use exact project name
3. Reload configuration

## Advanced Usage

### Adding a New Project

1. Clone to workspace:
```
/clone https://github.com/you/new-project
```

2. Add to config:
```json
{
  "new-project": {
    "workspace": "/workspace/new-project",
    "production": "/home/samuel/new-project",
    "compose_project": "new-project",
    "auto_detect": true
  }
}
```

3. First deployment:
```
/docker_deploy new-project
```

### Auto-Detection

Set `"auto_detect": true` in config to automatically detect containers from docker-compose.yml.

### Multiple Environments

You can configure different projects for different environments:

```json
{
  "app-dev": {
    "workspace": "/workspace/app",
    "production": "/home/samuel/app-dev",
    "compose_project": "app-dev",
    "containers": ["app-dev"]
  },
  "app-prod": {
    "workspace": "/workspace/app",
    "production": "/home/samuel/app-prod",
    "compose_project": "app-prod",
    "containers": ["app-prod"]
  }
}
```

## Security Considerations

### Docker Socket Access

Mounting the Docker socket gives SCAR **root-level access** to the host system.

**This is safe because:**
- SCAR already runs your code
- Only you have access (Telegram auth)
- Read-only operations are safe
- Destructive operations require confirmation

**Best practices:**
- Never expose SCAR to untrusted users
- Keep Telegram bot token secure
- Use confirmation prompts for destructive actions
- Monitor Docker logs for unusual activity

### Production Safety

- Always test changes in workspace first
- Use `/docker_status` before deploying
- Check `/docker_logs` after deployment
- Keep backups of production data
- Use git to track workspace changes

## Future Enhancements

Planned features:
- Auto-deployment on commit
- Rollback to previous version
- Health monitoring with alerts
- Multi-container orchestration
- Log streaming to Telegram
- Container metrics and performance data

## Support

If you encounter issues:
1. Check `/docker_status` for container health
2. View `/docker_logs` for error messages
3. Verify `.scar-projects.json` configuration
4. Check Docker socket permissions
5. Review SCAR logs in production

For bugs or feature requests, open an issue on GitHub.
