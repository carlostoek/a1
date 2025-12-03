import logging
from typing import Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker
from bot.database.models import GamificationProfile, Rank
from bot.services.event_bus import Events


class GamificationService:
    """
    Servicio de gamificación para gestionar puntos y rangos de usuarios.
    """
    def __init__(self, session_maker: async_sessionmaker, event_bus, notification_service):
        self.session_maker = session_maker
        self.event_bus = event_bus
        self.notification_service = notification_service
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
        channel_id = data.get('channel_id')
        emoji = data.get('emoji')

        if not user_id:
            self.logger.error("No user_id provided in reaction event")
            return

        # Otorgar puntos por reacción (10 puntos por defecto)
        points = 10

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

        except Exception as e:
            self.logger.error(f"Error adding points to user {user_id}: {e}", exc_info=True)
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
            )
            possible_ranks = result.scalars().all()

            new_rank = None
            if possible_ranks:
                new_rank = possible_ranks[0]  # El de mayor min_points que aún <= profile.points

            # Verificar si es un rango nuevo (mejor que el actual)
            if new_rank and (profile.current_rank_id != new_rank.id):
                old_rank_id = profile.current_rank_id
                profile.current_rank_id = new_rank.id

                # Aquí podemos enviar una notificación de nivel subido
                await self._notify_rank_up(profile.user_id, old_rank_id, new_rank, session)

                self.logger.info(f"User {profile.user_id} leveled up from rank {old_rank_id} to {new_rank.id}")
        except Exception as e:
            self.logger.error(f"Error checking rank up for user {profile.user_id}: {e}", exc_info=True)

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

            message = f"¡Felicidades! Has subido de rango: {old_rank_name} → {new_rank.name}"
            await self.notification_service.send_notification(user_id, message)

            self.logger.info(f"Rank up notification sent to user {user_id}")
        except Exception as e:
            self.logger.error(f"Error notifying rank up for user {user_id}: {e}", exc_info=True)