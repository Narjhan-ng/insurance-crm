"""
Event handlers for Prospect domain events
"""
from app.handlers.base import BaseEventHandler
from app.events.prospect_events import ProspectCreated


class AuditLogHandler(BaseEventHandler):
    """
    Records prospect creation in audit log for compliance.

    Why separate handler?
    - Audit logging is a cross-cutting concern
    - Should never fail main business logic
    - Easy to add/remove without touching code
    - Can be replaced with external audit service later
    """

    async def _handle(self, event: ProspectCreated) -> None:
        """
        Log prospect creation to audit trail.

        In production, this would write to:
        - Dedicated audit_log table
        - External audit service (e.g., AWS CloudTrail)
        - Compliance database

        For now: structured logging (can be ingested by ELK/Splunk)
        """
        self.logger.info(
            "AUDIT: Prospect created",
            extra={
                "event_id": event.event_id,
                "prospect_id": event.prospect_id,
                "prospect_type": event.prospect_type,
                "created_by_user_id": event.user_id,
                "timestamp": event.timestamp.isoformat(),
                "action": "prospect.created"
            }
        )

        # TODO: In production, write to audit_log table:
        # await audit_log_repository.create(
        #     event_id=event.event_id,
        #     entity_type="prospect",
        #     entity_id=event.prospect_id,
        #     action="created",
        #     user_id=event.user_id,
        #     timestamp=event.timestamp,
        #     metadata=event.to_dict()
        # )


class NotifyBrokerHandler(BaseEventHandler):
    """
    Notifies assigned broker when new prospect is created.

    Business logic:
    - If broker is assigned, send notification (email/SMS/push)
    - Include prospect details for quick action
    - Track notification delivery

    Why separate handler?
    - Notification is side-effect, not core business logic
    - Can fail without affecting prospect creation
    - Easy to add other notification channels (SMS, Slack, etc.)
    """

    async def _handle(self, event: ProspectCreated) -> None:
        """Send notification to assigned broker"""

        if not event.assigned_broker_id:
            self.logger.info(f"No broker assigned for prospect {event.prospect_id}, skipping notification")
            return

        # TODO: Fetch broker details from database
        # broker = await user_repository.get_by_id(event.assigned_broker_id)

        # For now: log the notification (in production, send actual email/SMS)
        self.logger.info(
            f"NOTIFICATION: New prospect {event.prospect_id} assigned to broker {event.assigned_broker_id}",
            extra={
                "broker_id": event.assigned_broker_id,
                "prospect_id": event.prospect_id,
                "prospect_name": event.full_name,
                "prospect_type": event.prospect_type,
                "notification_type": "email"
            }
        )

        # TODO: In production, send actual notification:
        # await email_service.send(
        #     to=broker.email,
        #     subject=f"New {event.prospect_type} prospect assigned: {event.full_name}",
        #     template="broker_new_prospect_assigned",
        #     context={
        #         "broker_name": broker.first_name,
        #         "prospect_name": event.full_name,
        #         "prospect_type": event.prospect_type,
        #         "prospect_id": event.prospect_id,
        #         "dashboard_url": f"{settings.APP_URL}/prospects/{event.prospect_id}"
        #     }
        # )


class SendWelcomeEmailHandler(BaseEventHandler):
    """
    Sends welcome email to newly created prospect.

    Business logic:
    - Only if email is provided
    - Personalized based on prospect type (individual/family/business)
    - Include next steps and contact info

    Why separate handler?
    - Marketing/communication concern, not core business logic
    - Can be toggled on/off via feature flag
    - Easy to A/B test different email templates
    - Failure doesn't affect prospect creation
    """

    async def _handle(self, event: ProspectCreated) -> None:
        """Send welcome email to prospect"""

        if not event.email:
            self.logger.info(f"No email for prospect {event.prospect_id}, skipping welcome email")
            return

        # Determine email template based on prospect type
        template_map = {
            "individual": "welcome_individual",
            "family": "welcome_family",
            "business": "welcome_business"
        }
        template = template_map.get(event.prospect_type, "welcome_generic")

        # For now: log the email (in production, send via SendGrid/SES)
        self.logger.info(
            f"EMAIL: Welcome email sent to prospect {event.prospect_id}",
            extra={
                "prospect_id": event.prospect_id,
                "email": event.email,
                "template": template,
                "prospect_name": event.full_name
            }
        )

        # TODO: In production, send actual email:
        # await email_service.send(
        #     to=event.email,
        #     subject=f"Welcome to Insurance CRM, {event.first_name}!",
        #     template=template,
        #     context={
        #         "prospect_name": event.first_name or "there",
        #         "prospect_type": event.prospect_type,
        #         "contact_email": "support@insurance-crm.com",
        #         "contact_phone": "+1-555-INSURE"
        #     }
        # )


class UpdateProspectDashboardHandler(BaseEventHandler):
    """
    Updates real-time dashboard metrics when prospect is created.

    Business logic:
    - Increment "total prospects" counter
    - Update "prospects by type" breakdown
    - Refresh broker's prospect count
    - Trigger WebSocket notification to connected dashboards

    Why separate handler?
    - Dashboard is read-side concern (CQRS pattern)
    - Can use denormalized data structures for fast queries
    - Easy to add caching layer (Redis) without changing code
    """

    async def _handle(self, event: ProspectCreated) -> None:
        """Update dashboard metrics"""

        self.logger.info(
            f"DASHBOARD: Updating metrics for new prospect {event.prospect_id}",
            extra={
                "prospect_id": event.prospect_id,
                "prospect_type": event.prospect_type,
                "broker_id": event.assigned_broker_id
            }
        )

        # TODO: In production, update dashboard cache:
        # redis_client = await get_redis()
        #
        # # Increment counters
        # await redis_client.hincrby("dashboard:metrics", "total_prospects", 1)
        # await redis_client.hincrby("dashboard:metrics", f"prospects_{event.prospect_type}", 1)
        #
        # if event.assigned_broker_id:
        #     await redis_client.hincrby(
        #         f"dashboard:broker:{event.assigned_broker_id}",
        #         "prospect_count",
        #         1
        #     )
        #
        # # Trigger WebSocket notification
        # await websocket_manager.broadcast({
        #     "type": "prospect_created",
        #     "prospect_id": event.prospect_id,
        #     "prospect_type": event.prospect_type
        # })
