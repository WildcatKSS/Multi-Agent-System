"""Email to Task adapter."""

import logging

from mas.adapters.contracts import EmailInput
from mas.domain.task import Task

logger = logging.getLogger(__name__)


class EmailAdapter:
    """Converts email messages to Task contracts."""

    def adapt(self, email: EmailInput, task_id: str | None = None) -> Task:
        """Convert email to task.

        Args:
            email: Email input to convert.
            task_id: Optional task ID. Generated if not provided.

        Returns:
            Task representing the email.
        """
        if task_id is None:
            task_id = f"email-{hash(email.sender + email.subject) % 10000000:07d}"

        logger.debug(
            f"Adapting email to task {task_id}",
            extra={"source": "email", "task_id": task_id},
        )

        description = f"Process email from {email.sender}\n\nSubject: {email.subject}\n\n{email.body}"

        context = {
            "source_type": "email",
            "sender": email.sender,
            "recipients": email.recipients,
            "subject": email.subject,
            "timestamp": email.timestamp,
            "attachments": list(email.attachments.keys()),
        }

        task = Task(
            id=task_id,
            description=description,
            goal=f"Handle email regarding: {email.subject}",
            context=context,
            metadata={"source": "email"},
        )

        logger.debug(
            f"Email adapted to task {task_id}",
            extra={"task_id": task_id, "sender": email.sender},
        )

        return task
