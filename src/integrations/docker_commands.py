"""
Docker management command handlers for Telegram bot.

Provides commands to manage production Docker containers for projects.
"""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from ..services.docker_manager import DockerManager
from ..utils.project_config import get_project_config


logger = logging.getLogger(__name__)


class DockerCommandHandler:
    """Handles Docker management commands from Telegram."""

    def __init__(self, docker_manager: Optional[DockerManager] = None):
        """
        Initialize Docker command handler.

        Args:
            docker_manager: DockerManager instance. If None, creates a new one.
        """
        self.docker_manager = docker_manager or DockerManager()

    async def docker_status_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, project_name: str
    ) -> None:
        """
        Handle /docker-status command - show production container status.

        Args:
            update: Telegram update
            context: Handler context
            project_name: Name of the project to check
        """
        try:
            # Validate project exists
            config = get_project_config(project_name)
            if not config:
                await update.message.reply_text(
                    f"❌ Project '{project_name}' not found in configuration.\n\n"
                    "Available projects can be found in .scar-projects.json"
                )
                return

            # Get container statuses
            statuses = await self.docker_manager.get_container_status(project_name)

            # Build status message
            message = f"📊 **{project_name.title()} - Production Status**\n\n"

            for container_name, info in statuses.items():
                status_emoji = "✅" if info["running"] else "❌"
                health_emoji = {"healthy": "💚", "unhealthy": "💔", "unknown": "❓"}.get(
                    info["health"], "❓"
                )

                is_primary = " (primary)" if info["is_primary"] else ""

                message += f"**{container_name}{is_primary}**\n"
                message += f"{status_emoji} Status: {info['status'].title()}\n"

                if info["running"]:
                    message += f"{health_emoji} Health: {info['health'].title()}\n"
                    message += f"⏱️ Uptime: {info['uptime']}\n"
                    if info['ports']:
                        message += f"🔌 Ports: {info['ports']}\n"
                    message += f"🐳 Image: {info['image']}\n"

                message += "\n"

            message += f"💡 **Production:** `{config.production}`\n"
            message += f"📁 **Workspace:** `{config.workspace}`\n"

            await update.message.reply_text(message, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in docker_status_command: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Error getting status: {str(e)}\n\n"
                "Make sure Docker is running and accessible."
            )

    async def docker_logs_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        project_name: str,
        lines: int = 50,
        container_name: Optional[str] = None,
    ) -> None:
        """
        Handle /docker-logs command - view production container logs.

        Args:
            update: Telegram update
            context: Handler context
            project_name: Name of the project
            lines: Number of log lines to retrieve (default: 50)
            container_name: Specific container name (default: primary container)
        """
        try:
            # Validate project exists
            config = get_project_config(project_name)
            if not config:
                await update.message.reply_text(
                    f"❌ Project '{project_name}' not found in configuration."
                )
                return

            target_container = container_name or config.primary_container

            # Get logs
            logs = await self.docker_manager.get_container_logs(
                project_name, lines=lines, container_name=target_container
            )

            # Format message
            message = f"📜 **{target_container} - Last {lines} lines**\n\n"
            message += f"```\n{logs}\n```"

            # Telegram has a 4096 character limit
            if len(message) > 4000:
                # Split into chunks
                chunks = [message[i : i + 3900] for i in range(0, len(message), 3900)]
                for i, chunk in enumerate(chunks[:3]):  # Limit to 3 chunks
                    if i > 0:
                        chunk = "```\n" + chunk  # Re-open code block
                    if i < len(chunks) - 1:
                        chunk = chunk + "\n```"  # Close code block
                    await update.message.reply_text(chunk, parse_mode="Markdown")
            else:
                await update.message.reply_text(message, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in docker_logs_command: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error getting logs: {str(e)}")

    async def docker_restart_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, project_name: str
    ) -> None:
        """
        Handle /docker-restart command - restart production containers.

        Args:
            update: Telegram update
            context: Handler context
            project_name: Name of the project
        """
        try:
            # Validate project exists
            config = get_project_config(project_name)
            if not config:
                await update.message.reply_text(
                    f"❌ Project '{project_name}' not found in configuration."
                )
                return

            # Ask for confirmation
            containers_list = "\n".join([f"- {c}" for c in config.containers])
            confirmation_msg = (
                f"⚠️ **Restart Production Containers**\n\n"
                f"Project: **{project_name}**\n\n"
                f"Containers to restart:\n{containers_list}\n\n"
                f"⏱️ Estimated downtime: 10-30 seconds\n\n"
                f"Type `yes` to confirm"
            )

            await update.message.reply_text(confirmation_msg, parse_mode="Markdown")

            # Store pending action in context
            context.chat_data["pending_docker_action"] = {
                "action": "restart",
                "project": project_name,
            }

        except Exception as e:
            logger.error(f"Error in docker_restart_command: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def docker_deploy_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, project_name: str
    ) -> None:
        """
        Handle /docker-deploy command - deploy workspace to production.

        Args:
            update: Telegram update
            context: Handler context
            project_name: Name of the project
        """
        try:
            # Validate project exists
            config = get_project_config(project_name)
            if not config:
                await update.message.reply_text(
                    f"❌ Project '{project_name}' not found in configuration."
                )
                return

            # Ask for confirmation
            confirmation_msg = (
                f"🚀 **Deploy Workspace → Production**\n\n"
                f"**Source:** `{config.workspace}`\n"
                f"**Target:** `{config.production}`\n\n"
                f"**Steps:**\n"
                f"1. Copy changes to production\n"
                f"2. Rebuild container (if needed)\n"
                f"3. Restart services\n\n"
                f"Type `yes` to deploy"
            )

            await update.message.reply_text(confirmation_msg, parse_mode="Markdown")

            # Store pending action in context
            context.chat_data["pending_docker_action"] = {
                "action": "deploy",
                "project": project_name,
            }

        except Exception as e:
            logger.error(f"Error in docker_deploy_command: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def handle_docker_confirmation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_response: str
    ) -> bool:
        """
        Handle user confirmation for Docker commands.

        Args:
            update: Telegram update
            context: Handler context
            user_response: User's response text

        Returns:
            True if handled, False otherwise
        """
        pending_action = context.chat_data.get("pending_docker_action")

        if not pending_action:
            return False

        if user_response.lower().strip() not in ["yes", "y"]:
            await update.message.reply_text("❌ Action cancelled.")
            context.chat_data.pop("pending_docker_action", None)
            return True

        action = pending_action["action"]
        project_name = pending_action["project"]

        try:
            if action == "restart":
                await update.message.reply_text("🔄 Restarting containers...")

                results = await self.docker_manager.restart_containers(project_name)

                # Build result message
                message = "**Restart Results:**\n\n"
                for container, success in results.items():
                    emoji = "✅" if success else "❌"
                    message += f"{emoji} {container}\n"

                all_success = all(results.values())
                if all_success:
                    message += "\n✅ All containers healthy. Production is live."
                else:
                    message += "\n⚠️ Some containers failed to restart. Check status."

                await update.message.reply_text(message, parse_mode="Markdown")

            elif action == "deploy":
                await update.message.reply_text("🚀 Deploying...")

                success, message = await self.docker_manager.deploy_project(project_name)

                if success:
                    # Get new status
                    statuses = await self.docker_manager.get_container_status(project_name)
                    config = get_project_config(project_name)

                    primary_status = statuses.get(config.primary_container, {})
                    uptime = primary_status.get("uptime", "unknown")

                    await update.message.reply_text(
                        f"✅ **Deployment Complete!**\n\n"
                        f"{config.primary_container}: Running ({uptime} uptime)\n\n"
                        f"Check status: /docker-status",
                        parse_mode="Markdown",
                    )
                else:
                    await update.message.reply_text(
                        f"❌ **Deployment Failed**\n\n{message}", parse_mode="Markdown"
                    )

            # Clear pending action
            context.chat_data.pop("pending_docker_action", None)
            return True

        except Exception as e:
            logger.error(f"Error executing Docker action: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error: {str(e)}")
            context.chat_data.pop("pending_docker_action", None)
            return True
