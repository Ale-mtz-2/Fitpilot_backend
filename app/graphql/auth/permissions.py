import strawberry
from strawberry.types import Info
from strawberry.permission import BasePermission
# from app.graphql.schema import Context

class IsAuthenticated(BasePermission):
    message = "Autheintication required."

    def has_permission(self, source, info: Info, **kwargs):
        return bool(info.context.user) 
