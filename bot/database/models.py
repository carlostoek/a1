from typing import Optional
from sqlalchemy import Integer, BigInteger, String, DateTime, Boolean, JSON, ForeignKey, Index, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from .base import Base


class BotConfig(Base):
    __tablename__ = "bot_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    vip_channel_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    free_channel_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    wait_time_minutes: Mapped[int] = mapped_column(default=0)
    vip_reactions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    free_reactions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    subscription_fees: Mapped[dict] = mapped_column(JSON, default=dict)
    vip_content_protection: Mapped[bool] = mapped_column(default=False)
    free_content_protection: Mapped[bool] = mapped_column(default=False)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default="free", index=True)  # 'free', 'vip', 'admin'
    join_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/expired
    token_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("invitation_tokens.id"), nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Index on [status, expiry_date]
    __table_args__ = (Index("idx_status_expiry", "status", "expiry_date"),)


class InvitationToken(Base):
    __tablename__ = "invitation_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    generated_by: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    tier_id: Mapped[int] = mapped_column(Integer, ForeignKey("subscription_tiers.id"))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class SubscriptionTier(Base):
    __tablename__ = "subscription_tiers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True) # Nombre de la tarifa (ej: 1 Mes PRO)
    duration_days: Mapped[int] = mapped_column(Integer) # Duración en días
    price_usd: Mapped[float] = mapped_column(Float) # Precio
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class FreeChannelRequest(Base):
    __tablename__ = "free_channel_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)  # Index for user_id
    request_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Composite index on [user_id, request_date]
    __table_args__ = (Index("idx_user_request_date", "user_id", "request_date"),)


# Update the existing Rank class to add reward fields (modifying the original class)
class Rank(Base):
    __tablename__ = "gamification_ranks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)  # Ej: "Novato", "Veterano"
    min_points: Mapped[int] = mapped_column(Integer, unique=True)  # Puntos para alcanzarlo
    reward_description: Mapped[str] = mapped_column(String(200), nullable=True)  # Texto descriptivo de recompensa

    # Nuevos campos para recompensas (añadidos según la especificación)
    # Recompensa 1: Días VIP
    reward_vip_days: Mapped[int] = mapped_column(Integer, default=0)
    # Recompensa 2: Pack de Contenido
    reward_content_pack_id: Mapped[Optional[int]] = mapped_column(ForeignKey("reward_content_packs.id"), nullable=True)

    # Índices para búsquedas rápidas al calcular nivel
    __table_args__ = (
        Index('idx_rank_points', 'min_points'),
    )


class RewardContentPack(Base):
    __tablename__ = "reward_content_packs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)  # Ej: "Pack de Bienvenida", "Set Exclusivo Octubre"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relación inversa (para saber qué archivos tiene)
    # files = relationship("RewardContentFile", back_populates="pack", cascade="all, delete-orphan")


class RewardContentFile(Base):
    __tablename__ = "reward_content_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    pack_id: Mapped[int] = mapped_column(ForeignKey("reward_content_packs.id"))

    file_id: Mapped[str] = mapped_column(String(255))  # El ID para enviar el archivo
    file_unique_id: Mapped[str] = mapped_column(String(255))  # Para evitar duplicados
    media_type: Mapped[str] = mapped_column(String(20))  # 'photo', 'video', 'document'

    # pack = relationship("RewardContentPack", back_populates="files")


class GamificationProfile(Base):
    __tablename__ = "gamification_profiles"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # FK lógica a Telegram ID
    points: Mapped[int] = mapped_column(Integer, default=0)
    current_rank_id: Mapped[Optional[int]] = mapped_column(ForeignKey("gamification_ranks.id"), nullable=True)

    # Metadatos de actividad
    last_interaction_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relación (Opcional, si usas ORM loading, sino solo el ID está bien)
    # rank = relationship("Rank")