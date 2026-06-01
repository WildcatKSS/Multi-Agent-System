"""Input adapter contracts and data structures."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class InputSource(str, Enum):
    """Type of input source."""

    EMAIL = "email"
    """Email message input."""

    CALENDAR = "calendar"
    """Calendar event input."""

    DOCUMENT = "document"
    """Document input (PDF, text, etc.)."""

    TRANSCRIPT = "transcript"
    """Transcript input (meeting, call, etc.)."""


@dataclass(frozen=True)
class EmailInput:
    """Email message as input source."""

    sender: str
    """Email sender address."""

    subject: str
    """Email subject line."""

    body: str
    """Email body content."""

    recipients: list[str] = field(default_factory=list)
    """Email recipients."""

    timestamp: str = ""
    """Email sent timestamp (ISO 8601)."""

    attachments: dict = field(default_factory=dict)
    """Email attachments (name -> content)."""

    def __post_init__(self) -> None:
        """Validate email input on creation."""
        if not self.sender:
            raise ValueError("sender cannot be empty")
        if not self.subject:
            raise ValueError("subject cannot be empty")
        if not self.body:
            raise ValueError("body cannot be empty")


@dataclass(frozen=True)
class CalendarInput:
    """Calendar event as input source."""

    title: str
    """Event title."""

    description: str
    """Event description."""

    start_time: str
    """Event start time (ISO 8601)."""

    end_time: str
    """Event end time (ISO 8601)."""

    attendees: list[str] = field(default_factory=list)
    """Event attendees."""

    location: str = ""
    """Event location."""

    def __post_init__(self) -> None:
        """Validate calendar input on creation."""
        if not self.title:
            raise ValueError("title cannot be empty")
        if not self.description:
            raise ValueError("description cannot be empty")
        if not self.start_time:
            raise ValueError("start_time cannot be empty")
        if not self.end_time:
            raise ValueError("end_time cannot be empty")


@dataclass(frozen=True)
class DocumentInput:
    """Document as input source."""

    title: str
    """Document title."""

    content: str
    """Document content (text)."""

    document_type: str
    """Document type (pdf, text, markdown, etc.)."""

    source_url: str = ""
    """Source URL if applicable."""

    metadata: dict = field(default_factory=dict)
    """Additional document metadata."""

    def __post_init__(self) -> None:
        """Validate document input on creation."""
        if not self.title:
            raise ValueError("title cannot be empty")
        if not self.content:
            raise ValueError("content cannot be empty")
        if not self.document_type:
            raise ValueError("document_type cannot be empty")


@dataclass(frozen=True)
class TranscriptInput:
    """Transcript as input source."""

    title: str
    """Transcript title (e.g., meeting name)."""

    content: str
    """Transcript content (full text)."""

    speaker_turns: list = field(default_factory=list)
    """Speaker turns as list of (speaker, text) tuples."""

    duration_seconds: int = 0
    """Duration in seconds."""

    source_type: str = ""
    """Source type (meeting, call, lecture, etc.)."""

    def __post_init__(self) -> None:
        """Validate transcript input on creation."""
        if not self.title:
            raise ValueError("title cannot be empty")
        if not self.content:
            raise ValueError("content cannot be empty")
        if self.duration_seconds < 0:
            raise ValueError("duration_seconds cannot be negative")
