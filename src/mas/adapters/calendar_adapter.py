"""Calendar event to Task adapter."""

import logging
import uuid

from mas.adapters.contracts import CalendarInput
from mas.domain.task import Task

logger = logging.getLogger(__name__)


class CalendarAdapter:
    """Converts calendar events to Task contracts."""

    def adapt(self, event: CalendarInput, task_id: str | None = None) -> Task:
        """Convert calendar event to task.

        Args:
            event: Calendar event to convert.
            task_id: Optional task ID. Generated if not provided.

        Returns:
            Task representing the calendar event.
        """
        if task_id is None:
            task_id = f"calendar-{uuid.uuid4().hex[:12]}"

        logger.debug(
            f"Adapting calendar event to task {task_id}",
            extra={"source": "calendar", "task_id": task_id},
        )

        attendees_str = ", ".join(event.attendees) if event.attendees else "No attendees"
        location_str = f" at {event.location}" if event.location else ""

        description = (
            f"Calendar event: {event.title}{location_str}\n\n"
            f"Time: {event.start_time} to {event.end_time}\n"
            f"Attendees: {attendees_str}\n\n"
            f"{event.description}"
        )

        context = {
            "source_type": "calendar",
            "event_title": event.title,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "attendees": event.attendees,
            "location": event.location,
        }

        task = Task(
            id=task_id,
            description=description,
            goal=f"Prepare for: {event.title}",
            context=context,
            metadata={"source": "calendar"},
        )

        logger.debug(
            f"Calendar event adapted to task {task_id}",
            extra={"task_id": task_id, "event_title": event.title},
        )

        return task
