"""Email tool for sending emails."""

from typing import Any

from manus.tools.base import Tool, ToolResult, ToolStatus


class EmailTool(Tool):
    """Send emails via SMTP or API."""

    name = "email"
    description = "Send emails via SMTP or API (Gmail, Outlook)"

    parameters = {
        "to": "Recipient email address",
        "subject": "Email subject",
        "body": "Email body (plain text or HTML)",
        "cc": "CC recipients (optional)",
        "bcc": "BCC recipients (optional)",
        "attachments": "List of file paths to attach (optional)",
    }

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int = 587,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls

    async def execute(
        self,
        to: str,
        subject: str,
        body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        attachments: list[str] | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        if not self.smtp_host:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="SMTP not configured. Please set smtp_host.",
            )

        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.base import MIMEBase
            from email import encoders
            import os

            msg = MIMEMultipart("alternative")
            msg["From"] = self.smtp_user
            msg["To"] = to
            msg["Subject"] = subject

            if cc:
                msg["Cc"] = ", ".join(cc)
            if bcc:
                msg["Bcc"] = ", ".join(bcc)

            msg.attach(MIMEText(body, "plain"))

            if attachments:
                for filepath in attachments:
                    if os.path.exists(filepath):
                        with open(filepath, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={os.path.basename(filepath)}",
                        )
                        msg.attach(part)

            recipients = [to]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, recipients, msg.as_string())

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "to": to,
                    "subject": subject,
                    "sent": True,
                },
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Failed to send email: {str(e)}",
            )


class GmailTool(Tool):
    """Send emails via Gmail API."""

    name = "gmail"
    description = "Send emails via Gmail API"

    parameters = {
        "to": "Recipient email address",
        "subject": "Email subject",
        "body": "Email body",
        "cc": "CC recipients (optional)",
        "attachments": "List of file paths to attach (optional)",
    }

    def __init__(self, credentials_path: str | None = None):
        self.credentials_path = credentials_path
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = None
            if self.credentials_path:
                import json

                with open(self.credentials_path) as f:
                    token = json.load(f)
                creds = Credentials(token=token.get("access_token"))

            self._service = build("gmail", "v1", credentials=creds)
            return self._service

        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gmail service: {e}")

    async def execute(
        self,
        to: str,
        subject: str,
        body: str,
        cc: list[str] | None = None,
        attachments: list[str] | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            import base64
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart()
            msg["To"] = to
            msg["Subject"] = subject

            if cc:
                msg["Cc"] = ", ".join(cc)

            msg.attach(MIMEText(body, "plain"))

            if attachments:
                from email.mime.base import MIMEBase
                from email import encoders
                import os

                for filepath in attachments:
                    if os.path.exists(filepath):
                        with open(filepath, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={os.path.basename(filepath)}",
                        )
                        msg.attach(part)

            service = self._get_service()
            encoded_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()

            result = (
                service.users()
                .messages()
                .send(userId="me", body={"raw": encoded_msg})
                .execute()
            )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"message_id": result.get("id"), "sent": True},
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Failed to send email via Gmail: {str(e)}",
            )
