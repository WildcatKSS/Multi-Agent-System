"""Document to Task adapter."""

import logging

from mas.adapters.contracts import DocumentInput
from mas.domain.task import Task

logger = logging.getLogger(__name__)


class DocumentAdapter:
    """Converts documents to Task contracts."""

    def adapt(self, document: DocumentInput, task_id: str | None = None) -> Task:
        """Convert document to task.

        Args:
            document: Document to convert.
            task_id: Optional task ID. Generated if not provided.

        Returns:
            Task representing the document.
        """
        if task_id is None:
            task_id = f"doc-{hash(document.title + document.document_type) % 10000000:07d}"

        logger.debug(
            f"Adapting document to task {task_id}",
            extra={"source": "document", "task_id": task_id},
        )

        content_preview = (
            document.content[:500] + "..."
            if len(document.content) > 500
            else document.content
        )

        description = (
            f"Document: {document.title}\n"
            f"Type: {document.document_type}\n\n"
            f"{content_preview}"
        )

        context = {
            "source_type": "document",
            "document_title": document.title,
            "document_type": document.document_type,
            "source_url": document.source_url,
            "content_length": len(document.content),
        }

        context.update(document.metadata)

        task = Task(
            id=task_id,
            description=description,
            goal=f"Process document: {document.title}",
            context=context,
            metadata={"source": "document"},
        )

        logger.debug(
            f"Document adapted to task {task_id}",
            extra={"task_id": task_id, "doc_title": document.title},
        )

        return task
