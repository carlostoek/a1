from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class BotConfig(Base):
    __tablename__ = "bot_config"

    id = Column(Integer, primary_key=True)
    vip_channel_id = Column(String, nullable=True)
    free_channel_id = Column(String, nullable=True)
    wait_time_minutes = Column(Integer, default=0)
    vip_reactions = Column(JSON, default=dict)
    free_reactions = Column(JSON, default=dict)
    subscription_fees = Column(JSON, default=dict)


class VIPSubscriber(Base):
    __tablename__ = "vip_subscribers"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True)
    join_date = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(DateTime)
    status = Column(String(20))  # active/expired
    token_id = Column(Integer, ForeignKey("invitation_tokens.id"))

    # Index on [status, expiry_date]
    __table_args__ = (Index("idx_status_expiry", "status", "expiry_date"),)


class InvitationToken(Base):
    __tablename__ = "invitation_tokens"

    id = Column(Integer, primary_key=True)
    token = Column(String, unique=True, index=True)
    generated_by = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.utcnow)
    duration_hours = Column(Integer)
    used = Column(Boolean, default=False)
    used_by = Column(BigInteger, nullable=True)
    used_at = Column(DateTime, nullable=True)


class FreeChannelRequest(Base):
    __tablename__ = "free_channel_requests"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True)  # Index for user_id
    request_date = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)

    # Composite index on [user_id, request_date]
    __table_args__ = (Index("idx_user_request_date", "user_id", "request_date"),)