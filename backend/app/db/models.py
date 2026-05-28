# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""


class User(Base):
    """Registered user account."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    brands: Mapped[list["Brand"]] = relationship(back_populates="user")
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="user")


class Brand(Base):
    """Brand identity with logo, colours, and fonts."""

    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text)
    colors: Mapped[dict] = mapped_column(JSONB, default=dict)
    fonts: Mapped[dict] = mapped_column(JSONB, default=dict)
    reference_images: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="brands")
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="brand")


class Campaign(Base):
    """Ad campaign linking a user, brand, and all generated assets."""

    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str | None] = mapped_column(Text)
    style: Mapped[str | None] = mapped_column(Text)
    tone: Mapped[str | None] = mapped_column(Text)
    product_description: Mapped[str | None] = mapped_column(Text)
    product_category: Mapped[str | None] = mapped_column(Text)
    target_audience: Mapped[str | None] = mapped_column(Text)
    reference_image_url: Mapped[str | None] = mapped_column(Text)
    tracks: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {
            "image_text": True,
            "audio_podcast": True,
            "video": False,
        },
    )
    status: Mapped[str] = mapped_column(
        Text, default="pending", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    user: Mapped["User"] = relationship(back_populates="campaigns")
    brand: Mapped["Brand"] = relationship(back_populates="campaigns")
    prompt_configs: Mapped[list["PromptConfig"]] = relationship(
        back_populates="campaign"
    )
    strategy: Mapped[list["CampaignStrategy"]] = relationship(
        back_populates="campaign"
    )
    copy_variants: Mapped[list["CopyVariant"]] = relationship(
        back_populates="campaign"
    )
    scene_prompts: Mapped[list["ScenePrompt"]] = relationship(
        back_populates="campaign"
    )
    generated_images: Mapped[list["GeneratedImage"]] = relationship(
        back_populates="campaign"
    )
    compositions: Mapped[list["Composition"]] = relationship(
        back_populates="campaign"
    )
    audio_ads: Mapped[list["AudioAd"]] = relationship(
        back_populates="campaign"
    )
    video_ads: Mapped[list["VideoAd"]] = relationship(
        back_populates="campaign"
    )
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship(
        back_populates="campaign"
    )
    llm_responses: Mapped[list["LLMResponse"]] = relationship(
        back_populates="campaign"
    )
    exports: Mapped[list["CampaignExport"]] = relationship(
        back_populates="campaign"
    )


class PromptConfig(Base):
    """Versioned prompt configuration for a campaign."""

    __tablename__ = "prompt_configs"
    __table_args__ = (UniqueConstraint("campaign_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    llm_system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    image_template: Mapped[str | None] = mapped_column(Text)
    audio_script_template: Mapped[str | None] = mapped_column(Text)
    video_script_template: Mapped[str | None] = mapped_column(Text)
    gen_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    campaign: Mapped["Campaign"] = relationship(
        back_populates="prompt_configs"
    )



class LLMResponse(Base):
    """Audit log entry for a single LLM API call."""

    __tablename__ = "llm_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    prompt_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_configs.id", ondelete="SET NULL"),
    )
    stage: Mapped[str] = mapped_column(Text, nullable=False)
    raw_request: Mapped[dict] = mapped_column(JSONB, default=dict)
    raw_response: Mapped[dict] = mapped_column(JSONB, default=dict)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="llm_responses")


class CampaignStrategy(Base):
    """LLM-generated strategic direction for a campaign."""

    __tablename__ = "campaign_strategy"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    prompt_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_configs.id", ondelete="CASCADE"),
    )
    campaign_direction: Mapped[str | None] = mapped_column(Text)
    audience_segments: Mapped[list] = mapped_column(JSONB, default=list)
    platform_strategy: Mapped[dict] = mapped_column(JSONB, default=dict)
    track_recommendations: Mapped[dict] = mapped_column(JSONB, default=dict)
    messaging_angles: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="strategy")


class CopyVariant(Base):
    """Single copy variant produced by the LLM (AIDA/PAS/BAB)."""

    __tablename__ = "copy_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    prompt_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_configs.id", ondelete="CASCADE"),
    )
    framework: Mapped[str] = mapped_column(Text, nullable=False)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    cta: Mapped[str] = mapped_column(Text, nullable=False)
    hashtags: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    platform_versions: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="copy_variants")


class ScenePrompt(Base):
    """Image and video prompts for one scene type."""

    __tablename__ = "scene_prompts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    prompt_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_configs.id", ondelete="CASCADE"),
    )
    scene_type: Mapped[str] = mapped_column(Text, nullable=False)
    image_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    video_script: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="scene_prompts")


class GeneratedImage(Base):
    """Raw image produced by the image generation model."""

    __tablename__ = "generated_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    scene_prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scene_prompts.id", ondelete="CASCADE"),
    )
    asset_url: Mapped[str] = mapped_column(Text, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    inference_steps: Mapped[int] = mapped_column(Integer, nullable=False)
    guidance_scale: Mapped[float] = mapped_column(Float, nullable=False)
    generation_time_ms: Mapped[int | None] = mapped_column(Integer)
    clip_score: Mapped[float | None] = mapped_column(Float)
    ocr_pass: Mapped[bool | None] = mapped_column(Boolean)
    ocr_text_found: Mapped[str | None] = mapped_column(Text)
    safe_zone_pass: Mapped[bool | None] = mapped_column(Boolean)
    final_score: Mapped[float | None] = mapped_column(Float)
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    campaign: Mapped["Campaign"] = relationship(
        back_populates="generated_images"
    )


class Composition(Base):
    """Composited ad creative (image + copy overlay)."""

    __tablename__ = "compositions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generated_images.id", ondelete="CASCADE"),
    )
    copy_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("copy_variants.id", ondelete="CASCADE"),
    )
    asset_url: Mapped[str] = mapped_column(Text, nullable=False)
    ad_size: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="compositions")


class SocialMockup(Base):
    """Platform-specific social media mockup."""

    __tablename__ = "social_mockups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    composition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compositions.id", ondelete="CASCADE"),
    )
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    asset_url: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AudioAd(Base):
    """TTS-generated audio ad with script and asset URL."""

    __tablename__ = "audio_ads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    prompt_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_configs.id", ondelete="CASCADE"),
    )
    tone: Mapped[str] = mapped_column(Text, nullable=False)
    script: Mapped[str] = mapped_column(Text, nullable=False)
    voice: Mapped[str] = mapped_column(Text, default="af_heart")
    speed: Mapped[float] = mapped_column(Float, default=1.0)
    asset_url: Mapped[str | None] = mapped_column(Text)
    is_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_sec: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="audio_ads")


class VideoAd(Base):
    """Video ad clip with optional voiceover and final mux."""

    __tablename__ = "video_ads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    scene_prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scene_prompts.id", ondelete="CASCADE"),
    )
    script: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(Text)
    voiceover_url: Mapped[str | None] = mapped_column(Text)
    final_url: Mapped[str | None] = mapped_column(Text)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_sec: Mapped[float | None] = mapped_column(Float)
    generation_time_ms: Mapped[int | None] = mapped_column(Integer)
    seed: Mapped[int | None] = mapped_column(Integer)
    is_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="video_ads")


class PipelineRun(Base):
    """Execution record for one pipeline stage."""

    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    prompt_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_configs.id", ondelete="SET NULL"),
    )
    stage: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="running")
    celery_task_id: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    campaign: Mapped["Campaign"] = relationship(back_populates="pipeline_runs")


class GpuMetric(Base):
    """Point-in-time GPU telemetry snapshot."""

    __tablename__ = "gpu_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    gpu_index: Mapped[int] = mapped_column(Integer, nullable=False)
    vram_used_mb: Mapped[int | None] = mapped_column(Integer)
    vram_total_mb: Mapped[int | None] = mapped_column(Integer)
    gpu_util_pct: Mapped[float | None] = mapped_column(Float)
    power_watts: Mapped[float | None] = mapped_column(Float)
    temp_celsius: Mapped[float | None] = mapped_column(Float)
    inference_rps: Mapped[float | None] = mapped_column(Float)
    ttft_ms: Mapped[float | None] = mapped_column(Float)


class CampaignExport(Base):
    """Completed ZIP export of campaign assets."""

    __tablename__ = "campaign_exports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    asset_url: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(Text, default="zip")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="exports")
