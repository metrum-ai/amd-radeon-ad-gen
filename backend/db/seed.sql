-- Copyright Advanced Micro Devices, Inc.
--
-- SPDX-License-Identifier: MIT

-- Seed data for development/demo.
--
-- How this fits together:
--   01-schema.sql  Creates every table.
--   02-seed.sql    Inserts rows below. Both run once when PostgreSQL initializes an
--                  empty data volume (docker-entrypoint-initdb.d). They are not
--                  re-run on later container restarts; your data directory keeps all
--                  DDL and data permanently.
BEGIN;

INSERT INTO users (id, email, name) VALUES
    ('00000000-0000-0000-0000-000000000001', 'demo@example.com', 'Demo User');

INSERT INTO brands (id, user_id, name, colors, fonts) VALUES
    ('00000000-0000-0000-0000-000000000010',
     '00000000-0000-0000-0000-000000000001',
     'AMD',
     '{"primary": "#ED1C24", "secondary": "#000000", "accent": "#ED1C24", "background": "#FFFFFF"}',
     '{"headline": "Trade Gothic", "body": "Helvetica Neue", "cta": "Trade Gothic"}');

COMMIT;
