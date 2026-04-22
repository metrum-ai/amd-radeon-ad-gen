-- Seed data for development/demo.
--
-- How this fits together:
--   01-schema.sql  Creates every table (including campaign_strategy.market_data_used).
--   02-seed.sql    Inserts rows below. Both run once when PostgreSQL initializes an
--                  empty data volume (docker-entrypoint-initdb.d). They are not
--                  re-run on later container restarts; your data directory keeps all
--                  DDL and data permanently.
--
--   If you have an older database volume created before market_data_used existed,
--   run once (outside init): ALTER TABLE campaign_strategy ADD COLUMN IF NOT EXISTS
--   market_data_used boolean;
--
-- This idempotent line keeps a fresh init consistent even if 01-schema were ever
-- replaced by an older dump missing the column (then the column is still added).
BEGIN;

ALTER TABLE campaign_strategy
    ADD COLUMN IF NOT EXISTS market_data_used boolean;

INSERT INTO users (id, email, name) VALUES
    ('00000000-0000-0000-0000-000000000001', 'demo@metrum.ai', 'Demo User');

INSERT INTO brands (id, user_id, name, colors, fonts) VALUES
    ('00000000-0000-0000-0000-000000000010',
     '00000000-0000-0000-0000-000000000001',
     'AMD',
     '{"primary": "#ED1C24", "secondary": "#000000", "accent": "#ED1C24", "background": "#FFFFFF"}',
     '{"headline": "Trade Gothic", "body": "Helvetica Neue", "cta": "Trade Gothic"}');

COMMIT;
