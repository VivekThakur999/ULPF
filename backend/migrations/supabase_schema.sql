-- =============================================================================
-- Universal Log Pre-processing Framework (ULPF)
-- SIH 2026 | Problem ID: SIH26156 | NTRO
-- Supabase PostgreSQL Control Plane Schema & Row Level Security (RLS) Policies
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 1. ROLES TABLE (Canonical RBAC Roles: ADMIN, ANALYST, VIEWER)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.roles (
    name VARCHAR(32) PRIMARY KEY,
    description VARCHAR(255) NOT NULL DEFAULT ''
);

INSERT INTO public.roles (name, description) VALUES
    ('ADMIN', 'Full administrative access to settings, users, and audit logs'),
    ('ANALYST', 'Access to ingestion, investigation, rules, templates, and analytics'),
    ('VIEWER', 'Read-only access to dashboards and logs')
ON CONFLICT (name) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 2. APP USERS TABLE (Control Plane Identities & Supabase Auth Sync)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.app_users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    supabase_user_id VARCHAR(64) UNIQUE,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL DEFAULT '',
    password_hash VARCHAR(255),  -- Nullable for Supabase Auth OAuth/JWT users
    role_name VARCHAR(32) NOT NULL DEFAULT 'VIEWER' REFERENCES public.roles(name) ON UPDATE CASCADE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS ix_app_users_email ON public.app_users (email);
CREATE INDEX IF NOT EXISTS ix_app_users_supabase_user_id ON public.app_users (supabase_user_id);
CREATE INDEX IF NOT EXISTS ix_app_users_role_name ON public.app_users (role_name);

-- -----------------------------------------------------------------------------
-- 3. AUDIT LOGS TABLE (Forensic Action Logging)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    ts TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    actor_id VARCHAR(36),
    actor_email VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(64),
    target_id VARCHAR(64),
    detail TEXT NOT NULL DEFAULT '',
    ip_address VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_ts ON public.audit_logs (ts DESC);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON public.audit_logs (action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_id ON public.audit_logs (actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_action_ts ON public.audit_logs (action, ts DESC);

-- -----------------------------------------------------------------------------
-- 4. LOG SOURCES TABLE (Configured Adapters & Data Feeds)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.log_sources (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name VARCHAR(120) UNIQUE NOT NULL,
    category VARCHAR(64) NOT NULL,
    adapter VARCHAR(32) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    connection_status VARCHAR(32) NOT NULL DEFAULT 'DISCONNECTED',
    events_processed BIGINT NOT NULL DEFAULT 0,
    last_received_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS ix_log_sources_name ON public.log_sources (name);
CREATE INDEX IF NOT EXISTS ix_log_sources_category ON public.log_sources (category);

-- -----------------------------------------------------------------------------
-- 5. PRIVACY & PII SETTINGS (Pseudonymization Policies)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pii_settings (
    id VARCHAR(36) PRIMARY KEY,
    mode VARCHAR(32) NOT NULL DEFAULT 'DETERMINISTIC_HASH',
    enabled_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO public.pii_settings (id, mode, enabled_fields) VALUES
    ('default', 'DETERMINISTIC_HASH', '["source_ip", "destination_ip", "username", "email", "mac_address"]'::jsonb)
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 6. SECURITY RULES (Detection Engine Correlation Rules)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.security_rules (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    rule_key VARCHAR(48) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    severity VARCHAR(16) NOT NULL DEFAULT 'medium',
    threshold INT NOT NULL DEFAULT 5,
    window_seconds INT NOT NULL DEFAULT 300,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    params JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS ix_security_rules_rule_key ON public.security_rules (rule_key);
CREATE INDEX IF NOT EXISTS ix_security_rules_severity ON public.security_rules (severity);

-- Baseline Security Rules Seeding
INSERT INTO public.security_rules (id, rule_key, name, description, severity, threshold, window_seconds, is_enabled, params) VALUES
    (gen_random_uuid()::text, 'RULE_1', 'Multiple failed logins from same source', 'More than N failed authentication events from one source IP within the window.', 'high', 5, 120, true, '{}'::jsonb),
    (gen_random_uuid()::text, 'RULE_2', 'Brute-force pattern', 'Sustained high-rate authentication failures against a host/service.', 'high', 10, 300, true, '{}'::jsonb),
    (gen_random_uuid()::text, 'RULE_3', 'Repeated auth failures across multiple hosts', 'Same source failing authentication against 3+ distinct hosts.', 'high', 3, 600, true, '{"distinct_hosts": 3}'::jsonb),
    (gen_random_uuid()::text, 'RULE_4', 'Unusual login frequency', 'Login attempt rate for an account far exceeds its normal baseline.', 'medium', 20, 300, true, '{}'::jsonb),
    (gen_random_uuid()::text, 'RULE_5', 'Suspicious network connection sequence', 'Firewall connection followed by repeated auth failures from the same source.', 'medium', 1, 180, true, '{}'::jsonb),
    (gen_random_uuid()::text, 'RULE_6', 'Failed auth burst followed by success', 'Several failed authentications then a successful login for the same account/source.', 'critical', 4, 300, true, '{}'::jsonb),
    (gen_random_uuid()::text, 'RULE_7', 'Suspicious log-injection payload', 'Security Shield flagged a raw log as SUSPICIOUS or WEAPONIZED_LOG.', 'high', 1, 3600, true, '{}'::jsonb),
    (gen_random_uuid()::text, 'RULE_8', 'Abnormal event burst', 'Event volume from a source spikes far above its recent rate.', 'medium', 100, 60, true, '{}'::jsonb)
ON CONFLICT (rule_key) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 7. PARSER PACKS & PARSER VERSIONS (Dynamic Parser Engine)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.parser_packs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name VARCHAR(120) UNIQUE NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category VARCHAR(64) NOT NULL,
    active_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS ix_parser_packs_name ON public.parser_packs (name);

CREATE TABLE IF NOT EXISTS public.parser_versions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    pack_id VARCHAR(36) NOT NULL REFERENCES public.parser_packs(id) ON DELETE CASCADE,
    version VARCHAR(32) NOT NULL,
    engine VARCHAR(32) NOT NULL DEFAULT 'regex',
    grammar_definition JSONB NOT NULL DEFAULT '{}'::jsonb,
    compiled_wasm BYTEA,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    changelog TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS ix_parser_versions_pack_id ON public.parser_versions (pack_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_parser_pack_version ON public.parser_versions (pack_id, version);

-- -----------------------------------------------------------------------------
-- 8. AUTOMATIC TIMESTAMP TRIGGER
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = clock_timestamp();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_app_users_updated_at ON public.app_users;
CREATE TRIGGER trg_app_users_updated_at
    BEFORE UPDATE ON public.app_users
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_log_sources_updated_at ON public.log_sources;
CREATE TRIGGER trg_log_sources_updated_at
    BEFORE UPDATE ON public.log_sources
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_pii_settings_updated_at ON public.pii_settings;
CREATE TRIGGER trg_pii_settings_updated_at
    BEFORE UPDATE ON public.pii_settings
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_security_rules_updated_at ON public.security_rules;
CREATE TRIGGER trg_security_rules_updated_at
    BEFORE UPDATE ON public.security_rules
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_parser_packs_updated_at ON public.parser_packs;
CREATE TRIGGER trg_parser_packs_updated_at
    BEFORE UPDATE ON public.parser_packs
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- -----------------------------------------------------------------------------
-- 9. SUPABASE AUTH AUTO-PROVISIONING TRIGGER
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_supabase_user()
RETURNS TRIGGER AS $$
DECLARE
    assigned_role VARCHAR(32);
    user_full_name VARCHAR(255);
BEGIN
    assigned_role := COALESCE(
        NEW.raw_app_meta_data->>'role',
        NEW.raw_user_meta_data->>'role',
        'VIEWER'
    );
    assigned_role := UPPER(assigned_role);
    IF assigned_role NOT IN ('ADMIN', 'ANALYST', 'VIEWER') THEN
        assigned_role := 'VIEWER';
    END IF;

    user_full_name := COALESCE(
        NEW.raw_user_meta_data->>'full_name',
        NEW.raw_user_meta_data->>'name',
        ''
    );

    INSERT INTO public.app_users (
        supabase_user_id,
        email,
        full_name,
        role_name,
        is_active,
        last_login_at
    )
    VALUES (
        NEW.id::text,
        NEW.email,
        user_full_name,
        assigned_role,
        TRUE,
        clock_timestamp()
    )
    ON CONFLICT (email) DO UPDATE SET
        supabase_user_id = EXCLUDED.supabase_user_id,
        full_name = CASE WHEN public.app_users.full_name = '' THEN EXCLUDED.full_name ELSE public.app_users.full_name END,
        last_login_at = clock_timestamp(),
        updated_at = clock_timestamp();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_supabase_user();

-- -----------------------------------------------------------------------------
-- 10. ROW LEVEL SECURITY (RLS) POLICIES
-- -----------------------------------------------------------------------------
ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.log_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pii_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.security_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parser_packs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parser_versions ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.current_user_role()
RETURNS VARCHAR AS $$
BEGIN
    RETURN COALESCE(
        current_setting('request.jwt.claims', true)::jsonb->'app_metadata'->>'role',
        current_setting('request.jwt.claims', true)::jsonb->'user_metadata'->>'role',
        'VIEWER'
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Service Role Policies (Backend Admin Access)
CREATE POLICY "Service Role Full Access - roles" ON public.roles FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access - app_users" ON public.app_users FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access - audit_logs" ON public.audit_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access - log_sources" ON public.log_sources FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access - pii_settings" ON public.pii_settings FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access - security_rules" ON public.security_rules FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access - parser_packs" ON public.parser_packs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Full Access - parser_versions" ON public.parser_versions FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Authenticated Users Policies
CREATE POLICY "Authenticated users can read roles" ON public.roles FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read log sources" ON public.log_sources FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read pii settings" ON public.pii_settings FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read security rules" ON public.security_rules FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read parser packs" ON public.parser_packs FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read parser versions" ON public.parser_versions FOR SELECT TO authenticated USING (true);

CREATE POLICY "Users can read their own profile" ON public.app_users FOR SELECT TO authenticated
    USING (supabase_user_id = auth.uid()::text OR email = auth.jwt()->>'email');

CREATE POLICY "Admins can manage app users" ON public.app_users FOR ALL TO authenticated
    USING (public.current_user_role() = 'ADMIN')
    WITH CHECK (public.current_user_role() = 'ADMIN');

CREATE POLICY "Admins can view all audit logs" ON public.audit_logs FOR SELECT TO authenticated
    USING (public.current_user_role() = 'ADMIN');

CREATE POLICY "Admins and Analysts can manage log sources" ON public.log_sources FOR ALL TO authenticated
    USING (public.current_user_role() IN ('ADMIN', 'ANALYST'))
    WITH CHECK (public.current_user_role() IN ('ADMIN', 'ANALYST'));

CREATE POLICY "Admins and Analysts can manage security rules" ON public.security_rules FOR ALL TO authenticated
    USING (public.current_user_role() IN ('ADMIN', 'ANALYST'))
    WITH CHECK (public.current_user_role() IN ('ADMIN', 'ANALYST'));
