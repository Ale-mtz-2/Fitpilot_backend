from typing import List, Optional
from datetime import datetime, timedelta
import strawberry
from app.graphql.context import Context
from app.graphql.leads.types import (
    Lead, LeadSource, LeadStats, LeadsPageResponse, FormSubmission,
    CommunicationOptIn, WhatsAppThread, LeadFilters, LeadPagination
)


@strawberry.type
class LeadsQuery:
    """GraphQL queries for lead management"""

    @strawberry.field
    async def leads(
        self,
        info: strawberry.Info[Context],
        filters: Optional[LeadFilters] = None,
        pagination: Optional[LeadPagination] = None
    ) -> LeadsPageResponse:
        """Get paginated leads with filtering"""
        # TODO: Implement leads pagination query
        # This would integrate with a new leadsCrud module
        return LeadsPageResponse(
            leads=[],
            total=0,
            page=1,
            per_page=20,
            total_pages=0
        )

    @strawberry.field
    async def lead(self, info: strawberry.Info[Context], lead_id: int) -> Optional[Lead]:
        """Get a specific lead by ID"""
        # TODO: Implement single lead query
        return None

    @strawberry.field
    async def lead_sources(self, info: strawberry.Info[Context]) -> List[LeadSource]:
        """Get all available lead sources"""
        # TODO: Implement lead sources query
        return []

    @strawberry.field
    async def lead_stats(
        self,
        info: strawberry.Info[Context],
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> LeadStats:
        """Get lead funnel statistics"""
        if not date_from:
            date_from = datetime.now() - timedelta(days=30)
        if not date_to:
            date_to = datetime.now()

        # TODO: Implement lead statistics calculation
        return LeadStats(
            total_leads=0,
            new_leads=0,
            contacted_leads=0,
            qualified_leads=0,
            converted_leads=0,
            lost_leads=0,
            conversion_rate=0.0,
            by_source=[]
        )

    @strawberry.field
    async def leads_by_person(
        self,
        info: strawberry.Info[Context],
        person_id: int
    ) -> List[Lead]:
        """Get all leads for a specific person"""
        # TODO: Implement leads by person query
        return []

    @strawberry.field
    async def form_submissions(
        self,
        info: strawberry.Info[Context],
        person_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[FormSubmission]:
        """Get form submissions with optional filtering"""
        # TODO: Implement form submissions query
        return []

    @strawberry.field
    async def communication_opt_ins(
        self,
        info: strawberry.Info[Context],
        person_id: int
    ) -> List[CommunicationOptIn]:
        """Get communication opt-ins for a person"""
        # TODO: Implement opt-ins query
        return []

    @strawberry.field
    async def whatsapp_thread(
        self,
        info: strawberry.Info[Context],
        person_id: int
    ) -> Optional[WhatsAppThread]:
        """Get WhatsApp thread for a person"""
        # TODO: Implement WhatsApp thread query
        return None

    @strawberry.field
    async def recent_leads(
        self,
        info: strawberry.Info[Context],
        limit: int = 10
    ) -> List[Lead]:
        """Get recent leads for dashboard"""
        # TODO: Implement recent leads query
        return []

    @strawberry.field
    async def leads_needing_followup(
        self,
        info: strawberry.Info[Context],
        days_since_contact: int = 3
    ) -> List[Lead]:
        """Get leads that need follow-up attention"""
        # TODO: Implement leads needing follow-up query
        return []