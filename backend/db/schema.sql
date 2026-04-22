-- AI Ad Campaign Pipeline - Database Schema
-- PostgreSQL 16+
-- 3-Track Architecture: Image+Text, Audio/Podcast, Video

BEGIN;

-- ============================================================
-- 1. users
-- ============================================================
CREATE TABLE users (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email       text NOT NULL UNIQUE,
    name        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- 2. brands
-- ============================================================
CREATE TABLE brands (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            text NOT NULL,
    logo_url        text,
    colors          jsonb NOT NULL DEFAULT '{}',
    fonts           jsonb NOT NULL DEFAULT '{}',
    reference_images text[] NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_brands_user ON brands(user_id);

COMMENT ON COLUMN brands.colors IS '{ primary, secondary, accent, background }';
COMMENT ON COLUMN brands.fonts IS '{ headline, body, cta } -- font names or asset URLs';

-- ============================================================
-- 3. campaigns
-- ============================================================
CREATE TABLE campaigns (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    brand_id            uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    name                text NOT NULL,
    objective           text,
    style               text,
    tone                text,
    product_description text,
    product_category    text,
    target_audience     text,
    reference_image_url text,
    tracks              jsonb NOT NULL DEFAULT '{
                            "image_text": true,
                            "audio_podcast": true,
                            "video": false
                        }',
    status              text NOT NULL DEFAULT 'pending'
                            CHECK (status IN (
                                'pending',
                                'strategy_running','strategy_complete',
                                'generation_pending','generation_running',
                                'completed','failed'
                            )),
    created_at          timestamptz NOT NULL DEFAULT now(),
    completed_at        timestamptz
);

CREATE INDEX idx_campaigns_brand ON campaigns(brand_id);
CREATE INDEX idx_campaigns_user ON campaigns(user_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);

-- ============================================================
-- 4. prompt_configs (Prompt Lab versioning)
-- ============================================================
CREATE TABLE prompt_configs (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id             uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    version                 int NOT NULL,
    llm_system_prompt       text NOT NULL,
    image_template          text,
    audio_script_template   text,
    video_script_template   text,
    gen_config              jsonb NOT NULL DEFAULT '{}',
    is_active               boolean NOT NULL DEFAULT true,
    created_at              timestamptz NOT NULL DEFAULT now(),
    UNIQUE (campaign_id, version)
);

-- ============================================================
-- 5. circana_data (market data injection)
-- ============================================================
CREATE TABLE circana_data (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id      uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    product_category text NOT NULL,
    market_data      jsonb NOT NULL DEFAULT '{}',
    fetched_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_circana_campaign ON circana_data(campaign_id);

-- ============================================================
-- 6. llm_responses (raw LLM audit log)
-- ============================================================
CREATE TABLE llm_responses (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id      uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    prompt_config_id uuid REFERENCES prompt_configs(id) ON DELETE SET NULL,
    stage            text NOT NULL,
    raw_request      jsonb NOT NULL DEFAULT '{}',
    raw_response     jsonb NOT NULL DEFAULT '{}',
    model            text NOT NULL,
    tokens_used      int,
    latency_ms       int,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_llm_responses_campaign ON llm_responses(campaign_id);

-- ============================================================
-- 7. campaign_strategy (LLM creative direction)
-- ============================================================
CREATE TABLE campaign_strategy (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id             uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    prompt_config_id        uuid NOT NULL REFERENCES prompt_configs(id) ON DELETE CASCADE,
    campaign_direction      text,
    audience_segments       jsonb NOT NULL DEFAULT '[]',
    platform_strategy       jsonb NOT NULL DEFAULT '{}',
    track_recommendations   jsonb NOT NULL DEFAULT '{}',
    messaging_angles        jsonb NOT NULL DEFAULT '[]',
    created_at              timestamptz NOT NULL DEFAULT now(),
    market_data_used        boolean
);

CREATE INDEX idx_campaign_strategy_campaign ON campaign_strategy(campaign_id);

-- ============================================================
-- 8. copy_variants (LLM output - 3 per campaign: AIDA, PAS, BAB)
-- ============================================================
CREATE TABLE copy_variants (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id         uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    prompt_config_id    uuid NOT NULL REFERENCES prompt_configs(id) ON DELETE CASCADE,
    framework           text NOT NULL CHECK (framework IN ('AIDA','PAS','BAB')),
    headline            text NOT NULL,
    body                text NOT NULL,
    cta                 text NOT NULL,
    hashtags            text[] NOT NULL DEFAULT '{}',
    platform_versions   jsonb NOT NULL DEFAULT '{}',
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_copy_variants_campaign ON copy_variants(campaign_id);

-- ============================================================
-- 9. scene_prompts (LLM-generated - 3 per campaign)
-- ============================================================
CREATE TABLE scene_prompts (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id         uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    prompt_config_id    uuid NOT NULL REFERENCES prompt_configs(id) ON DELETE CASCADE,
    scene_type          text NOT NULL CHECK (scene_type IN ('primary','lifestyle','mood')),
    image_prompt        text NOT NULL,
    video_script        text,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_scene_prompts_campaign ON scene_prompts(campaign_id);

-- ============================================================
-- 10. generated_images (FLUX output + quality scoring)
-- ============================================================
CREATE TABLE generated_images (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id         uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    scene_prompt_id     uuid NOT NULL REFERENCES scene_prompts(id) ON DELETE CASCADE,
    asset_url           text NOT NULL,
    seed                int NOT NULL,
    width               int NOT NULL,
    height              int NOT NULL,
    inference_steps     int NOT NULL,
    guidance_scale      float NOT NULL,
    generation_time_ms  int,
    clip_score          float,
    ocr_pass            boolean,
    ocr_text_found      text,
    safe_zone_pass      boolean,
    final_score         float,
    is_winner           boolean NOT NULL DEFAULT false,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_generated_images_campaign ON generated_images(campaign_id);
CREATE INDEX idx_generated_images_winner ON generated_images(campaign_id) WHERE is_winner;

-- ============================================================
-- 11. compositions (finished ad creatives)
-- ============================================================
CREATE TABLE compositions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    image_id        uuid NOT NULL REFERENCES generated_images(id) ON DELETE CASCADE,
    copy_variant_id uuid NOT NULL REFERENCES copy_variants(id) ON DELETE CASCADE,
    asset_url       text NOT NULL,
    ad_size         text NOT NULL CHECK (ad_size IN ('1080x1080','1080x1350','1200x628')),
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_compositions_campaign ON compositions(campaign_id);

-- ============================================================
-- 12. social_mockups (IG + LinkedIn frames)
-- ============================================================
CREATE TABLE social_mockups (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    composition_id  uuid NOT NULL REFERENCES compositions(id) ON DELETE CASCADE,
    platform        text NOT NULL CHECK (platform IN ('instagram_feed','linkedin_card')),
    asset_url       text NOT NULL,
    caption         text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_social_mockups_campaign ON social_mockups(campaign_id);

-- ============================================================
-- 13. audio_ads (Track 2: 2 clips per campaign)
-- ============================================================
CREATE TABLE audio_ads (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id      uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    prompt_config_id uuid NOT NULL REFERENCES prompt_configs(id) ON DELETE CASCADE,
    tone             text NOT NULL,
    script           text NOT NULL,
    voice            text NOT NULL DEFAULT 'af_heart',
    speed            float NOT NULL DEFAULT 1.0,
    asset_url        text,
    is_generated     boolean NOT NULL DEFAULT false,
    duration_sec     float,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_audio_ads_campaign ON audio_ads(campaign_id);

-- ============================================================
-- 14. video_ads (Track 3: future ready)
-- ============================================================
CREATE TABLE video_ads (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id        uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    scene_prompt_id    uuid NOT NULL REFERENCES scene_prompts(id) ON DELETE CASCADE,
    script             text NOT NULL,
    model_used         text,
    video_url          text,
    voiceover_url      text,
    final_url          text,
    width              int,
    height             int,
    duration_sec       float,
    generation_time_ms int,
    seed               int,
    is_generated       boolean NOT NULL DEFAULT false,
    created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_video_ads_campaign ON video_ads(campaign_id);

-- ============================================================
-- 15. pipeline_runs (execution tracking)
-- ============================================================
CREATE TABLE pipeline_runs (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id      uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    prompt_config_id uuid REFERENCES prompt_configs(id) ON DELETE SET NULL,
    stage            text NOT NULL CHECK (stage IN (
                        'strategy','copy_gen','scene_gen',
                        'image_gen','quality_gate',
                        'composition','social_mockups',
                        'audio_gen','video_gen','video_mux',
                        'finalize','export'
                    )),
    status           text NOT NULL DEFAULT 'running'
                        CHECK (status IN ('running','completed','failed','retrying','skipped')),
    celery_task_id   text,
    started_at       timestamptz NOT NULL DEFAULT now(),
    completed_at     timestamptz,
    duration_ms      int,
    error            text,
    retry_count      int NOT NULL DEFAULT 0
);

CREATE INDEX idx_pipeline_runs_campaign ON pipeline_runs(campaign_id);
CREATE INDEX idx_pipeline_runs_celery ON pipeline_runs(celery_task_id);

-- ============================================================
-- 16. gpu_metrics (Prometheus scraper writes here)
-- ============================================================
CREATE TABLE gpu_metrics (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recorded_at     timestamptz NOT NULL DEFAULT now(),
    gpu_index       int NOT NULL,
    vram_used_mb    int,
    vram_total_mb   int,
    gpu_util_pct    float,
    power_watts     float,
    temp_celsius    float,
    inference_rps   float,
    ttft_ms         float
);

CREATE INDEX idx_gpu_metrics_time ON gpu_metrics(recorded_at DESC);
CREATE INDEX idx_gpu_metrics_gpu ON gpu_metrics(gpu_index, recorded_at DESC);

-- ============================================================
-- 17. campaign_exports (ZIP download tracking)
-- ============================================================
CREATE TABLE campaign_exports (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    asset_url   text NOT NULL,
    format      text NOT NULL DEFAULT 'zip',
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_campaign_exports_campaign ON campaign_exports(campaign_id);

-- ============================================================
-- VIEW: campaign_summary (dashboard list page)
-- ============================================================
CREATE VIEW campaign_summary AS
SELECT
    c.id,
    c.name,
    c.status,
    c.tracks,
    c.created_at,
    c.completed_at,
    b.name                                                      AS brand_name,
    b.logo_url                                                  AS brand_logo,
    COUNT(DISTINCT cv.id)                                       AS copy_count,
    COUNT(DISTINCT gi.id)                                       AS image_count,
    COUNT(DISTINCT comp.id)                                     AS creative_count,
    COUNT(DISTINCT sm.id)                                       AS mockup_count,
    COUNT(DISTINCT aa.id)                                       AS audio_count,
    COUNT(DISTINCT va.id)                                       AS video_count
FROM campaigns c
JOIN brands b               ON b.id = c.brand_id
LEFT JOIN copy_variants cv  ON cv.campaign_id = c.id
LEFT JOIN generated_images gi ON gi.campaign_id = c.id
LEFT JOIN compositions comp ON comp.campaign_id = c.id
LEFT JOIN social_mockups sm ON sm.campaign_id = c.id
LEFT JOIN audio_ads aa      ON aa.campaign_id = c.id
LEFT JOIN video_ads va      ON va.campaign_id = c.id
GROUP BY c.id, c.name, c.status, c.tracks, c.created_at, c.completed_at, b.name, b.logo_url;

COMMIT;
