import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from aiogram import Bot
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from aiogram.types import InputMediaPhoto, InputMediaVideo
from bot.database.models import GamificationProfile, Rank, RewardContentPack, RewardContentFile
from bot.services.event_bus import Events
from bot.services.subscription_service import SubscriptionService


class GamificationService:
    """
    Servicio de gamificación para gestionar puntos y rangos de usuarios.
    """
    # Constants
    POINTS_PER_REACTION = 10

    def __init__(self, session_maker: async_sessionmaker, event_bus: 'EventBus', notification_service: 'NotificationService', subscription_service: 'SubscriptionService', bot: 'Bot'):
        self.session_maker = session_maker
        self.event_bus = event_bus
        self.notification_service = notification_service
        self.subscription_service = subscription_service
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    def setup_listeners(self):
        """Registrar el método _on_reaction_added al evento Events.REACTION_ADDED."""
        self.event_bus.subscribe(Events.REACTION_ADDED, self._on_reaction_added)
        self.logger.info("GamificationService listeners configured")

    async def _on_reaction_added(self, event_name: str, data: Dict[str, Any]):
        """
        Manejar el evento de reacción añadida.

        Input: data contiene {'user_id': int, 'channel_id': int, 'emoji': str}.
        """
        user_id = data.get('user_id')
        # channel_id = data.get('channel_id')  # Unused variable
        # emoji = data.get('emoji')  # Unused variable

        if not user_id:
            self.logger.error("No user_id provided in reaction event")
            return

        # Otorgar puntos por reacción
        points = self.POINTS_PER_REACTION

        # Abrir una nueva sesión para esta operación
        async with self.session_maker() as session:
            await self.add_points(user_id, points, session)

    async def add_points(self, user_id: int, amount: int, session):
        """
        Lógica principal para añadir puntos a un usuario y verificar cambios de rango.
        """
        try:
            # Buscar el perfil de gamificación del usuario
            result = await session.execute(
                select(GamificationProfile).where(GamificationProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()

            if profile:
                # Actualizar puntos existentes
                profile.points += amount
            else:
                # Crear nuevo perfil con 0 puntos y rango de 0 puntos
                # Buscar el rango con min_points = 0 (Bronce)
                rank_result = await session.execute(
                    select(Rank).where(Rank.min_points == 0)
                )
                starting_rank = rank_result.scalar_one_or_none()

                profile = GamificationProfile(
                    user_id=user_id,
                    points=amount,
                    current_rank_id=starting_rank.id if starting_rank else None
                )
                session.add(profile)

            # Actualizar última interacción
            profile.last_interaction_at = func.now()

            # Verificar si subió de rango
            await self._check_rank_up(profile, session)

            # Guardar cambios
            await session.commit()
            self.logger.info(f"Added {amount} points to user {user_id}. New total: {profile.points}")

        except SQLAlchemyError as e:
            self.logger.error(f"Database error adding points to user {user_id}: {e}", exc_info=True)
            await session.rollback()
        except Exception as e:
            self.logger.error(f"Unexpected error adding points to user {user_id}: {e}", exc_info=True)
            await session.rollback()

    async def _check_rank_up(self, profile: GamificationProfile, session):
        """
        Verificar si el usuario subió de rango y actualizar si es necesario.
        """
        try:
            # Buscar el rango con el mayor min_points que sea <= a los puntos del usuario
            # Ordenados descendentemente para obtener el más alto que cumpla la condición
            result = await session.execute(
                select(Rank)
                .where(Rank.min_points <= profile.points)
                .order_by(Rank.min_points.desc())
                .limit(1)  # Only get the first result
            )
            new_rank = result.scalar_one_or_none()

            # Verificar si es un rango nuevo (mejor que el actual)
            if new_rank and (profile.current_rank_id != new_rank.id):
                old_rank_id = profile.current_rank_id
                profile.current_rank_id = new_rank.id

                # Aquí podemos enviar una notificación de nivel subido
                await self._notify_rank_up(profile.user_id, old_rank_id, new_rank, session)

                # Entregar las recompensas configuradas para este nuevo rango
                await self._deliver_rewards(profile.user_id, new_rank, session)

                self.logger.info(f"User {profile.user_id} leveled up from rank {old_rank_id} to {new_rank.id}")
        except SQLAlchemyError as e:
            self.logger.error(f"Database error checking rank up for user {profile.user_id}: {e}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Unexpected error checking rank up for user {profile.user_id}: {e}", exc_info=True)

    async def _deliver_rewards(self, user_id: int, rank: Rank, session):
        """
        Deliver rewards configured for a rank to the user.

        Args:
            user_id: ID of the user who leveled up
            rank: Rank object containing reward configuration
            session: Database session
        """
        # A. Entrega VIP (rank.reward_vip_days > 0)
        if rank.reward_vip_days and rank.reward_vip_days > 0:
            # Add VIP days to user's subscription
            result = await self.subscription_service.add_vip_days(
                user_id=user_id,
                days=rank.reward_vip_days,
                session=session
            )

            if result["success"]:
                # Get formatted date for notification
                expiry_date_str = result["new_expiry_date"].strftime("%d/%m/%Y")

                # Send notification using the notification service
                await self.notification_service.send_notification(
                    user_id,
                    "vip_reward",
                    context_data={
                        "days": rank.reward_vip_days,
                        "date": expiry_date_str
                    }
                )

                self.logger.info(f"VIP reward of {rank.reward_vip_days} days delivered to user {user_id}")
            else:
                self.logger.error(f"Failed to deliver VIP reward to user {user_id}: {result.get('error', 'Unknown error')}")

        # B. Entrega de Pack (rank.reward_content_pack_id is not None)
        if rank.reward_content_pack_id:
            # Get all files associated with the pack
            result = await session.execute(
                select(RewardContentFile).where(
                    RewardContentFile.pack_id == rank.reward_content_pack_id
                )
            )
            content_files = result.scalars().all()

            if content_files:
                # Classify media files
                album_media = []
                documents = []

                for content_file in content_files:
                    file_obj = {
                        'file_id': content_file.file_id,
                        'media_type': content_file.media_type
                    }

                    if content_file.media_type in ['photo', 'video']:
                        album_media.append(file_obj)
                    else:
                        # Treat documents, audio, etc. as individual files
                        documents.append(file_obj)

                # Send album media (photos and videos) using send_media_group
                if album_media:
                    media_group = []
                    for media_item in album_media:
                        if media_item['media_type'] == 'photo':
                            media_group.append(InputMediaPhoto(media=media_item['file_id']))
                        elif media_item['media_type'] == 'video':
                            media_group.append(InputMediaVideo(media=media_item['file_id']))

                    try:
                        await self.bot.send_media_group(chat_id=user_id, media=media_group)
                        self.logger.info(f"Sent {len(media_group)} media items as album to user {user_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to send media group to user {user_id}: {e}")

                # Send individual documents
                for doc in documents:
                    try:
                        if doc['media_type'] == 'document':
                            await self.bot.send_document(chat_id=user_id, document=doc['file_id'])
                        elif doc['media_type'] == 'photo':  # In case any photo wasn't sent in album
                            await self.bot.send_photo(chat_id=user_id, photo=doc['file_id'])
                        elif doc['media_type'] == 'video':  # In case any video wasn't sent in album
                            await self.bot.send_video(chat_id=user_id, video=doc['file_id'])

                        self.logger.info(f"Sent individual {doc['media_type']} to user {user_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to send individual {doc['media_type']} to user {user_id}: {e}")

                # Get pack name for notification
                pack_result = await session.execute(
                    select(RewardContentPack).where(
                        RewardContentPack.id == rank.reward_content_pack_id
                    )
                )
                pack = pack_result.scalar_one_or_none()
                pack_name = pack.name if pack else "Pack Desconocido"

                # Send notification about the pack reward
                await self.notification_service.send_notification(
                    user_id,
                    "pack_reward",
                    context_data={
                        "pack_name": pack_name,
                        "rank_name": rank.name
                    }
                )

                self.logger.info(f"Content pack '{pack_name}' delivered to user {user_id}")

    async def _notify_rank_up(self, user_id: int, old_rank_id: int, new_rank: Rank, session):
        """
        Enviar notificación al usuario cuando sube de rango.
        """
        try:
            # Buscar el nombre del rango anterior para la notificación
            old_rank_name = "Unknown"
            if old_rank_id is not None:
                old_rank_result = await session.execute(
                    select(Rank).where(Rank.id == old_rank_id)
                )
                old_rank = old_rank_result.scalar_one_or_none()
                if old_rank:
                    old_rank_name = old_rank.name

            await self.notification_service.send_notification(
                user_id,
                "rank_up",
                context_data={
                    "old_rank": old_rank_name,
                    "new_rank": new_rank.name
                }
            )

            self.logger.info(f"Rank up notification sent to user {user_id}")
        except SQLAlchemyError as e:
            self.logger.error(f"Database error notifying rank up for user {user_id}: {e}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Unexpected error notifying rank up for user {user_id}: {e}", exc_info=True)

    async def create_content_pack(self, name: str, session) -> Optional[RewardContentPack]:
        """
        Creates a new content pack with the given name.

        Args:
            name: Unique name for the content pack
            session: Async database session

        Returns:
            The created RewardContentPack instance or None if name already exists
        """
        try:
            # Check if a pack with this name already exists
            result = await session.execute(
                select(RewardContentPack).where(RewardContentPack.name == name)
            )
            existing_pack = result.scalar_one_or_none()

            if existing_pack:
                self.logger.warning(f"Content pack with name '{name}' already exists")
                return None

            # Create new content pack
            pack = RewardContentPack(name=name)
            session.add(pack)
            await session.commit()

            # Refresh the pack to get the generated ID
            await session.refresh(pack)

            self.logger.info(f"Created content pack: {name} (ID: {pack.id})")
            return pack

        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating content pack '{name}': {e}", exc_info=True)
            await session.rollback()
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error creating content pack '{name}': {e}", exc_info=True)
            await session.rollback()
            return None

    async def add_file_to_pack(self, pack_id: int, file_id: str, unique_id: str, media_type: str, session):
        """
        Adds a media file to an existing content pack.

        Args:
            pack_id: ID of the content pack to add the file to
            file_id: Telegram file_id
            unique_id: Telegram unique identifier for the file
            media_type: Type of media ('photo', 'video', 'document')
            session: Async database session

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create new content file
            content_file = RewardContentFile(
                pack_id=pack_id,
                file_id=file_id,
                file_unique_id=unique_id,
                media_type=media_type
            )
            session.add(content_file)
            await session.commit()

            self.logger.info(f"Added file to pack {pack_id}: {media_type} (ID: {unique_id})")
            return True

        except SQLAlchemyError as e:
            self.logger.error(f"Database error adding file to pack {pack_id}: {e}", exc_info=True)
            await session.rollback()
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error adding file to pack {pack_id}: {e}", exc_info=True)
            await session.rollback()
            return False

    async def get_all_content_packs(self, session) -> List[RewardContentPack]:
        """
        Retrieves all content packs from the database.

        Args:
            session: Async database session

        Returns:
            List of RewardContentPack instances
        """
        try:
            result = await session.execute(
                select(RewardContentPack).order_by(RewardContentPack.name)
            )
            packs = result.scalars().all()

            self.logger.info(f"Retrieved {len(packs)} content packs")
            return packs

        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving content packs: {e}", exc_info=True)
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving content packs: {e}", exc_info=True)
            return []

    async def delete_content_pack(self, pack_id: int, session):
        """
        Deletes a content pack and all its associated files.

        Args:
            pack_id: ID of the content pack to delete
            session: Async database session

        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete all files associated with the pack first
            await session.execute(
                select(RewardContentFile).where(RewardContentFile.pack_id == pack_id)
            )
            # SQLAlchemy should handle the foreign key constraint with cascade delete if configured,
            # but we handle it explicitly for safety
            await session.execute(
                "DELETE FROM reward_content_files WHERE pack_id = :pack_id",
                {"pack_id": pack_id}
            )

            # Delete the pack itself
            pack_result = await session.execute(
                "DELETE FROM reward_content_packs WHERE id = :pack_id",
                {"pack_id": pack_id}
            )

            await session.commit()

            # Check if any pack was deleted
            if pack_result.rowcount > 0:
                self.logger.info(f"Deleted content pack: {pack_id}")
                return True
            else:
                self.logger.warning(f"Attempted to delete non-existent content pack: {pack_id}")
                return False

        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting content pack {pack_id}: {e}", exc_info=True)
            await session.rollback()
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error deleting content pack {pack_id}: {e}", exc_info=True)
            await session.rollback()
            return False

    async def get_all_ranks(self, session) -> List[Rank]:
        """
        Retrieves all ranks from the database ordered by points.

        Args:
            session: Async database session

        Returns:
            List of Rank instances ordered by min_points
        """
        try:
            result = await session.execute(
                select(Rank).order_by(Rank.min_points)
            )
            ranks = result.scalars().all()

            self.logger.info(f"Retrieved {len(ranks)} ranks")
            return ranks

        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving ranks: {e}", exc_info=True)
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving ranks: {e}", exc_info=True)
            return []

    async def update_rank_rewards(self, rank_id: int, session, vip_days: int = None, pack_id: int = None) -> Optional[Rank]:
        """
        Updates the reward configuration for a specific rank.

        Args:
            rank_id: ID of the rank to update
            vip_days: New VIP days reward (if provided)
            pack_id: New content pack ID (if provided, None to remove)
            session: Async database session

        Returns:
            Updated Rank instance or None if rank not found
        """
        try:
            # Get the rank
            result = await session.execute(
                select(Rank).where(Rank.id == rank_id)
            )
            rank = result.scalar_one_or_none()

            if not rank:
                self.logger.warning(f"Attempted to update non-existent rank: {rank_id}")
                return None

            # Update the fields if provided
            if vip_days is not None:
                rank.reward_vip_days = vip_days

            if pack_id is not None:
                rank.reward_content_pack_id = pack_id

            await session.commit()
            await session.refresh(rank)  # Refresh to get the updated values

            self.logger.info(f"Updated rank {rank_id} rewards: VIP days={vip_days}, Pack ID={pack_id}")
            return rank

        except SQLAlchemyError as e:
            self.logger.error(f"Database error updating rank {rank_id} rewards: {e}", exc_info=True)
            await session.rollback()
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error updating rank {rank_id} rewards: {e}", exc_info=True)
            await session.rollback()
            return None

    async def get_rank_by_id(self, rank_id: int, session) -> Optional[Rank]:
        """
        Retrieves a specific rank by its ID.

        Args:
            rank_id: ID of the rank to retrieve
            session: Async database session

        Returns:
            Rank instance or None if not found
        """
        try:
            result = await session.execute(
                select(Rank).where(Rank.id == rank_id)
            )
            rank = result.scalar_one_or_none()

            if rank:
                self.logger.info(f"Retrieved rank {rank_id}: {rank.name}")
            else:
                self.logger.warning(f"Attempted to retrieve non-existent rank: {rank_id}")

            return rank

        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving rank {rank_id}: {e}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving rank {rank_id}: {e}", exc_info=True)
            return None