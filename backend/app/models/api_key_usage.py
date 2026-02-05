"""
API Key Usage model for tracking API call statistics.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class APIKeyUsage(Base):
    """
    Tracks individual API key usage for statistics and rate limiting.
    Each record represents a single API call.
    """

    __tablename__ = "api_key_usage"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Request details
    endpoint = Column(String(255), nullable=False)  # e.g., "/api/v1/documents"
    method = Column(String(10), nullable=False)  # GET, POST, etc.
    status_code = Column(Integer, nullable=True)  # HTTP response status

    # Resource access tracking
    template_id = Column(Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)

    # Request metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    api_key = relationship("APIKey", back_populates="usage_records")
    tenant = relationship("Tenant", back_populates="api_key_usage")
    template = relationship("Template", back_populates="api_key_usage")
    document = relationship("Document", back_populates="api_key_usage")

    # Indexes for efficient querying
    __table_args__ = (
        Index('ix_api_key_usage_key_date', 'api_key_id', 'created_at'),
        Index('ix_api_key_usage_tenant_date', 'tenant_id', 'created_at'),
    )

    def __repr__(self):
        return f"<APIKeyUsage(id={self.id}, api_key_id={self.api_key_id}, endpoint='{self.endpoint}')>"


class APIKeyDailyStats(Base):
    """
    Aggregated daily statistics for API keys.
    Pre-computed for faster dashboard queries.
    """

    __tablename__ = "api_key_daily_stats"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Date for aggregation (stored as date at midnight)
    date = Column(DateTime, nullable=False, index=True)

    # Aggregated stats
    total_requests = Column(Integer, nullable=False, default=0)
    successful_requests = Column(Integer, nullable=False, default=0)  # 2xx status codes
    failed_requests = Column(Integer, nullable=False, default=0)  # 4xx, 5xx status codes

    # Endpoint breakdown
    documents_accessed = Column(Integer, nullable=False, default=0)
    templates_accessed = Column(Integer, nullable=False, default=0)
    extractions_performed = Column(Integer, nullable=False, default=0)

    # Performance stats
    avg_response_time_ms = Column(Integer, nullable=True)
    max_response_time_ms = Column(Integer, nullable=True)

    # Quota tracking
    quota_used = Column(Integer, nullable=False, default=0)
    quota_limit = Column(Integer, nullable=False, default=1000)
    rate_limit_hits = Column(Integer, nullable=False, default=0)  # Times rate limit was exceeded

    # Relationships
    api_key = relationship("APIKey", back_populates="daily_stats")
    tenant = relationship("Tenant", back_populates="api_key_daily_stats")

    # Unique constraint for one record per key per day
    __table_args__ = (
        Index('ix_api_key_daily_stats_key_date', 'api_key_id', 'date', unique=True),
    )

    def __repr__(self):
        return f"<APIKeyDailyStats(api_key_id={self.api_key_id}, date={self.date}, requests={self.total_requests})>"
