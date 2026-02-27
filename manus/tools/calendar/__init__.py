"""Calendar tool for managing calendar events."""

from typing import Any

from manus.tools.base import Tool, ToolResult, ToolStatus


class CalendarTool(Tool):
    """Manage calendar events via Google Calendar or Outlook."""

    name = "calendar"
    description = "Create, read, update, delete calendar events"

    parameters = {
        "action": "Operation: create, get, update, delete, list",
        "event_id": "Event ID (required for get, update, delete)",
        "title": "Event title",
        "description": "Event description",
        "start_time": "Start time (ISO 8601 format)",
        "end_time": "End time (ISO 8601 format)",
        "location": "Event location",
        "attendees": "List of attendee email addresses",
        "calendar_id": "Calendar ID (default: primary)",
    }

    def __init__(
        self,
        provider: str = "google",
        credentials_path: str | None = None,
    ):
        self.provider = provider
        self.credentials_path = credentials_path
        self._service = None

    def _get_google_service(self):
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

            self._service = build("calendar", "v3", credentials=creds)
            return self._service

        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google Calendar service: {e}")

    async def execute(
        self,
        action: str,
        event_id: str | None = None,
        title: str | None = None,
        description: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
        calendar_id: str = "primary",
        **kwargs: Any,
    ) -> ToolResult:
        if self.provider == "google":
            return await self._execute_google(
                action,
                event_id,
                title,
                description,
                start_time,
                end_time,
                location,
                attendees,
                calendar_id,
            )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Provider {self.provider} not supported yet",
            )

    async def _execute_google(
        self,
        action: str,
        event_id: str | None,
        title: str | None,
        description: str | None,
        start_time: str | None,
        end_time: str | None,
        location: str | None,
        attendees: list[str] | None,
        calendar_id: str,
    ) -> ToolResult:
        try:
            service = self._get_google_service()

            if action == "create":
                if not title or not start_time or not end_time:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="title, start_time, and end_time are required",
                    )

                event = {
                    "summary": title,
                    "description": description,
                    "start": {"dateTime": start_time, "timeZone": "UTC"},
                    "end": {"dateTime": end_time, "timeZone": "UTC"},
                }

                if location:
                    event["location"] = location
                if attendees:
                    event["attendees"] = [{"email": email} for email in attendees]

                result = (
                    service.events()
                    .insert(calendarId=calendar_id, body=event)
                    .execute()
                )

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"event_id": result.get("id"), "created": True},
                )

            elif action == "get":
                if not event_id:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="event_id is required for get action",
                    )

                result = (
                    service.events()
                    .get(calendarId=calendar_id, eventId=event_id)
                    .execute()
                )

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "event_id": result.get("id"),
                        "title": result.get("summary"),
                        "description": result.get("description"),
                        "start": result.get("start"),
                        "end": result.get("end"),
                        "location": result.get("location"),
                    },
                )

            elif action == "list":
                now = start_time or end_time or "Z"
                result = (
                    service.events()
                    .list(
                        calendarId=calendar_id,
                        timeMin=now,
                        maxResults=10,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )

                events = result.get("items", [])
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "events": [
                            {
                                "id": e.get("id"),
                                "title": e.get("summary"),
                                "start": e.get("start"),
                                "end": e.get("end"),
                            }
                            for e in events
                        ],
                        "count": len(events),
                    },
                )

            elif action == "delete":
                if not event_id:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="event_id is required for delete action",
                    )

                service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"deleted": True, "event_id": event_id},
                )

            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Action {action} not supported",
                )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Calendar operation failed: {str(e)}",
            )


class OutlookCalendarTool(Tool):
    """Manage calendar events via Microsoft Outlook."""

    name = "outlook_calendar"
    description = "Manage Outlook calendar events"

    parameters = {
        "action": "Operation: create, get, update, delete, list",
        "event_id": "Event ID (required for get, update, delete)",
        "subject": "Event subject",
        "body": "Event body",
        "start": "Start time (ISO 8601)",
        "end": "End time (ISO 8601)",
        "location": "Event location",
    }

    def __init__(self, credentials_path: str | None = None):
        self.credentials_path = credentials_path

    async def execute(
        self,
        action: str,
        event_id: str | None = None,
        subject: str | None = None,
        body: str | None = None,
        start: str | None = None,
        end: str | None = None,
        location: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        return ToolResult(
            status=ToolStatus.ERROR,
            error="Outlook Calendar not implemented yet. Use Google Calendar.",
        )
