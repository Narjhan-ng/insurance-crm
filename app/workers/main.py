"""
ARQ Worker - Event Processor
Consumes events from Redis Streams and dispatches to handlers
"""
import asyncio
import json
import logging
from arq import create_pool
from arq.connections import RedisSettings
from redis.asyncio import Redis

from config.settings import settings
from app.handlers.prospect_handlers import (
    AuditLogHandler,
    NotifyBrokerHandler,
    SendWelcomeEmailHandler,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Handler registry - maps event types to handlers
EVENT_HANDLERS = {
    "ProspectCreated": [
        AuditLogHandler(),
        NotifyBrokerHandler(),
        SendWelcomeEmailHandler(),
    ],
    # Add more event types as needed
    # "QuoteGenerated": [QuoteEmailHandler(), ...],
    # "PolicySigned": [PolicyPDFHandler(), CommissionCalculator(), ...],
}


async def process_event(ctx, event_json: str):
    """
    ARQ task function - processes a single event.

    Args:
        ctx: ARQ context (contains redis connection, etc.)
        event_json: JSON string of the event data

    This function:
    1. Deserializes the event
    2. Finds matching handlers
    3. Executes each handler
    4. Logs results
    """
    try:
        event_data = json.loads(event_json)
        event_type = event_data.get("event_type")

        logger.info(f"Processing event: {event_type} (id={event_data.get('event_id')})")

        # Get handlers for this event type
        handlers = EVENT_HANDLERS.get(event_type, [])

        if not handlers:
            logger.warning(f"No handlers registered for event type: {event_type}")
            return

        # Execute each handler
        for handler in handlers:
            try:
                await handler.handle(event_data)
                logger.info(f"✅ Handler {handler.__class__.__name__} completed")
            except Exception as e:
                logger.error(
                    f"❌ Handler {handler.__class__.__name__} failed: {e}",
                    exc_info=True
                )
                # Continue with other handlers even if one fails

    except Exception as e:
        logger.error(f"Failed to process event: {e}", exc_info=True)
        raise  # Re-raise to let ARQ handle retry


async def consume_events_from_stream(redis: Redis, stream_name: str):
    """
    Consume events from Redis Stream and queue them to ARQ.

    This runs continuously, reading events from Redis Streams
    and dispatching them to the ARQ worker pool.
    """
    logger.info(f"📡 Listening for events on stream: {stream_name}")

    # Create ARQ pool
    arq_pool = await create_pool(RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DB,
    ))

    # Consumer group setup
    consumer_group = "insurance-crm-workers"
    consumer_name = "worker-1"

    try:
        # Create consumer group (ignore if already exists)
        await redis.xgroup_create(
            name=stream_name,
            groupname=consumer_group,
            id="0",
            mkstream=True
        )
    except Exception:
        # Group already exists, that's fine
        pass

    # Continuously read from stream
    while True:
        try:
            # Read messages from stream
            messages = await redis.xreadgroup(
                groupname=consumer_group,
                consumername=consumer_name,
                streams={stream_name: ">"},
                count=10,
                block=5000,  # Block for 5 seconds if no messages
            )

            for stream, message_list in messages:
                for message_id, data in message_list:
                    event_json = data.get(b"event", b"{}").decode("utf-8")

                    # Queue event to ARQ for processing
                    job = await arq_pool.enqueue_job(
                        "process_event",
                        event_json
                    )
                    logger.info(f"📨 Queued event for processing: job_id={job.job_id}")

                    # Acknowledge message
                    await redis.xack(stream_name, consumer_group, message_id)

        except Exception as e:
            logger.error(f"Error consuming events: {e}", exc_info=True)
            await asyncio.sleep(5)  # Wait before retrying


async def startup(ctx):
    """ARQ worker startup - called once when worker starts"""
    logger.info("🚀 ARQ Worker starting up...")
    ctx["startup_time"] = asyncio.get_event_loop().time()


async def shutdown(ctx):
    """ARQ worker shutdown - called when worker stops"""
    logger.info("🛑 ARQ Worker shutting down...")
    if "startup_time" in ctx:
        uptime = asyncio.get_event_loop().time() - ctx["startup_time"]
        logger.info(f"Worker uptime: {uptime:.2f} seconds")


# ARQ WorkerSettings
class WorkerSettings:
    """
    Configuration for ARQ worker.

    See: https://arq-docs.helpmanual.io/
    """
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DB,
    )

    functions = [process_event]
    on_startup = startup
    on_shutdown = shutdown

    # Worker configuration
    max_jobs = 10  # Maximum concurrent jobs
    job_timeout = 300  # Job timeout in seconds (5 minutes)
    keep_result = 3600  # Keep job results for 1 hour


async def main():
    """
    Main entry point for worker.
    Starts event stream consumer.
    """
    logger.info("🏭 Insurance CRM Event Worker")
    logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")

    # Create Redis connection for stream consumer
    redis = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=False,  # We handle decoding manually
    )

    try:
        await redis.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise

    # Start consuming events from different streams
    streams = [
        "insurance:events:prospect",
        "insurance:events:quote",
        "insurance:events:policy",
    ]

    tasks = [
        consume_events_from_stream(redis, stream)
        for stream in streams
    ]

    # Run all consumers concurrently
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    """
    Run worker:
    python -m app.workers.main

    Or use ARQ CLI:
    arq app.workers.main.WorkerSettings
    """
    asyncio.run(main())
