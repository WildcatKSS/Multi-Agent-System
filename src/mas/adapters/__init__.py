"""Input Adapters module for converting various input sources to Task contracts.

Provides adapters for Email, Calendar, Document, and Transcript inputs,
normalizing them into a unified Task format for workflow execution.
"""

from mas.adapters.contracts import InputSource, EmailInput, CalendarInput, DocumentInput, TranscriptInput
from mas.adapters.email_adapter import EmailAdapter
from mas.adapters.calendar_adapter import CalendarAdapter
from mas.adapters.document_adapter import DocumentAdapter
from mas.adapters.transcript_adapter import TranscriptAdapter
from mas.adapters.input_dispatcher import InputDispatcher

__all__ = [
    "InputSource",
    "EmailInput",
    "CalendarInput",
    "DocumentInput",
    "TranscriptInput",
    "EmailAdapter",
    "CalendarAdapter",
    "DocumentAdapter",
    "TranscriptAdapter",
    "InputDispatcher",
]
