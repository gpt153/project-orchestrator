# Docker Management Feature - Deployment Guide

This guide will help you deploy the Docker management feature to your SCAR instance.

## Quick Start

### Step 1: Rebuild SCAR Container

The SCAR container needs Docker CLI installed. Rebuild it with the updated Dockerfile:

```bash
cd /home/samuel/scar  # Or wherever your SCAR instance lives
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Step 2: Verify Docker Access

Test that SCAR can access Docker:

```bash
docker exec -it scar-app docker ps
```

You should see a list of running containers. If you get a permission error, see Troubleshooting below.

### Step 3: Configure Projects

The project configuration file should already exist at `/workspace/.scar-projects.json` with your projects configured.

To verify:
```bash
cat /workspace/.scar-projects.json
```

### Step 4: Test Commands

From Telegram, test the Docker commands:

1. **Check status:**
   ```
   /docker_status
   ```

2. **View logs:**
   ```
   /docker_logs 50
   ```

3. **Get help:**
   ```
   /help
   ```

## What Was Changed

### Files Modified

1. **`Dockerfile`**
   - Added Docker CLI installation
   - Installed curl and ca-certificates

2. **`docker-compose.yml`**
   - Mounted Docker socket: `/var/run/docker.sock`
   - Added docker group (108) to container user

3. **`pyproject.toml`**
   - Added `docker>=7.1.0` dependency

4. **`src/integrations/telegram_bot.py`**
   - Added Docker command handlers
   - Updated help text
   - Integrated confirmation flow

### Files Created

1. **`/workspace/.scar-projects.json`**
   - Project configuration mapping

2. **`src/utils/project_config.py`**
   - Configuration loader utility

3. **`src/services/docker_manager.py`**
   - Docker API wrapper service

4. **`src/integrations/docker_commands.py`**
   - Telegram command handlers for Docker

5. **`docs/DOCKER_MANAGEMENT.md`**
   - Complete user documentation

## Verification Checklist

After deployment, verify:

- [ ] SCAR container can run `docker ps`
- [ ] `/docker_status` shows container information
- [ ] `/docker_logs` displays recent logs
- [ ] `/help` shows Docker commands
- [ ] Confirmation prompts work for restart/deploy

## Troubleshooting

### Permission Denied on Docker Socket

If you see: `Permission denied while connecting to /var/run/docker.sock`

**Check docker group ID:**
```bash
ls -la /var/run/docker.sock
# Output: srw-rw---- 1 root 108 ...
#                            ^^^ This is the group ID
```

**Update docker-compose.yml:**
```yaml
group_add:
  - "108"  # Use the actual group ID from above
```

**Restart SCAR:**
```bash
docker-compose restart
```

### Container Not Found

If containers aren't found, verify:

1. **Container names are correct:**
   ```bash
   docker ps --format "{{.Names}}"
   ```

2. **Update .scar-projects.json with actual names:**
   ```json
   {
     "project-orchestrator": {
       "containers": ["backend", "po-postgres-1", "po-redis-1"]
     }
   }
   ```

### Docker CLI Not Found

If `docker` command is not found in SCAR container:

1. **Rebuild with --no-cache:**
   ```bash
   docker-compose build --no-cache app
   docker-compose up -d
   ```

2. **Verify Docker installation in container:**
   ```bash
   docker exec -it scar-app which docker
   ```

## Testing the Deployment Feature

To test the full deployment workflow:

1. **Make a small change in workspace:**
   ```bash
   echo "# Test change" >> /workspace/project-orchestrator/README.md
   ```

2. **Deploy via Telegram:**
   ```
   /docker_deploy project-orchestrator
   yes
   ```

3. **Verify deployment:**
   ```
   /docker_status
   /docker_logs 20
   ```

4. **Check production directory:**
   ```bash
   ls -la /home/samuel/po/README.md
   # Should show recent modification time
   ```

## Rollback

If you need to rollback these changes:

1. **Restore Dockerfile:**
   ```bash
   git checkout HEAD -- Dockerfile
   ```

2. **Restore docker-compose.yml:**
   ```bash
   git checkout HEAD -- docker-compose.yml
   ```

3. **Remove new files:**
   ```bash
   rm -rf src/utils/project_config.py
   rm -rf src/services/docker_manager.py
   rm -rf src/integrations/docker_commands.py
   rm /workspace/.scar-projects.json
   ```

4. **Rebuild:**
   ```bash
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

## Production Deployment Checklist

Before deploying to production:

1. **Backup current state:**
   ```bash
   docker-compose down
   tar -czf scar-backup-$(date +%Y%m%d).tar.gz /home/samuel/scar
   ```

2. **Deploy changes:**
   ```bash
   cd /home/samuel/scar
   git pull  # Or copy files from workspace
   docker-compose build --no-cache
   docker-compose up -d
   ```

3. **Monitor logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Test from Telegram:**
   ```
   /help
   /docker_status
   ```

5. **Verify no errors:**
   ```bash
   docker-compose ps
   # All services should be "Up" and "healthy"
   ```

## Next Steps

After successful deployment:

1. **Read the full documentation:** `docs/DOCKER_MANAGEMENT.md`
2. **Configure additional projects** in `.scar-projects.json`
3. **Try the deployment workflow** with a test change
4. **Set up monitoring** for production containers

## Support

If you encounter issues:

1. Check SCAR logs: `docker-compose logs app`
2. Check Docker socket permissions: `ls -la /var/run/docker.sock`
3. Verify configuration: `cat /workspace/.scar-projects.json`
4. Test Docker CLI in container: `docker exec -it scar-app docker ps`

## Security Notes

- Docker socket access gives root privileges
- Only enable for trusted SCAR instances
- Keep Telegram bot token secure
- Use confirmation prompts for destructive operations
- Monitor Docker logs for unusual activity

---

**Status:** Ready for deployment ✅

The implementation is complete and ready to use. Follow the steps above to deploy and start managing your Docker containers via SCAR!
