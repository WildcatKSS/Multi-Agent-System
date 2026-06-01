"""Tests for input dispatcher."""

import pytest

from mas.adapters.contracts import (
    InputSource,
    EmailInput,
    CalendarInput,
    DocumentInput,
    TranscriptInput,
)
from mas.adapters.input_dispatcher import InputDispatcher
from mas.domain.task import Task


class TestInputDispatcher:
    """Tests for InputDispatcher."""

    def test_dispatcher_initialization(self) -> None:
        """Can initialize dispatcher."""
        dispatcher = InputDispatcher()

        assert dispatcher.email_adapter is not None
        assert dispatcher.calendar_adapter is not None
        assert dispatcher.document_adapter is not None
        assert dispatcher.transcript_adapter is not None

    def test_dispatch_email_input(self) -> None:
        """Can dispatch email input."""
        dispatcher = InputDispatcher()

        email = EmailInput(
            sender="user@example.com",
            subject="Test",
            body="Body",
        )

        task = dispatcher.dispatch(InputSource.EMAIL, email)

        assert isinstance(task, Task)
        assert task.context["source_type"] == "email"

    def test_dispatch_calendar_input(self) -> None:
        """Can dispatch calendar input."""
        dispatcher = InputDispatcher()

        event = CalendarInput(
            title="Meeting",
            description="Test",
            start_time="2026-06-01T10:00:00Z",
            end_time="2026-06-01T11:00:00Z",
        )

        task = dispatcher.dispatch(InputSource.CALENDAR, event)

        assert isinstance(task, Task)
        assert task.context["source_type"] == "calendar"

    def test_dispatch_document_input(self) -> None:
        """Can dispatch document input."""
        dispatcher = InputDispatcher()

        doc = DocumentInput(
            title="Report",
            content="Content",
            document_type="pdf",
        )

        task = dispatcher.dispatch(InputSource.DOCUMENT, doc)

        assert isinstance(task, Task)
        assert task.context["source_type"] == "document"

    def test_dispatch_transcript_input(self) -> None:
        """Can dispatch transcript input."""
        dispatcher = InputDispatcher()

        transcript = TranscriptInput(
            title="Meeting",
            content="Content",
        )

        task = dispatcher.dispatch(InputSource.TRANSCRIPT, transcript)

        assert isinstance(task, Task)
        assert task.context["source_type"] == "transcript"

    def test_dispatch_with_custom_task_id(self) -> None:
        """Can dispatch with custom task ID."""
        dispatcher = InputDispatcher()

        email = EmailInput(
            sender="user@example.com",
            subject="Test",
            body="Body",
        )

        task = dispatcher.dispatch(
            InputSource.EMAIL, email, task_id="custom-task-001"
        )

        assert task.id == "custom-task-001"

    def test_dispatch_rejects_mismatched_types(self) -> None:
        """Dispatcher rejects mismatched input types."""
        dispatcher = InputDispatcher()

        email = EmailInput(
            sender="user@example.com",
            subject="Test",
            body="Body",
        )

        with pytest.raises(ValueError, match="Expected CalendarInput"):
            dispatcher.dispatch(InputSource.CALENDAR, email)

    def test_dispatch_rejects_unknown_source(self) -> None:
        """Dispatcher rejects unknown input sources."""
        dispatcher = InputDispatcher()

        email = EmailInput(
            sender="user@example.com",
            subject="Test",
            body="Body",
        )

        with pytest.raises(ValueError, match="Unknown input source"):
            # Manually create an invalid source
            dispatcher.dispatch("invalid_source", email)  # type: ignore


class TestDispatcherIntegration:
    """Integration tests for dispatcher with all input types."""

    def test_dispatcher_handles_all_input_types(self) -> None:
        """Dispatcher can handle all four input types."""
        dispatcher = InputDispatcher()

        inputs = [
            (
                InputSource.EMAIL,
                EmailInput(
                    sender="test@example.com",
                    subject="Test",
                    body="Body",
                ),
            ),
            (
                InputSource.CALENDAR,
                CalendarInput(
                    title="Meeting",
                    description="Test",
                    start_time="2026-06-01T10:00:00Z",
                    end_time="2026-06-01T11:00:00Z",
                ),
            ),
            (
                InputSource.DOCUMENT,
                DocumentInput(
                    title="Report",
                    content="Content",
                    document_type="pdf",
                ),
            ),
            (
                InputSource.TRANSCRIPT,
                TranscriptInput(
                    title="Meeting",
                    content="Content",
                ),
            ),
        ]

        for source, input_obj in inputs:
            task = dispatcher.dispatch(source, input_obj)

            assert isinstance(task, Task)
            assert task.id
            assert task.description
            assert task.goal
            assert task.context["source_type"] == source.value

    def test_dispatcher_produces_different_task_ids(self) -> None:
        """Dispatcher produces different task IDs for different inputs."""
        dispatcher = InputDispatcher()

        email1 = EmailInput(
            sender="user1@example.com",
            subject="Test1",
            body="Body1",
        )
        email2 = EmailInput(
            sender="user2@example.com",
            subject="Test2",
            body="Body2",
        )

        task1 = dispatcher.dispatch(InputSource.EMAIL, email1)
        task2 = dispatcher.dispatch(InputSource.EMAIL, email2)

        assert task1.id != task2.id

    def test_dispatcher_batch_processing(self) -> None:
        """Can process multiple inputs sequentially."""
        dispatcher = InputDispatcher()

        tasks = []

        # Process email
        email = EmailInput(
            sender="user@example.com",
            subject="Test",
            body="Body",
        )
        tasks.append(dispatcher.dispatch(InputSource.EMAIL, email))

        # Process calendar
        event = CalendarInput(
            title="Meeting",
            description="Test",
            start_time="2026-06-01T10:00:00Z",
            end_time="2026-06-01T11:00:00Z",
        )
        tasks.append(dispatcher.dispatch(InputSource.CALENDAR, event))

        # Process document
        doc = DocumentInput(
            title="Report",
            content="Content",
            document_type="pdf",
        )
        tasks.append(dispatcher.dispatch(InputSource.DOCUMENT, doc))

        assert len(tasks) == 3
        for task in tasks:
            assert isinstance(task, Task)
            assert task.id
