"""Tests for input adapters."""

import pytest

from mas.adapters.contracts import (
    EmailInput,
    CalendarInput,
    DocumentInput,
    TranscriptInput,
)
from mas.adapters.email_adapter import EmailAdapter
from mas.adapters.calendar_adapter import CalendarAdapter
from mas.adapters.document_adapter import DocumentAdapter
from mas.adapters.transcript_adapter import TranscriptAdapter
from mas.domain.task import Task


class TestEmailAdapter:
    """Tests for EmailAdapter."""

    def test_adapt_email_to_task(self) -> None:
        """Can adapt email to task."""
        adapter = EmailAdapter()

        email = EmailInput(
            sender="user@example.com",
            subject="Urgent: Action Required",
            body="Please review the attached document",
        )

        task = adapter.adapt(email)

        assert isinstance(task, Task)
        assert task.id.startswith("email-")
        assert "Urgent: Action Required" in task.goal
        assert "user@example.com" in task.context["sender"]

    def test_adapt_email_with_custom_task_id(self) -> None:
        """Can adapt email with custom task ID."""
        adapter = EmailAdapter()

        email = EmailInput(
            sender="user@example.com",
            subject="Test",
            body="Body",
        )

        task = adapter.adapt(email, task_id="custom-email-001")

        assert task.id == "custom-email-001"

    def test_email_task_includes_metadata(self) -> None:
        """Email task includes source metadata."""
        adapter = EmailAdapter()

        email = EmailInput(
            sender="user@example.com",
            subject="Test",
            body="Body",
            recipients=["other@example.com"],
            timestamp="2026-06-01T10:00:00Z",
        )

        task = adapter.adapt(email)

        assert task.metadata["source"] == "email"
        assert task.context["source_type"] == "email"
        assert task.context["recipients"] == ["other@example.com"]


class TestCalendarAdapter:
    """Tests for CalendarAdapter."""

    def test_adapt_calendar_event_to_task(self) -> None:
        """Can adapt calendar event to task."""
        adapter = CalendarAdapter()

        event = CalendarInput(
            title="Team Meeting",
            description="Discuss roadmap",
            start_time="2026-06-01T10:00:00Z",
            end_time="2026-06-01T11:00:00Z",
        )

        task = adapter.adapt(event)

        assert isinstance(task, Task)
        assert task.id.startswith("calendar-")
        assert "Team Meeting" in task.goal
        assert "2026-06-01T10:00:00Z" in task.context["start_time"]

    def test_adapt_calendar_with_custom_task_id(self) -> None:
        """Can adapt calendar event with custom task ID."""
        adapter = CalendarAdapter()

        event = CalendarInput(
            title="Meeting",
            description="Test",
            start_time="2026-06-01T10:00:00Z",
            end_time="2026-06-01T11:00:00Z",
        )

        task = adapter.adapt(event, task_id="custom-calendar-001")

        assert task.id == "custom-calendar-001"

    def test_calendar_task_includes_attendees(self) -> None:
        """Calendar task includes attendee information."""
        adapter = CalendarAdapter()

        event = CalendarInput(
            title="Meeting",
            description="Test",
            start_time="2026-06-01T10:00:00Z",
            end_time="2026-06-01T11:00:00Z",
            attendees=["alice@example.com", "bob@example.com"],
            location="Conference Room",
        )

        task = adapter.adapt(event)

        assert task.context["attendees"] == ["alice@example.com", "bob@example.com"]
        assert task.context["location"] == "Conference Room"


class TestDocumentAdapter:
    """Tests for DocumentAdapter."""

    def test_adapt_document_to_task(self) -> None:
        """Can adapt document to task."""
        adapter = DocumentAdapter()

        doc = DocumentInput(
            title="Project Proposal",
            content="This is a proposal document with details...",
            document_type="pdf",
        )

        task = adapter.adapt(doc)

        assert isinstance(task, Task)
        assert task.id.startswith("doc-")
        assert "Project Proposal" in task.goal
        assert "pdf" in task.context["document_type"]

    def test_adapt_document_with_custom_task_id(self) -> None:
        """Can adapt document with custom task ID."""
        adapter = DocumentAdapter()

        doc = DocumentInput(
            title="Report",
            content="Content",
            document_type="txt",
        )

        task = adapter.adapt(doc, task_id="custom-doc-001")

        assert task.id == "custom-doc-001"

    def test_document_task_truncates_long_content(self) -> None:
        """Document task truncates very long content in description."""
        adapter = DocumentAdapter()

        long_content = "x" * 1000

        doc = DocumentInput(
            title="Large Document",
            content=long_content,
            document_type="pdf",
        )

        task = adapter.adapt(doc)

        assert len(task.description) < len(long_content)
        assert "..." in task.description


class TestTranscriptAdapter:
    """Tests for TranscriptAdapter."""

    def test_adapt_transcript_to_task(self) -> None:
        """Can adapt transcript to task."""
        adapter = TranscriptAdapter()

        transcript = TranscriptInput(
            title="All-Hands Meeting",
            content="Discussion about company direction...",
        )

        task = adapter.adapt(transcript)

        assert isinstance(task, Task)
        assert task.id.startswith("transcript-")
        assert "All-Hands Meeting" in task.goal

    def test_adapt_transcript_with_custom_task_id(self) -> None:
        """Can adapt transcript with custom task ID."""
        adapter = TranscriptAdapter()

        transcript = TranscriptInput(
            title="Meeting",
            content="Content",
        )

        task = adapter.adapt(transcript, task_id="custom-transcript-001")

        assert task.id == "custom-transcript-001"

    def test_transcript_task_includes_speaker_info(self) -> None:
        """Transcript task includes speaker information."""
        adapter = TranscriptAdapter()

        transcript = TranscriptInput(
            title="Team Sync",
            content="Meeting notes",
            speaker_turns=[
                ("Alice", "I have updates"),
                ("Bob", "Thanks Alice"),
                ("Alice", "Any questions?"),
            ],
            duration_seconds=1800,
            source_type="meeting",
        )

        task = adapter.adapt(transcript)

        assert task.context["speaker_count"] == 2
        assert task.context["duration_seconds"] == 1800
        assert task.context["source_type_detail"] == "meeting"


class TestAdapterTaskQuality:
    """Tests for task quality across adapters."""

    def test_all_adapted_tasks_have_valid_structure(self) -> None:
        """All adapted tasks have required Task fields."""
        email_adapter = EmailAdapter()
        calendar_adapter = CalendarAdapter()
        document_adapter = DocumentAdapter()
        transcript_adapter = TranscriptAdapter()

        email = EmailInput(sender="test@example.com", subject="Test", body="Body")
        event = CalendarInput(
            title="Meeting",
            description="Test",
            start_time="2026-06-01T10:00:00Z",
            end_time="2026-06-01T11:00:00Z",
        )
        doc = DocumentInput(title="Report", content="Content", document_type="pdf")
        transcript = TranscriptInput(title="Meeting", content="Content")

        for adapter, input_obj in [
            (email_adapter, email),
            (calendar_adapter, event),
            (document_adapter, doc),
            (transcript_adapter, transcript),
        ]:
            task = adapter.adapt(input_obj)

            assert task.id
            assert task.description
            assert task.goal
            assert task.context
            assert task.metadata["source"]

    def test_adapted_tasks_have_consistent_metadata(self) -> None:
        """All adapted tasks have source metadata."""
        email_adapter = EmailAdapter()

        email = EmailInput(sender="test@example.com", subject="Test", body="Body")
        task = email_adapter.adapt(email)

        assert "source" in task.metadata
        assert task.metadata["source"] == "email"
        assert "source_type" in task.context
        assert task.context["source_type"] == "email"
