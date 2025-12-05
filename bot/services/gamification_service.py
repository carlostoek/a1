from bot.utils.sexy_logger import get_logger
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
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
        self.logger = get_logger(__name__)

    def setup_listeners(self):
        """Registrar el método _on_reaction_added al evento Events.REACTION_ADDED."""
        self.event_bus.subscribe(Events.REACTION_ADDED, self._on_reaction_added)
        self.logger.event("GamificationService listeners configured")

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
            self.logger.event(f"Added {amount} points to user {user_id}. New total: {profile.points}")

        except SQLAlchemyError as e:
            self.logger.database(f"Database error adding points to user {user_id}: {e}", exc_info=True)
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

                self.logger.success(f"User {profile.user_id} leveled up from rank {old_rank_id} to {new_rank.id}")
        except SQLAlchemyError as e:
            self.logger.database(f"Database error checking rank up for user {profile.user_id}: {e}", exc_info=True)
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

                self.logger.success(f"VIP reward of {rank.reward_vip_days} days delivered to user {user_id}")
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
                        self.logger.success(f"Sent {len(media_group)} media items as album to user {user_id}")
                    except TelegramAPIError as e:
                        self.logger.api(f"Telegram API error sending media group to user {user_id}: {e}")
                    except Exception as e:
                        self.logger.error(f"Unexpected error sending media group to user {user_id}: {e}")

                # Send individual documents
                for doc in documents:
                    try:
                        if doc['media_type'] == 'document':
                            await self.bot.send_document(chat_id=user_id, document=doc['file_id'])
                        elif doc['media_type'] == 'photo':  # In case any photo wasn't sent in album
                            await self.bot.send_photo(chat_id=user_id, photo=doc['file_id'])
                        elif doc['media_type'] == 'video':  # In case any video wasn't sent in album
                            await self.bot.send_video(chat_id=user_id, video=doc['file_id'])

                        self.logger.success(f"Sent individual {doc['media_type']} to user {user_id}")
                    except TelegramAPIError as e:
                        self.logger.api(f"Telegram API error sending individual {doc['media_type']} to user {user_id}: {e}")
                    except Exception as e:
                        self.logger.error(f"Unexpected error sending individual {doc['media_type']} to user {user_id}: {e}")

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

                self.logger.success(f"Content pack '{pack_name}' delivered to user {user_id}")

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

            self.logger.success(f"Rank up notification sent to user {user_id}")
        except SQLAlchemyError as e:
            self.logger.database(f"Database error notifying rank up for user {user_id}: {e}", exc_info=True)
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
                self.logger.event(f"Content pack with name '{name}' already exists")
                return None

            # Create new content pack
            pack = RewardContentPack(name=name)
            session.add(pack)
            await session.commit()

            # Refresh the pack to get the generated ID
            await session.refresh(pack)

            self.logger.success(f"Created content pack: {name} (ID: {pack.id})")
            return pack

        except SQLAlchemyError as e:
            self.logger.database(f"Database error creating content pack '{name}': {e}", exc_info=True)
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

            self.logger.success(f"Added file to pack {pack_id}: {media_type} (ID: {unique_id})")
            return True

        except SQLAlchemyError as e:
            self.logger.database(f"Database error adding file to pack {pack_id}: {e}", exc_info=True)
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

            self.logger.database(f"Retrieved {len(packs)} content packs")
            return packs

        except SQLAlchemyError as e:
            self.logger.database(f"Database error retrieving content packs: {e}", exc_info=True)
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
            # Get the pack to delete (this will trigger cascade deletion of files if properly configured)
            pack_result = await session.execute(
                select(RewardContentPack).where(RewardContentPack.id == pack_id)
            )
            pack = pack_result.scalar_one_or_none()

            if pack:
                # Use ORM to delete, which will handle cascade deletion if properly configured in the model
                await session.delete(pack)
                await session.commit()

                self.logger.success(f"Deleted content pack: {pack_id}")
                return True
            else:
                self.logger.event(f"Attempted to delete non-existent content pack: {pack_id}")
                return False

        except SQLAlchemyError as e:
            self.logger.database(f"Database error deleting content pack {pack_id}: {e}", exc_info=True)
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

            self.logger.database(f"Retrieved {len(ranks)} ranks")
            return ranks

        except SQLAlchemyError as e:
            self.logger.database(f"Database error retrieving ranks: {e}", exc_info=True)
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
                self.logger.event(f"Attempted to update non-existent rank: {rank_id}")
                return None

            # Update the fields if provided
            if vip_days is not None:
                rank.reward_vip_days = vip_days

            if pack_id is not None:
                rank.reward_content_pack_id = pack_id

            await session.commit()
            await session.refresh(rank)  # Refresh to get the updated values

            self.logger.success(f"Updated rank {rank_id} rewards: VIP days={vip_days}, Pack ID={pack_id}")
            return rank

        except SQLAlchemyError as e:
            self.logger.database(f"Database error updating rank {rank_id} rewards: {e}", exc_info=True)
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
                self.logger.database(f"Retrieved rank {rank_id}: {rank.name}")
            else:
                self.logger.event(f"Attempted to retrieve non-existent rank: {rank_id}")

            return rank

        except SQLAlchemyError as e:
            self.logger.database(f"Database error retrieving rank {rank_id}: {e}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving rank {rank_id}: {e}", exc_info=True)
            return None

    async def claim_daily_reward(self, user_id: int, session) -> Dict[str, Any]:
        """
        Claim daily reward for the user, with 24-hour cooldown.

        Args:
            user_id: ID of the user claiming the reward
            session: Async database session

        Returns:
            Dictionary with success status and relevant data
        """
        try:
            # Get user profile (create if doesn't exist)
            result = await session.execute(
                select(GamificationProfile).where(GamificationProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                # Create new profile if it doesn't exist
                rank_result = await session.execute(
                    select(Rank).where(Rank.min_points == 0)
                )
                starting_rank = rank_result.scalar_one_or_none()

                profile = GamificationProfile(
                    user_id=user_id,
                    points=0,
                    current_rank_id=starting_rank.id if starting_rank else None
                )
                session.add(profile)
                await session.commit()
                await session.refresh(profile)

            # Check if user can claim daily reward
            now = datetime.now(timezone.utc)
            daily_points = 50  # Fixed daily reward points

            if profile.last_daily_claim is not None:
                # Handle potential mismatch between offset-aware and offset-naive datetimes
                last_claim = profile.last_daily_claim
                if last_claim.tzinfo is None:
                    # Convert to offset-aware datetime in UTC
                    last_claim = last_claim.replace(tzinfo=timezone.utc)

                # Calculate time elapsed since last claim
                time_since_last_claim = now - last_claim

                # Check if it's been less than 24 hours
                if time_since_last_claim.total_seconds() < 24 * 3600:  # 24 hours in seconds
                    # Calculate remaining time
                    remaining_seconds = int((24 * 3600) - time_since_last_claim.total_seconds())
                    hours = remaining_seconds // 3600
                    minutes = (remaining_seconds % 3600) // 60
                    seconds = remaining_seconds % 60

                    remaining_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    return {
                        'success': False,
                        'remaining': remaining_time
                    }

            # Update points and last claim time
            await self.add_points(user_id, daily_points, session)

            # Refresh profile after adding points
            result = await session.execute(
                select(GamificationProfile).where(GamificationProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()

            profile.last_daily_claim = now
            await session.commit()

            return {
                'success': True,
                'points': daily_points,
                'total': profile.points
            }

        except SQLAlchemyError as e:
            self.logger.database(f"Database error claiming daily reward for user {user_id}: {e}", exc_info=True)
            await session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            self.logger.error(f"Unexpected error claiming daily reward for user {user_id}: {e}", exc_info=True)
            await session.rollback()
            return {
                'success': False,
                'error': str(e)
            }

    async def get_referral_link(self, user_id: int, bot_username: str) -> str:
        """
        Generate a referral link for the user.

        Args:
            user_id: ID of the user requesting the referral link
            bot_username: Username of the bot (without @)

        Returns:
            The referral link as a string
        """
        return f"https://t.me/{bot_username}?start=ref_{user_id}"

    async def process_referral(self, new_user_id: int, ref_payload: str, session) -> bool:
        """
        Process a referral when a new user joins using a referral link.

        Args:
            new_user_id: ID of the new user
            ref_payload: The referral payload (e.g., "ref_12345")
            session: Database session

        Returns:
            True if referral was processed successfully, False otherwise
        """
        try:
            # Extract the referrer ID from the payload
            if not ref_payload.startswith("ref_"):
                self.logger.event(f"Invalid referral payload format: {ref_payload}")
                return False

            try:
                referrer_id = int(ref_payload[4:])  # Extract the number after "ref_"
            except ValueError:
                self.logger.event(f"Invalid referral payload format (non-numeric ID): {ref_payload}")
                return False

            # Check if the new user already has a gamification profile (must be truly new)
            result = await session.execute(
                select(GamificationProfile).where(GamificationProfile.user_id == new_user_id)
            )
            existing_profile = result.scalar_one_or_none()

            if existing_profile:
                self.logger.event(f"User {new_user_id} already has a gamification profile, referral ignored")
                return False

            # Check that referrer and referee are not the same person (anti-loop)
            if new_user_id == referrer_id:
                self.logger.event(f"User {new_user_id} tried to refer themselves, preventing referral loop")
                return False

            # Check if the referrer exists in the database
            result = await session.execute(
                select(GamificationProfile).where(GamificationProfile.user_id == referrer_id)
            )
            referrer_profile = result.scalar_one_or_none()

            if not referrer_profile:
                self.logger.event(f"Referrer {referrer_id} does not exist in database")
                return False

            # Create a new gamification profile for the new user with the referral info
            rank_result = await session.execute(
                select(Rank).where(Rank.min_points == 0)
            )
            starting_rank = rank_result.scalar_one_or_none()

            new_profile = GamificationProfile(
                user_id=new_user_id,
                points=0,
                current_rank_id=starting_rank.id if starting_rank else None,
                referred_by_id=referrer_id,  # Set who referred this user
                referrals_count=0  # New users start with 0 referrals
            )
            session.add(new_profile)

            # Update referrer's profile: add points and increment referral count
            referrer_profile.referrals_count += 1
            await self.add_points(referrer_id, 100, session)  # Reward referrer with 100 points

            # Add points to the new user (50 points as incentive)
            await self.add_points(new_user_id, 50, session)  # Reward new user with 50 points

            # Commit the changes
            await session.commit()

            # Send notifications
            try:
                # Notify referrer about the new referral
                await self.notification_service.send_notification(
                    referrer_id,
                    "referral_success",
                    context_data={
                        "points": 100
                    }
                )
                self.logger.success(f"Referral notification sent to referrer {referrer_id}")
            except Exception as e:
                self.logger.error(f"Error sending referral notification to referrer {referrer_id}: {e}")

            try:
                # Notify the new user about their bonus
                await self.notification_service.send_notification(
                    new_user_id,
                    "referral_bonus",
                    context_data={
                        "points": 50
                    }
                )
                self.logger.success(f"Referral bonus notification sent to new user {new_user_id}")
            except Exception as e:
                self.logger.error(f"Error sending referral bonus notification to user {new_user_id}: {e}")

            self.logger.success(f"Successfully processed referral: {referrer_id} -> {new_user_id}")
            return True

        except SQLAlchemyError as e:
            self.logger.database(f"Database error processing referral for user {new_user_id}: {e}", exc_info=True)
            await session.rollback()
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error processing referral for user {new_user_id}: {e}", exc_info=True)
            await session.rollback()
            return False