"""Transcript to Task adapter."""

import logging
import uuid

from mas.adapters.contracts import TranscriptInput
from mas.domain.task import Task

logger = logging.getLogger(__name__)


class TranscriptAdapter:
    """Converts transcripts to Task contracts."""

    def adapt(self, transcript: TranscriptInput, task_id: str | None = None) -> Task:
        """Convert transcript to task.

        Args:
            transcript: Transcript to convert.
            task_id: Optional task ID. Generated if not provided.

        Returns:
            Task representing the transcript.
        """
        if task_id is None:
            task_id = f"transcript-{uuid.uuid4().hex[:12]}"

        logger.debug(
            f"Adapting transcript to task {task_id}",
            extra={"source": "transcript", "task_id": task_id},
        )

        content_preview = (
            transcript.content[:500] + "..."
            if len(transcript.content) > 500
            else transcript.content
        )

        duration_str = f"{transcript.duration_seconds // 60}m" if transcript.duration_seconds else "Unknown"

        description = (
            f"Transcript: {transcript.title}\n"
            f"Duration: {duration_str}\n"
            f"Type: {transcript.source_type or 'Unspecified'}\n\n"
            f"{content_preview}"
        )

        context = {
            "source_type": "transcript",
            "transcript_title": transcript.title,
            "source_type_detail": transcript.source_type,
            "duration_seconds": transcript.duration_seconds,
            "speaker_count": len({speaker for speaker, _ in transcript.speaker_turns}),
            "content_length": len(transcript.content),
        }

        task = Task(
            id=task_id,
            description=description,
            goal=f"Analyze transcript: {transcript.title}",
            context=context,
            metadata={"source": "transcript"},
        )

        logger.debug(
            f"Transcript adapted to task {task_id}",
            extra={"task_id": task_id, "transcript_title": transcript.title},
        )

        return task
