-- Deterministic demo fixture for pulse-data. Fixed UUIDs, fixed dates
-- (2026-09-21..23), hand-computable numbers. Reviewable rows, no secrets.
-- Load into a scratch DB (see README), never production.

-- 1 user (bcrypt of Demo1234!; used by run.py cross-check login).
-- Documented throwaway for the scratch DB only.
INSERT INTO users (id, email, password_hash, name) VALUES
  ('11111111-1111-1111-1111-111111111111', 'demo@pulse.local', '$2a$10$Xex62aLiCJ11M7w.Zv29hulAQOSNwPy2TOo2DmWt.f6HPCqWe35YO', 'Demo')
ON CONFLICT (id) DO NOTHING;

-- 3 monitors, interval 300s
INSERT INTO monitors (id, user_id, name, url, method, interval_seconds, timeout_seconds,
  failure_threshold, recovery_threshold, status, is_active) VALUES
  ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111',
   'web-api', 'https://web.example.com/health', 'GET', 300, 5, 3, 2, 'UP', TRUE),
  ('33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111',
   'pay-api', 'https://pay.example.com/health', 'GET', 300, 5, 3, 2, 'DOWN', TRUE),
  ('44444444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111',
   'legacy-svc', 'https://legacy.example.com/health', 'GET', 300, 5, 3, 2, 'DOWN', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Checks: every 5 min per monitor per day (288/day x 3 days = 864 each).
-- web-api: all UP, latency 80+((epoch/300 % 5))*10 ms (deterministic).
INSERT INTO monitor_checks (monitor_id, status, status_code, response_time_ms, checked_at)
SELECT '22222222-2222-2222-2222-222222222222', 'UP', 200,
       80 + (((EXTRACT(EPOCH FROM ts) / 300)::INT % 5)) * 10, ts
FROM generate_series('2026-09-21 00:00+00'::timestamptz,
                     '2026-09-23 23:55+00', interval '5 minutes') ts;

-- pay-api: UP except a DOWN burst 2026-09-22 10:00..10:10 (3 checks) and
-- a DOWN burst 2026-09-23 08:00..08:10 (3 checks, still open).
INSERT INTO monitor_checks (monitor_id, status, status_code, response_time_ms, error_message, checked_at)
SELECT '33333333-3333-3333-3333-333333333333',
       CASE WHEN ts IN ('2026-09-22 10:00+00', '2026-09-22 10:05+00', '2026-09-22 10:10+00',
                        '2026-09-23 08:00+00', '2026-09-23 08:05+00', '2026-09-23 08:10+00')
            THEN 'DOWN' ELSE 'UP' END,
       CASE WHEN ts IN ('2026-09-22 10:00+00', '2026-09-22 10:05+00', '2026-09-22 10:10+00',
                        '2026-09-23 08:00+00', '2026-09-23 08:05+00', '2026-09-23 08:10+00')
            THEN 500 ELSE 200 END,
       CASE WHEN ts IN ('2026-09-22 10:00+00', '2026-09-22 10:05+00', '2026-09-22 10:10+00',
                        '2026-09-23 08:00+00', '2026-09-23 08:05+00', '2026-09-23 08:10+00')
            THEN 420 ELSE 95 + (((EXTRACT(EPOCH FROM ts) / 300)::INT % 4)) * 15 END,
       CASE WHEN ts IN ('2026-09-22 10:00+00', '2026-09-22 10:05+00', '2026-09-22 10:10+00',
                        '2026-09-23 08:00+00', '2026-09-23 08:05+00', '2026-09-23 08:10+00')
            THEN 'unexpected status 500' ELSE NULL END,
       ts
FROM generate_series('2026-09-21 00:00+00'::timestamptz,
                     '2026-09-23 23:55+00', interval '5 minutes') ts;

-- legacy-svc: all TIMEOUT (no response time).
INSERT INTO monitor_checks (monitor_id, status, response_time_ms, error_message, checked_at)
SELECT '44444444-4444-4444-4444-444444444444', 'TIMEOUT', NULL, 'timeout', ts
FROM generate_series('2026-09-21 00:00+00'::timestamptz,
                     '2026-09-23 23:55+00', interval '5 minutes') ts;

-- Incidents (MTTR hand-computable):
-- pay-api #1 RESOLVED: 10:00 -> 10:15 = 900s. pay-api #2 OPEN 09-23 08:00.
-- legacy-svc OPEN since 09-21 00:05.
INSERT INTO incidents (id, monitor_id, status, reason, started_at, resolved_at, failure_count, recovery_count) VALUES
  ('55555555-5555-5555-5555-555555555555', '33333333-3333-3333-3333-333333333333',
   'RESOLVED', '3 consecutive failures (last: status 500 in 420ms)',
   '2026-09-22 10:00+00', '2026-09-22 10:15+00', 3, 2),
  ('66666666-6666-6666-6666-666666666666', '33333333-3333-3333-3333-333333333333',
   'OPEN', '3 consecutive failures (last: status 500 in 420ms)',
   '2026-09-23 08:00+00', NULL, 3, 0),
  ('77777777-7777-7777-7777-777777777777', '44444444-4444-4444-4444-444444444444',
   'OPEN', '3 consecutive failures (last: TIMEOUT: timeout)',
   '2026-09-21 00:05+00', NULL, 3, 0)
ON CONFLICT (id) DO NOTHING;
