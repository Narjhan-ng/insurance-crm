"""
Event Publisher for publishing domain events to Redis Streams
"""
import json
import logging
from typing import Optional
from app.events.base import DomainEvent
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Publishes domain events to Redis Streams.

    Pattern:
    1. Event is serialized to JSON
    2. Published to Redis Stream: `insurance:events:{entity}`
    3. ARQ workers consume from these streams
    4. Workers dispatch to appropriate handlers

    Key design decisions:
    - Stream per entity type (prospect, quote, policy) for parallel processing
    - Events are stored in Redis for ~24h (configurable retention)
    - At-least-once delivery (workers ACK after successful processing)
    """

    STREAM_PREFIX = "insurance:events"
    MAX_STREAM_LENGTH = 10000  # Trim streams to prevent unbounded growth

    @classmethod
    async def publish(cls, event: DomainEvent, stream_name: Optional[str] = None) -> str:
        """
        Publish a domain event to Redis Streams.

        Args:
            event: The domain event to publish
            stream_name: Optional custom stream name (defaults to entity-based)

        Returns:
            Event ID from Redis (used for tracking)

        Raises:
            Exception if Redis is unavailable (fail fast)
        """
        redis_client = await get_redis()

        # Determine stream name based on event type
        if stream_name is None:
            stream_name = cls._get_stream_name(event.event_type)

        # Serialize event to JSON
        event_data = event.to_dict()
        event_json = json.dumps(event_data)

        try:
            # Publish to Redis Stream
            # XADD key [MAXLEN ~ length] * field value [field value ...]
            message_id = await redis_client.xadd(
                name=stream_name,
                fields={"event": event_json},
                maxlen=cls.MAX_STREAM_LENGTH,
                approximate=True  # Allow approximate trimming for performance
            )

            logger.info(
                f"Published event {event.event_type} "
                f"(id={event.event_id}) to stream {stream_name}, "
                f"message_id={message_id}"
            )

            return message_id

        except Exception as e:
            logger.error(
                f"Failed to publish event {event.event_type} "
                f"(id={event.event_id}): {str(e)}"
            )
            raise

    @classmethod
    def _get_stream_name(cls, event_type: str) -> str:
        """
        Determine Redis stream name based on event type.

        Pattern: insurance:events:{entity}

        Examples:
        - ProspectCreated → insurance:events:prospect
        - QuoteGenerated → insurance:events:quote
        - PolicySigned → insurance:events:policy
        """
        # Extract entity from event type (e.g., "ProspectCreated" → "prospect")
        if "Prospect" in event_type:
            entity = "prospect"
        elif "Quote" in event_type:
            entity = "quote"
        elif "Policy" in event_type:
            entity = "policy"
        elif "Commission" in event_type:
            entity = "commission"
        else:
            entity = "general"

        return f"{cls.STREAM_PREFIX}:{entity}"

    @classmethod
    async def publish_batch(cls, events: list[DomainEvent]) -> list[str]:
        """
        Publish multiple events efficiently.

        Useful for transactional operations that generate multiple events.
        Example: QuoteAccepted generates both PolicyCreated and CommissionCalculated.
        """
        message_ids = []
        for event in events:
            message_id = await cls.publish(event)
            message_ids.append(message_id)

        logger.info(f"Published batch of {len(events)} events")
        return message_ids
