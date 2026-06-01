"""Tests for input adapter contracts."""

import pytest

from mas.adapters.contracts import (
    InputSource,
    EmailInput,
    CalendarInput,
    DocumentInput,
    TranscriptInput,
)


class TestInputSource:
    """Tests for InputSource enum."""

    def test_email_source(self) -> None:
        """InputSource.EMAIL is defined."""
        assert InputSource.EMAIL == "email"

    def test_calendar_source(self) -> None:
        """InputSource.CALENDAR is defined."""
        assert InputSource.CALENDAR == "calendar"

    def test_document_source(self) -> None:
        """InputSource.DOCUMENT is defined."""
        assert InputSource.DOCUMENT == "document"

    def test_transcript_source(self) -> None:
        """InputSource.TRANSCRIPT is defined."""
        assert InputSource.TRANSCRIPT == "transcript"


class TestEmailInput:
    """Tests for EmailInput contract."""

    def test_create_email(self) -> None:
        """Can create email input with required fields."""
        email = EmailInput(
            sender="user@example.com",
            subject="Test",
            body="Test body",
        )

        assert email.sender == "user@example.com"
        assert email.subject == "Test"
        assert email.body == "Test body"

    def test_create_email_with_optional_fields(self) -> None:
        """Can create email with optional fields."""
        email = EmailInput(
            sender="user@example.com",
            subject="Test",
            body="Test body",
            recipients=["other@example.com"],
            timestamp="2026-06-01T10:00:00Z",
            attachments={"file.pdf": "content"},
        )

        assert email.recipients == ["other@example.com"]
        assert email.timestamp == "2026-06-01T10:00:00Z"
        assert "file.pdf" in email.attachments

    def test_reject_empty_sender(self) -> None:
        """Cannot create email with empty sender."""
        with pytest.raises(ValueError, match="sender cannot be empty"):
            EmailInput(sender="", subject="Test", body="Body")

    def test_reject_empty_subject(self) -> None:
        """Cannot create email with empty subject."""
        with pytest.raises(ValueError, match="subject cannot be empty"):
            EmailInput(sender="user@example.com", subject="", body="Body")

    def test_reject_empty_body(self) -> None:
        """Cannot create email with empty body."""
        with pytest.raises(ValueError, match="body cannot be empty"):
            EmailInput(sender="user@example.com", subject="Test", body="")

    def test_immutable(self) -> None:
        """EmailInput is immutable (frozen dataclass)."""
        email = EmailInput(sender="test@example.com", subject="Test", body="Body")

        with pytest.raises(AttributeError):
            email.sender = "modified@example.com"  # type: ignore


class TestCalendarInput:
    """Tests for CalendarInput contract."""

    def test_create_calendar_event(self) -> None:
        """Can create calendar event with required fields."""
        event = CalendarInput(
            title="Team Meeting",
            description="Discuss project",
            start_time="2026-06-01T10:00:00Z",
            end_time="2026-06-01T11:00:00Z",
        )

        assert event.title == "Team Meeting"
        assert event.description == "Discuss project"
        assert event.start_time == "2026-06-01T10:00:00Z"

    def test_create_calendar_event_with_optional_fields(self) -> None:
        """Can create calendar event with optional fields."""
        event = CalendarInput(
            title="Team Meeting",
            description="Discuss project",
            start_time="2026-06-01T10:00:00Z",
            end_time="2026-06-01T11:00:00Z",
            attendees=["alice@example.com", "bob@example.com"],
            location="Conference Room A",
        )

        assert event.attendees == ["alice@example.com", "bob@example.com"]
        assert event.location == "Conference Room A"

    def test_reject_empty_title(self) -> None:
        """Cannot create event with empty title."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            CalendarInput(
                title="",
                description="Test",
                start_time="2026-06-01T10:00:00Z",
                end_time="2026-06-01T11:00:00Z",
            )

    def test_immutable(self) -> None:
        """CalendarInput is immutable (frozen dataclass)."""
        event = CalendarInput(
            title="Meeting",
            description="Test",
            start_time="2026-06-01T10:00:00Z",
            end_time="2026-06-01T11:00:00Z",
        )

        with pytest.raises(AttributeError):
            event.title = "Modified"  # type: ignore


class TestDocumentInput:
    """Tests for DocumentInput contract."""

    def test_create_document(self) -> None:
        """Can create document input with required fields."""
        doc = DocumentInput(
            title="Report",
            content="Document content",
            document_type="pdf",
        )

        assert doc.title == "Report"
        assert doc.content == "Document content"
        assert doc.document_type == "pdf"

    def test_create_document_with_optional_fields(self) -> None:
        """Can create document with optional fields."""
        doc = DocumentInput(
            title="Report",
            content="Content",
            document_type="pdf",
            source_url="https://example.com/report.pdf",
            metadata={"author": "John Doe", "pages": 10},
        )

        assert doc.source_url == "https://example.com/report.pdf"
        assert doc.metadata["author"] == "John Doe"

    def test_reject_empty_title(self) -> None:
        """Cannot create document with empty title."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            DocumentInput(title="", content="Content", document_type="pdf")

    def test_reject_empty_content(self) -> None:
        """Cannot create document with empty content."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            DocumentInput(title="Report", content="", document_type="pdf")

    def test_reject_empty_document_type(self) -> None:
        """Cannot create document with empty document_type."""
        with pytest.raises(ValueError, match="document_type cannot be empty"):
            DocumentInput(title="Report", content="Content", document_type="")

    def test_immutable(self) -> None:
        """DocumentInput is immutable (frozen dataclass)."""
        doc = DocumentInput(
            title="Report",
            content="Content",
            document_type="pdf",
        )

        with pytest.raises(AttributeError):
            doc.title = "Modified"  # type: ignore


class TestTranscriptInput:
    """Tests for TranscriptInput contract."""

    def test_create_transcript(self) -> None:
        """Can create transcript input with required fields."""
        transcript = TranscriptInput(
            title="Team Standup",
            content="Meeting notes...",
        )

        assert transcript.title == "Team Standup"
        assert transcript.content == "Meeting notes..."

    def test_create_transcript_with_optional_fields(self) -> None:
        """Can create transcript with optional fields."""
        transcript = TranscriptInput(
            title="Team Standup",
            content="Notes",
            speaker_turns=[("Alice", "I completed the feature"), ("Bob", "Great!")],
            duration_seconds=600,
            source_type="meeting",
        )

        assert transcript.speaker_turns == [("Alice", "I completed the feature"), ("Bob", "Great!")]
        assert transcript.duration_seconds == 600
        assert transcript.source_type == "meeting"

    def test_reject_empty_title(self) -> None:
        """Cannot create transcript with empty title."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            TranscriptInput(title="", content="Content")

    def test_reject_empty_content(self) -> None:
        """Cannot create transcript with empty content."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            TranscriptInput(title="Meeting", content="")

    def test_reject_negative_duration(self) -> None:
        """Cannot create transcript with negative duration."""
        with pytest.raises(ValueError, match="duration_seconds cannot be negative"):
            TranscriptInput(
                title="Meeting",
                content="Content",
                duration_seconds=-100,
            )

    def test_immutable(self) -> None:
        """TranscriptInput is immutable (frozen dataclass)."""
        transcript = TranscriptInput(
            title="Meeting",
            content="Content",
        )

        with pytest.raises(AttributeError):
            transcript.title = "Modified"  # type: ignore
