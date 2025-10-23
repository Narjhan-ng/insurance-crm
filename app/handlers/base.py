"""
Base event handler infrastructure
"""
import logging
from typing import Protocol
from app.events.base import DomainEvent

logger = logging.getLogger(__name__)


class EventHandler(Protocol):
    """
    Protocol for event handlers.

    All event handlers must implement the `handle` method.

    Key principles:
    - **Idempotent**: Can be called multiple times with same event, same result
    - **Isolated**: Failure doesn't affect other handlers
    - **Async**: Non-blocking for performance
    - **Logged**: All actions logged for debugging
    """

    async def handle(self, event: DomainEvent) -> None:
        """
        Handle a domain event.

        Args:
            event: The domain event to process

        Raises:
            Exception: If handling fails (will trigger retry)
        """
        ...


class BaseEventHandler:
    """
    Base class for event handlers with common functionality.

    Provides:
    - Logging
    - Error handling
    - Idempotency helpers
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def handle(self, event: DomainEvent) -> None:
        """
        Handle event with logging and error handling.

        Subclasses should override `_handle` instead of this method.
        """
        self.logger.info(f"Handling {event.event_type} (id={event.event_id})")

        try:
            await self._handle(event)
            self.logger.info(f"Successfully handled {event.event_type} (id={event.event_id})")

        except Exception as e:
            self.logger.error(
                f"Error handling {event.event_type} (id={event.event_id}): {str(e)}",
                exc_info=True
            )
            raise  # Re-raise for retry logic

    async def _handle(self, event: DomainEvent) -> None:
        """
        Actual event handling logic.

        Override this in subclasses.
        """
        raise NotImplementedError("Subclasses must implement _handle()")
