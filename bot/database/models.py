from typing import Optional
from sqlalchemy import Integer, BigInteger, String, DateTime, Boolean, JSON, ForeignKey, Index, Float
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from .base import Base


class BotConfig(Base):
    __tablename__ = "bot_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    vip_channel_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    free_channel_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    wait_time_minutes: Mapped[int] = mapped_column(default=0)
    vip_reactions: Mapped[dict] = mapped_column(JSON, default=dict)
    free_reactions: Mapped[dict] = mapped_column(JSON, default=dict)
    subscription_fees: Mapped[dict] = mapped_column(JSON, default=dict)


class VIPSubscriber(Base):
    __tablename__ = "vip_subscribers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    join_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    expiry_date: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20))  # active/expired
    token_id: Mapped[int] = mapped_column(Integer, ForeignKey("invitation_tokens.id"))

    # Index on [status, expiry_date]
    __table_args__ = (Index("idx_status_expiry", "status", "expiry_date"),)


class InvitationToken(Base):
    __tablename__ = "invitation_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    generated_by: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    duration_hours: Mapped[int] = mapped_column(Integer)
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class FreeChannelRequest(Base):
    __tablename__ = "free_channel_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)  # Index for user_id
    request_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Composite index on [user_id, request_date]
    __table_args__ = (Index("idx_user_request_date", "user_id", "request_date"),)