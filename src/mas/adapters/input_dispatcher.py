"""Input dispatcher routes inputs to appropriate adapters."""

import logging

from mas.adapters.calendar_adapter import CalendarAdapter
from mas.adapters.contracts import (
    CalendarInput,
    DocumentInput,
    EmailInput,
    InputSource,
    TranscriptInput,
)
from mas.adapters.document_adapter import DocumentAdapter
from mas.adapters.email_adapter import EmailAdapter
from mas.adapters.transcript_adapter import TranscriptAdapter
from mas.domain.task import Task

logger = logging.getLogger(__name__)

AnyInput = EmailInput | CalendarInput | DocumentInput | TranscriptInput


class InputDispatcher:
    """Routes input sources to appropriate adapters."""

    def __init__(self) -> None:
        """Initialize dispatcher with all adapters."""
        self.email_adapter = EmailAdapter()
        self.calendar_adapter = CalendarAdapter()
        self.document_adapter = DocumentAdapter()
        self.transcript_adapter = TranscriptAdapter()

    def dispatch(
        self, input_source: InputSource, input_data: AnyInput, task_id: str | None = None
    ) -> Task:
        """Dispatch input to appropriate adapter.

        Args:
            input_source: Type of input source.
            input_data: Input data to convert.
            task_id: Optional task ID.

        Returns:
            Converted Task.

        Raises:
            ValueError: If input source is unknown.
        """
        if not isinstance(input_source, InputSource):
            raise ValueError(f"Unknown input source: {input_source}")

        logger.debug(
            f"Dispatching input of type {input_source.value}",
            extra={"source": input_source.value},
        )

        if input_source == InputSource.EMAIL:
            if not isinstance(input_data, EmailInput):
                raise ValueError(f"Expected EmailInput, got {type(input_data)}")
            return self.email_adapter.adapt(input_data, task_id)

        elif input_source == InputSource.CALENDAR:
            if not isinstance(input_data, CalendarInput):
                raise ValueError(f"Expected CalendarInput, got {type(input_data)}")
            return self.calendar_adapter.adapt(input_data, task_id)

        elif input_source == InputSource.DOCUMENT:
            if not isinstance(input_data, DocumentInput):
                raise ValueError(f"Expected DocumentInput, got {type(input_data)}")
            return self.document_adapter.adapt(input_data, task_id)

        elif input_source == InputSource.TRANSCRIPT:
            if not isinstance(input_data, TranscriptInput):
                raise ValueError(f"Expected TranscriptInput, got {type(input_data)}")
            return self.transcript_adapter.adapt(input_data, task_id)

        raise ValueError(f"Unknown input source: {input_source}")
