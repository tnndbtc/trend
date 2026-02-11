"""
Alert service for sending notifications via multiple channels.

Supports:
- Email (SMTP)
- Slack (webhooks)
- Future: Discord, Teams, PagerDuty, etc.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Supported alert channels."""
    EMAIL = "email"
    SLACK = "slack"
    CONSOLE = "console"  # For testing


class AlertService:
    """
    Multi-channel alert service.

    Sends notifications through configured channels (email, Slack, etc.)
    based on alert severity and configuration.
    """

    def __init__(
        self,
        email_enabled: bool = True,
        slack_enabled: bool = True,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_from: Optional[str] = None,
        alert_emails: Optional[List[str]] = None,
        slack_webhook_url: Optional[str] = None,
    ):
        """
        Initialize alert service.

        Args:
            email_enabled: Enable email alerts
            slack_enabled: Enable Slack alerts
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            smtp_from: From email address
            alert_emails: List of email recipients
            slack_webhook_url: Slack webhook URL
        """
        self.email_enabled = email_enabled
        self.slack_enabled = slack_enabled

        # Email configuration
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", smtp_port))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.smtp_from = smtp_from or os.getenv("SMTP_FROM", "alerts@trendplatform.com")

        # Parse alert emails from env (comma-separated)
        emails_env = os.getenv("ALERT_EMAILS", "")
        self.alert_emails = alert_emails or (emails_env.split(",") if emails_env else [])

        # Slack configuration
        self.slack_webhook_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL")

        # Validate configuration
        if self.email_enabled and not self.smtp_host:
            logger.warning("Email alerts enabled but SMTP_HOST not configured")
            self.email_enabled = False

        if self.slack_enabled and not self.slack_webhook_url:
            logger.warning("Slack alerts enabled but SLACK_WEBHOOK_URL not configured")
            self.slack_enabled = False

    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        channels: Optional[List[AlertChannel]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, bool]:
        """
        Send alert through configured channels.

        Args:
            title: Alert title/subject
            message: Alert message body
            severity: Alert severity level
            channels: Specific channels to use (default: all enabled)
            metadata: Additional metadata to include

        Returns:
            Dictionary of channel results (channel_name -> success)
        """
        if channels is None:
            # Use all enabled channels by default
            channels = []
            if self.email_enabled:
                channels.append(AlertChannel.EMAIL)
            if self.slack_enabled:
                channels.append(AlertChannel.SLACK)

        results = {}

        # Send to each channel
        for channel in channels:
            try:
                if channel == AlertChannel.EMAIL:
                    success = await self._send_email(title, message, severity, metadata)
                    results["email"] = success
                elif channel == AlertChannel.SLACK:
                    success = await self._send_slack(title, message, severity, metadata)
                    results["slack"] = success
                elif channel == AlertChannel.CONSOLE:
                    logger.info(f"ALERT [{severity.value.upper()}] {title}: {message}")
                    results["console"] = True
            except Exception as e:
                logger.error(f"Failed to send alert via {channel.value}: {e}")
                results[channel.value] = False

        return results

    async def _send_email(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send email alert.

        Args:
            title: Email subject
            message: Email body
            severity: Alert severity
            metadata: Additional data

        Returns:
            True if sent successfully
        """
        if not self.email_enabled or not self.alert_emails:
            logger.warning("Email alerts not configured properly")
            return False

        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.smtp_from
            msg["To"] = ", ".join(self.alert_emails)
            msg["Subject"] = f"[{severity.value.upper()}] {title}"

            # Build email body
            body = f"""
Severity: {severity.value.upper()}
Title: {title}

{message}
"""

            if metadata:
                body += "\n\nMetadata:\n"
                for key, value in metadata.items():
                    body += f"  {key}: {value}\n"

            body += "\n\n---\nGenerated by Trend Intelligence Platform"

            msg.attach(MIMEText(body, "plain"))

            # Send email in thread pool (smtplib is synchronous)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_email_sync,
                msg,
            )

            logger.info(f"Email alert sent to {len(self.alert_emails)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    def _send_email_sync(self, msg: MIMEMultipart) -> None:
        """
        Synchronous email sending (for thread pool).

        Args:
            msg: Email message to send
        """
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)

    async def _send_slack(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send Slack alert via webhook.

        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity
            metadata: Additional data

        Returns:
            True if sent successfully
        """
        if not self.slack_enabled or not self.slack_webhook_url:
            logger.warning("Slack alerts not configured properly")
            return False

        try:
            # Map severity to Slack color
            color_map = {
                AlertSeverity.INFO: "#36a64f",  # Green
                AlertSeverity.WARNING: "#ff9900",  # Orange
                AlertSeverity.ERROR: "#ff0000",  # Red
                AlertSeverity.CRITICAL: "#8b0000",  # Dark red
            }

            # Build Slack message
            slack_payload = {
                "username": "Trend Platform Alerts",
                "icon_emoji": ":warning:",
                "attachments": [
                    {
                        "color": color_map.get(severity, "#808080"),
                        "title": f"[{severity.value.upper()}] {title}",
                        "text": message,
                        "fields": [],
                        "footer": "Trend Intelligence Platform",
                        "ts": int(asyncio.get_event_loop().time()),
                    }
                ],
            }

            # Add metadata fields
            if metadata:
                for key, value in metadata.items():
                    slack_payload["attachments"][0]["fields"].append({
                        "title": key,
                        "value": str(value),
                        "short": True,
                    })

            # Send webhook request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.slack_webhook_url,
                    json=slack_payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        logger.info("Slack alert sent successfully")
                        return True
                    else:
                        logger.error(f"Slack webhook returned status {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    async def send_collection_failure_alert(
        self,
        plugin_name: str,
        error_message: str,
        consecutive_failures: int = 1,
    ) -> Dict[str, bool]:
        """
        Send alert for collection failure.

        Args:
            plugin_name: Name of the failed plugin
            error_message: Error message
            consecutive_failures: Number of consecutive failures

        Returns:
            Dictionary of send results per channel
        """
        severity = AlertSeverity.WARNING if consecutive_failures < 3 else AlertSeverity.ERROR

        title = f"Collection Failure: {plugin_name}"
        message = f"""
Plugin '{plugin_name}' failed to collect data.

Error: {error_message}

Consecutive Failures: {consecutive_failures}
"""

        if consecutive_failures >= 5:
            message += "\n⚠️  WARNING: This plugin has failed 5+ times and may need manual intervention."

        metadata = {
            "plugin": plugin_name,
            "consecutive_failures": consecutive_failures,
        }

        return await self.send_alert(title, message, severity, metadata=metadata)

    async def send_trend_alert(
        self,
        trend_title: str,
        trend_score: float,
        trend_state: str,
        trend_category: str,
    ) -> Dict[str, bool]:
        """
        Send alert for trending topic.

        Args:
            trend_title: Title of the trend
            trend_score: Trend score
            trend_state: Trend state (emerging, viral, etc.)
            trend_category: Trend category

        Returns:
            Dictionary of send results per channel
        """
        title = f"New Trending Topic: {trend_title}"
        message = f"""
A new trend has been detected:

Title: {trend_title}
Category: {trend_category}
State: {trend_state}
Score: {trend_score:.2f}
"""

        metadata = {
            "category": trend_category,
            "state": trend_state,
            "score": trend_score,
        }

        return await self.send_alert(
            title,
            message,
            AlertSeverity.INFO,
            metadata=metadata,
        )

    async def send_system_health_alert(
        self,
        service: str,
        is_healthy: bool,
        details: Optional[str] = None,
    ) -> Dict[str, bool]:
        """
        Send alert for system health issues.

        Args:
            service: Service name (postgres, redis, qdrant, etc.)
            is_healthy: Current health status
            details: Additional details

        Returns:
            Dictionary of send results per channel
        """
        if is_healthy:
            severity = AlertSeverity.INFO
            title = f"Service Recovered: {service}"
            message = f"Service '{service}' is now healthy."
        else:
            severity = AlertSeverity.CRITICAL
            title = f"Service Down: {service}"
            message = f"Service '{service}' is unhealthy or unavailable."

        if details:
            message += f"\n\nDetails: {details}"

        metadata = {
            "service": service,
            "status": "healthy" if is_healthy else "unhealthy",
        }

        return await self.send_alert(title, message, severity, metadata=metadata)


# Singleton instance
_alert_service: Optional[AlertService] = None


def get_alert_service() -> AlertService:
    """
    Get singleton alert service instance.

    Returns:
        AlertService instance
    """
    global _alert_service

    if _alert_service is None:
        _alert_service = AlertService(
            email_enabled=os.getenv("ENABLE_EMAIL_ALERTS", "false").lower() == "true",
            slack_enabled=os.getenv("ENABLE_SLACK_ALERTS", "false").lower() == "true",
        )

    return _alert_service
