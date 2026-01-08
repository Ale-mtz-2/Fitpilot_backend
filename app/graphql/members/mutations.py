from typing import Optional
from datetime import datetime, timezone

import strawberry
from strawberry.file_uploads import Upload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.crud.membersCrud import create_member, update_member, delete_member_and_related
from app.graphql.members.types import Member, MemberResponse, DeleteMemberResponse
from app.graphql.auth.permissions import IsAuthenticated
from app.crud.authCrud import get_account_by_id
from app.security.hashing import verify_password
from app.services.image_service import ImageService
from app.models import People
from app.core.conversions import coerce_int


@strawberry.input
class CreateMemberInput:
    full_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    wa_id: Optional[str] = None


@strawberry.input
class UpdateMemberInput:
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    wa_id: Optional[str] = None


async def _build_member_response(
    db: AsyncSession,
    member_id: int,
    *,
    success_message: str,
    missing_message: str,
) -> MemberResponse:
    """Load member data and return a standardized MemberResponse."""
    from app.crud.membersCrud import get_member_by_id

    member_data = await get_member_by_id(db=db, member_id=member_id)
    if not member_data:
        return MemberResponse(
            member=None,
            message=missing_message
        )

    return MemberResponse(
        member=Member.from_data(member_data),
        message=success_message
    )


@strawberry.type
class MemberMutation:
    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def create_member(self, info, input: CreateMemberInput) -> MemberResponse:
        """Create a new member"""
        db: AsyncSession = info.context.db

        try:
            person = await create_member(
                db=db,
                full_name=input.full_name,
                email=input.email,
                phone_number=input.phone_number,
                wa_id=input.wa_id
            )

            return await _build_member_response(
                db=db,
                member_id=person.id,
                success_message="Miembro creado exitosamente",
                missing_message="Error al obtener datos del miembro creado",
            )

        except Exception as e:
            return MemberResponse(
                member=None,
                message=f"Error al crear miembro: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def update_member(self, info, member_id: int, input: UpdateMemberInput) -> MemberResponse:
        """Update member information"""
        db: AsyncSession = info.context.db

        member_id = coerce_int(member_id)
        if member_id is None:
            return MemberResponse(
                member=None,
                message="ID de miembro inválido"
            )

        try:
            # Build update dict
            update_data = {}
            if input.full_name is not None:
                update_data['full_name'] = input.full_name
            if input.email is not None:
                update_data['email'] = input.email
            if input.phone_number is not None:
                update_data['phone_number'] = input.phone_number
            if input.wa_id is not None:
                update_data['wa_id'] = input.wa_id

            person = await update_member(db=db, member_id=member_id, **update_data)

            if not person:
                return MemberResponse(
                    member=None,
                    message="Miembro no encontrado"
                )

            return await _build_member_response(
                db=db,
                member_id=person.id,
                success_message="Miembro actualizado exitosamente",
                missing_message="Error al obtener datos del miembro actualizado",
            )

        except Exception as e:
            return MemberResponse(
                member=None,
                message=f"Error al actualizar miembro: {str(e)}"
            )

    @strawberry.mutation(name="deleteMember", permission_classes=[IsAuthenticated])
    async def delete_member(self, info, member_id: int, admin_password: str) -> DeleteMemberResponse:
        """Delete a member after validating administrator password."""
        db: AsyncSession = info.context.db

        member_id = coerce_int(member_id)
        if member_id is None:
            return DeleteMemberResponse(
                success=False,
                message="ID de socio invalido"
            )

        if not admin_password:
            return DeleteMemberResponse(
                success=False,
                message="La contrasena de administrador es obligatoria"
            )

        account_id = getattr(info.context, "account_id", None)
        if not account_id:
            return DeleteMemberResponse(
                success=False,
                message="Acceso no autorizado"
            )

        account = await get_account_by_id(db=db, account_id=account_id)
        if not account or not account.person:
            return DeleteMemberResponse(
                success=False,
                message="Cuenta de administrador no encontrada"
            )

        roles = {role.role.code for role in account.person.roles if role.role}
        if "admin" not in roles:
            return DeleteMemberResponse(
                success=False,
                message="Se requiere rol de administrador"
            )

        if not verify_password(admin_password, account.password_hash):
            return DeleteMemberResponse(
                success=False,
                message="Contrasena de administrador incorrecta"
            )

        success, message = await delete_member_and_related(db=db, member_id=member_id)
        return DeleteMemberResponse(success=success, message=message)

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def upload_profile_picture(self, info, member_id: int, file: Upload) -> MemberResponse:
        """Upload or update a member's profile picture"""
        db: AsyncSession = info.context.db
        image_service = ImageService()

        member_id = coerce_int(member_id)
        if member_id is None:
            return MemberResponse(
                member=None,
                message="ID de miembro inválido"
            )

        try:
            # Read file data
            file_data = await file.read()

            # Validate image
            is_valid, error_message = image_service.validate_image(file_data, file.filename)
            if not is_valid:
                return MemberResponse(
                    member=None,
                    message=f"Archivo inválido: {error_message}"
                )

            # Get current member to check old picture
            from app.crud.membersCrud import get_member_by_id
            member_data = await get_member_by_id(db=db, member_id=member_id)
            if not member_data:
                return MemberResponse(
                    member=None,
                    message="Miembro no encontrado"
                )

            # Delete old picture if exists
            if member_data.profile_picture_path:
                image_service.delete_old_picture(member_data.profile_picture_path)

            # Process and save new image
            new_path = image_service.process_and_save_image(
                file_data=file_data,
                user_id=member_id,
                original_filename=file.filename
            )

            if not new_path:
                return MemberResponse(
                    member=None,
                    message="Error al procesar la imagen"
                )

            # Update database
            stmt = (
                update(People)
                .where(People.id == member_id)
                .values(
                    profile_picture_path=new_path,
                    profile_picture_uploaded_at=datetime.now(timezone.utc)
                )
            )
            await db.execute(stmt)
            await db.commit()

            return await _build_member_response(
                db=db,
                member_id=member_id,
                success_message="Foto de perfil actualizada exitosamente",
                missing_message="Error al obtener datos actualizados",
            )

        except Exception as e:
            await db.rollback()
            return MemberResponse(
                member=None,
                message=f"Error al cargar foto: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def delete_profile_picture(self, info, member_id: int) -> MemberResponse:
        """Delete a member's profile picture"""
        db: AsyncSession = info.context.db
        image_service = ImageService()

        member_id = coerce_int(member_id)
        if member_id is None:
            return MemberResponse(
                member=None,
                message="ID de miembro inválido"
            )

        try:
            # Get current member
            from app.crud.membersCrud import get_member_by_id
            member_data = await get_member_by_id(db=db, member_id=member_id)
            if not member_data:
                return MemberResponse(
                    member=None,
                    message="Miembro no encontrado"
                )

            # Delete picture file if exists
            if member_data.profile_picture_path:
                image_service.delete_old_picture(member_data.profile_picture_path)

            # Update database
            stmt = (
                update(People)
                .where(People.id == member_id)
                .values(
                    profile_picture_path=None,
                    profile_picture_uploaded_at=None
                )
            )
            await db.execute(stmt)
            await db.commit()

            return await _build_member_response(
                db=db,
                member_id=member_id,
                success_message="Foto de perfil eliminada exitosamente",
                missing_message="Error al obtener datos actualizados",
            )

        except Exception as e:
            await db.rollback()
            return MemberResponse(
                member=None,
                message=f"Error al eliminar foto: {str(e)}"
            )
