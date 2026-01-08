"""
GraphQL mutations for Class Sessions
"""
from typing import List
import logging
import strawberry
from strawberry.types import Info

from app.crud.classSessionCrud import (
    create_class_session,
    update_session_capacity,
    update_session_status,
    cancel_session,
    generate_sessions_from_template
)
from app.services.session_generator import SessionGeneratorService
from app.graphql.auth.permissions import IsAuthenticated
from .types import (
    ClassSession,
    ClassSessionResponse,
    SessionGenerationResponse,
    GenerateAndMaterializeResponse,
    MaintenanceResponse,
    CreateClassSessionInput,
    UpdateSessionCapacityInput,
    UpdateSessionStatusInput,
    GenerateSessionsInput,
    GenerateFutureSessionsInput,
    GenerateAndMaterializeInput,
    EmergencySessionGenerationInput,
    convert_generation_stats
)

logger = logging.getLogger(__name__)


@strawberry.type
class ClassSessionMutations:
    """Class Session mutations"""

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def create_class_session(
        self,
        info: Info,
        input: CreateClassSessionInput
    ) -> ClassSessionResponse:
        """Create a new class session"""
        db = info.context.db

        try:
            session = await create_class_session(
                db=db,
                template_id=input.template_id,
                class_type_id=input.class_type_id,
                venue_id=input.venue_id,
                start_at=input.start_at,
                end_at=input.end_at,
                capacity=input.capacity,
                instructor_id=input.instructor_id,
                name=input.name,
                status=input.status
            )

            return ClassSessionResponse(
                success=True,
                session=ClassSession.from_model(session),
                message="Class session created successfully"
            )

        except Exception as e:
            return ClassSessionResponse(
                success=False,
                session=None,
                message=f"Error creating session: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def update_session_capacity(
        self,
        info: Info,
        input: UpdateSessionCapacityInput
    ) -> ClassSessionResponse:
        """Update session capacity"""
        db = info.context.db

        try:
            session = await update_session_capacity(
                db=db,
                session_id=input.session_id,
                new_capacity=input.new_capacity
            )

            if session:
                return ClassSessionResponse(
                    success=True,
                    session=ClassSession.from_model(session),
                    message="Session capacity updated successfully"
                )
            else:
                return ClassSessionResponse(
                    success=False,
                    session=None,
                    message="Session not found"
                )

        except Exception as e:
            return ClassSessionResponse(
                success=False,
                session=None,
                message=f"Error updating capacity: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def update_session_status(
        self,
        info: Info,
        input: UpdateSessionStatusInput
    ) -> ClassSessionResponse:
        """Update session status"""
        db = info.context.db

        try:
            session = await update_session_status(
                db=db,
                session_id=input.session_id,
                new_status=input.new_status
            )

            if session:
                return ClassSessionResponse(
                    success=True,
                    session=ClassSession.from_model(session),
                    message="Session status updated successfully"
                )
            else:
                return ClassSessionResponse(
                    success=False,
                    session=None,
                    message="Session not found"
                )

        except Exception as e:
            return ClassSessionResponse(
                success=False,
                session=None,
                message=f"Error updating status: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def cancel_session(
        self,
        info: Info,
        session_id: int,
        cancel_reservations: bool = True
    ) -> ClassSessionResponse:
        """Cancel a session and optionally cancel reservations"""
        db = info.context.db

        try:
            session = await cancel_session(
                db=db,
                session_id=session_id,
                cancel_reservations=cancel_reservations
            )

            if session:
                return ClassSessionResponse(
                    success=True,
                    session=ClassSession.from_model(session),
                    message="Session canceled successfully"
                )
            else:
                return ClassSessionResponse(
                    success=False,
                    session=None,
                    message="Session not found"
                )

        except Exception as e:
            return ClassSessionResponse(
                success=False,
                session=None,
                message=f"Error canceling session: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def generate_sessions_from_template(
        self,
        info: Info,
        input: GenerateSessionsInput
    ) -> SessionGenerationResponse:
        """Generate sessions from a template for specific date range"""
        db = info.context.db

        try:
            sessions = await generate_sessions_from_template(
                db=db,
                template_id=input.template_id,
                start_date=input.start_date,
                end_date=input.end_date
            )

            if sessions:
                try:
                    from app.crud.standingBookingsCrud import materialize_standing_bookings_for_session
                    created_total = 0
                    for session in sessions:
                        stats = await materialize_standing_bookings_for_session(db, session.id)
                        created_total += int(stats.get("created_reservations", 0))
                    if created_total > 0:
                        await db.commit()
                except Exception as exc:
                    await db.rollback()
                    logger.error("Materialization failed after session generation: %s", exc)

            # Create stats manually for this operation
            stats_dict = {
                "templates_processed": 1,
                "sessions_created": len(sessions),
                "date_range": {
                    "start": input.start_date.isoformat(),
                    "end": input.end_date.isoformat()
                },
                "templates_with_sessions": [
                    {
                        "template_id": input.template_id,
                        "template_name": sessions[0].name if sessions else None,
                        "sessions_created": len(sessions),
                        "date_range": f"{input.start_date} to {input.end_date}"
                    }
                ] if sessions else []
            }

            return SessionGenerationResponse(
                success=True,
                stats=convert_generation_stats(stats_dict),
                message=f"Generated {len(sessions)} sessions successfully"
            )

        except Exception as e:
            return SessionGenerationResponse(
                success=False,
                stats=None,
                message=f"Error generating sessions: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def generate_future_sessions(
        self,
        info: Info,
        input: GenerateFutureSessionsInput
    ) -> SessionGenerationResponse:
        """Generate future sessions for templates"""
        db = info.context.db

        try:
            service = SessionGeneratorService(db)
            stats = await service.generate_future_sessions(
                template_id=input.template_id,
                weeks_ahead=input.weeks_ahead,
                start_from_date=input.start_from_date
            )

            return SessionGenerationResponse(
                success=True,
                stats=convert_generation_stats(stats),
                message="Future sessions generated successfully"
            )

        except Exception as e:
            return SessionGenerationResponse(
                success=False,
                stats=None,
                message=f"Error generating future sessions: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def generate_and_materialize(
        self,
        info: Info,
        input: GenerateAndMaterializeInput
    ) -> GenerateAndMaterializeResponse:
        """Generate sessions and materialize standing bookings"""
        db = info.context.db

        try:
            service = SessionGeneratorService(db)
            result = await service.generate_and_materialize(
                template_id=input.template_id,
                weeks_ahead=input.weeks_ahead,
                auto_materialize=input.auto_materialize
            )

            return GenerateAndMaterializeResponse(
                success=True,
                generation_stats=convert_generation_stats(result["generation"]),
                materialization_stats_json=str(result.get("materialization")) if result.get("materialization") else None,
                message="Sessions generated and standing bookings materialized successfully"
            )

        except Exception as e:
            return GenerateAndMaterializeResponse(
                success=False,
                generation_stats=None,
                materialization_stats_json=None,
                message=f"Error in generation and materialization: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def maintain_weekly_schedule(
        self,
        info: Info,
        weeks_ahead: int = 8,
        cleanup_old_sessions: bool = False
    ) -> MaintenanceResponse:
        """Perform weekly schedule maintenance"""
        db = info.context.db

        try:
            service = SessionGeneratorService(db)
            stats = await service.maintain_weekly_schedule(
                weeks_ahead=weeks_ahead,
                cleanup_old_sessions=cleanup_old_sessions
            )

            return MaintenanceResponse(
                success=True,
                maintenance_stats_json=str(stats) if stats else None,
                message="Weekly schedule maintenance completed successfully"
            )

        except Exception as e:
            return MaintenanceResponse(
                success=False,
                maintenance_stats_json=None,
                message=f"Error in weekly maintenance: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def emergency_session_generation(
        self,
        info: Info,
        input: EmergencySessionGenerationInput
    ) -> SessionGenerationResponse:
        """Emergency generation of sessions for specific dates"""
        db = info.context.db

        try:
            service = SessionGeneratorService(db)
            result = await service.emergency_session_generation(
                template_id=input.template_id,
                specific_dates=input.specific_dates
            )

            # Convert result to expected format
            stats_dict = {
                "templates_processed": 1,
                "sessions_created": result["sessions_created"],
                "date_range": {
                    "start": min(input.specific_dates).isoformat() if input.specific_dates else "",
                    "end": max(input.specific_dates).isoformat() if input.specific_dates else ""
                },
                "templates_with_sessions": [
                    {
                        "template_id": input.template_id,
                        "template_name": None,
                        "sessions_created": result["sessions_created"],
                        "date_range": f"Emergency generation for {len(input.specific_dates)} dates"
                    }
                ] if result["sessions_created"] > 0 else []
            }

            return SessionGenerationResponse(
                success=True,
                stats=convert_generation_stats(stats_dict),
                message=f"Emergency generation completed: {result['sessions_created']} sessions created"
            )

        except Exception as e:
            return SessionGenerationResponse(
                success=False,
                stats=None,
                message=f"Error in emergency generation: {str(e)}"
            )
