-- =============================================================================
-- Sluice ingestion platform: PostgreSQL job store, complete table structure
-- DRAFT for review, 4 Oct 2026
--
-- Source: app/models/entities.py and Alembic migrations 0001-0005 in
-- D:\ingestion-platform (0005_q4_operations is the Q4 POC addition).
--
-- How to read this file
--   * 21 tables. 16 are in the code today; 5 (and 2 job_tasks columns) come
--     from migration 0005, marked "Q4 POC".
--   * Every id is a UUID kept as VARCHAR(36), created by the app (gen_uuid).
--   * JSONVariant in the models is JSONB on PostgreSQL.
--   * Tables with TimestampMixin have created_at and updated_at.
--   * DEFAULT values below are what the app writes (SQLAlchemy client-side
--     defaults). Alembic does not create them as server defaults; they are
--     written here so the file reads, and runs, like the real behaviour.
--   * NOT NULL follows the models. Migration 0005 creates its new columns
--     without NOT NULL, so in a live database those five tables are looser
--     than shown here (noted on each table).
--   * tenant_id is a real foreign key only on users. Everywhere else it is
--     a plain indexed column; the API enforces tenant isolation.
--   * Index and constraint names follow SQLAlchemy's defaults (ix_<table>_<col>;
--     PostgreSQL's <table>_<col>_key for column-level UNIQUE).
-- =============================================================================

-- ------------------------------------------------------------------ identity

CREATE TABLE tenants (
    id              VARCHAR(36)  PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id                  VARCHAR(36)  PRIMARY KEY,
    tenant_id           VARCHAR(36)  NOT NULL REFERENCES tenants (id),
    email               VARCHAR(320) NOT NULL,
    password_hash       VARCHAR(200) NOT NULL,
    role                VARCHAR(40)  NOT NULL,              -- Role enum (5 RBAC roles)
    is_active           BOOLEAN      NOT NULL DEFAULT true,
    is_platform_admin   BOOLEAN      NOT NULL DEFAULT false, -- may cross tenants
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX        ix_users_tenant_id ON users (tenant_id);
CREATE UNIQUE INDEX ix_users_email     ON users (email);

-- -------------------------------------------------------- sources & targets

CREATE TABLE connections (
    id              VARCHAR(36)  PRIMARY KEY,
    tenant_id       VARCHAR(36)  NOT NULL,
    name            VARCHAR(200) NOT NULL,
    type            VARCHAR(50)  NOT NULL,                  -- mssql, postgres, sftp ...
    config          JSONB        NOT NULL DEFAULT '{}',     -- never holds credentials
    credential_ref  VARCHAR(200),                           -- pointer, value comes from env
    created_by      VARCHAR(36),
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_connections_tenant_id ON connections (tenant_id);
CREATE INDEX ix_connections_type      ON connections (type);

-- In the code; not used in Q4. Credentials come from environment variables
-- provided by the Systems Architecture team (decision 3 Oct).
CREATE TABLE secrets (
    id              VARCHAR(36)  PRIMARY KEY,
    ref             VARCHAR(200) NOT NULL,
    ciphertext      TEXT         NOT NULL,
    key_version     INTEGER      NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ix_secrets_ref ON secrets (ref);

CREATE TABLE targets (
    id              VARCHAR(36)  PRIMARY KEY,
    tenant_id       VARCHAR(36)  NOT NULL,
    name            VARCHAR(200) NOT NULL,
    type            VARCHAR(50)  NOT NULL,                  -- s3 | sftp | gcs | azure
    config          JSONB        NOT NULL DEFAULT '{}',
    credential_ref  VARCHAR(200),
    created_by      VARCHAR(36),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_targets_tenant_id ON targets (tenant_id);
CREATE INDEX ix_targets_type      ON targets (type);

-- ---------------------------------------------------------------- pipelines

CREATE TABLE templates (
    id              VARCHAR(36)  PRIMARY KEY,
    tenant_id       VARCHAR(36),                            -- NULL = global template
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    config          JSONB        NOT NULL,
    is_global       BOOLEAN      NOT NULL DEFAULT false,
    created_by      VARCHAR(36),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_templates_tenant_id ON templates (tenant_id);

CREATE TABLE pipelines (
    id              VARCHAR(36)  PRIMARY KEY,
    tenant_id       VARCHAR(36)  NOT NULL,
    name            VARCHAR(200) NOT NULL,
    connection_id   VARCHAR(36)  NOT NULL REFERENCES connections (id),
    target_id       VARCHAR(36)  NOT NULL REFERENCES targets (id),
    config          JSONB        NOT NULL,                  -- full pipeline config
    template_id     VARCHAR(36),                            -- logical link to templates, no FK
    created_by      VARCHAR(36),
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_pipelines_tenant_id ON pipelines (tenant_id);

-- One row per table or file a pipeline moves.
CREATE TABLE pipeline_objects (
    id                  VARCHAR(36)  PRIMARY KEY,
    pipeline_id         VARCHAR(36)  NOT NULL REFERENCES pipelines (id),
    object_type         VARCHAR(20)  NOT NULL,              -- table | file
    schema_name         VARCHAR(200),
    object_name         VARCHAR(400),                       -- tables only
    object_key          VARCHAR(600) NOT NULL,              -- "dbo.customer" or a file path
    selected            BOOLEAN      NOT NULL DEFAULT true,
    target_folder       VARCHAR(400),
    watermark_column    VARCHAR(200),
    discovered_schema   JSONB,
    row_count_estimate  BIGINT,
    last_profiled_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_pipeline_object UNIQUE (pipeline_id, object_key)
);
CREATE INDEX ix_pipeline_objects_pipeline_id ON pipeline_objects (pipeline_id);

-- --------------------------------------------------------------------- runs

-- One row per run of a pipeline.
CREATE TABLE jobs (
    id              VARCHAR(36)  PRIMARY KEY,
    tenant_id       VARCHAR(36)  NOT NULL,
    job_number      VARCHAR(30)  NOT NULL,
    pipeline_id     VARCHAR(36)  NOT NULL REFERENCES pipelines (id),
    status          VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
                    -- PENDING | RUNNING | SUCCESS | FAILED | CANCELLED | PARTIAL_SUCCESS
    mode            VARCHAR(20)  NOT NULL DEFAULT 'full',   -- full | incremental
    parallelism     INTEGER      NOT NULL DEFAULT 4,
    batch_size      INTEGER      NOT NULL DEFAULT 100000,
    created_by      VARCHAR(36),
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX        ix_jobs_tenant_id   ON jobs (tenant_id);
CREATE UNIQUE INDEX ix_jobs_job_number  ON jobs (job_number);
CREATE INDEX        ix_jobs_pipeline_id ON jobs (pipeline_id);
CREATE INDEX        ix_jobs_status      ON jobs (status);

-- One row per pipeline object in a job. This is the unit a worker claims.
CREATE TABLE job_tasks (
    id                  VARCHAR(36)  PRIMARY KEY,
    job_id              VARCHAR(36)  NOT NULL REFERENCES jobs (id),
    pipeline_object_id  VARCHAR(36)  NOT NULL REFERENCES pipeline_objects (id),
    status              VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
                        -- PENDING | RUNNING | SUCCESS | FAILED | CANCELLED | RETRY_WAIT (Q4 POC)
    attempt             INTEGER      NOT NULL DEFAULT 0,    -- fencing token
    rows_read           BIGINT       NOT NULL DEFAULT 0,
    rows_written        BIGINT       NOT NULL DEFAULT 0,
    bytes_read          BIGINT       NOT NULL DEFAULT 0,
    bytes_written       BIGINT       NOT NULL DEFAULT 0,
    watermark_value     VARCHAR(200),
    partition           JSONB,                              -- {"column","min","max"}
    output_files        JSONB,                              -- removed before a re-run
    error               TEXT,
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ,
    heartbeat_at        TIMESTAMPTZ,                        -- Q4 POC: every 30 s while RUNNING
    retry_at            TIMESTAMPTZ                         -- Q4 POC: RETRY_WAIT -> PENDING at
);
CREATE INDEX ix_job_tasks_job_id   ON job_tasks (job_id);
CREATE INDEX ix_job_tasks_status   ON job_tasks (status);
CREATE INDEX ix_job_tasks_retry_at ON job_tasks (retry_at); -- Q4 POC

-- What a run did, phase by phase.
CREATE TABLE job_events (
    id              VARCHAR(36)  PRIMARY KEY,
    job_id          VARCHAR(36)  NOT NULL REFERENCES jobs (id),
    job_task_id     VARCHAR(36)  REFERENCES job_tasks (id), -- NULL = job-level event
    ts              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    level           VARCHAR(10)  NOT NULL DEFAULT 'info',   -- info | ok | warn | error
    phase           VARCHAR(30)  NOT NULL,                  -- queue | extract | normalize | load | validate | job
    message         TEXT         NOT NULL,
    detail          JSONB
);
CREATE INDEX ix_job_events_job_id      ON job_events (job_id);
CREATE INDEX ix_job_events_job_task_id ON job_events (job_task_id);
CREATE INDEX ix_job_events_ts          ON job_events (ts);

-- Last loaded value per object, for incremental runs.
CREATE TABLE watermarks (
    id                  VARCHAR(36)  PRIMARY KEY,
    tenant_id           VARCHAR(36)  NOT NULL,
    pipeline_id         VARCHAR(36)  NOT NULL REFERENCES pipelines (id),
    pipeline_object_id  VARCHAR(36)  NOT NULL REFERENCES pipeline_objects (id),
    watermark_value     VARCHAR(200) NOT NULL,
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_watermark_obj UNIQUE (pipeline_id, pipeline_object_id)
);
CREATE INDEX ix_watermarks_tenant_id   ON watermarks (tenant_id);
CREATE INDEX ix_watermarks_pipeline_id ON watermarks (pipeline_id);

CREATE TABLE validation_results (
    id              VARCHAR(36)  PRIMARY KEY,
    job_task_id     VARCHAR(36)  NOT NULL REFERENCES job_tasks (id),
    check_name      VARCHAR(50)  NOT NULL,                  -- row_count | schema_match | nulls ...
    source_value    TEXT,
    target_value    TEXT,
    status          VARCHAR(10)  NOT NULL,                  -- PASS | FAIL | WARN
    detail          TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_validation_results_job_task_id ON validation_results (job_task_id);

CREATE TABLE job_metrics (
    id                  VARCHAR(36)  PRIMARY KEY,
    job_id              VARCHAR(36)  NOT NULL REFERENCES jobs (id),
    rows_processed      BIGINT       NOT NULL DEFAULT 0,
    bytes_processed     BIGINT       NOT NULL DEFAULT 0,
    duration_seconds    DOUBLE PRECISION,
    records_per_sec     DOUBLE PRECISION,
    mb_per_sec          DOUBLE PRECISION,
    captured_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_job_metrics_job_id ON job_metrics (job_id);

-- ------------------------------------------------------------ audit & files

-- Who did what. ids are kept as plain columns so rows outlive what they name.
CREATE TABLE audit_events (
    id              VARCHAR(36)  PRIMARY KEY,
    tenant_id       VARCHAR(36),
    user_id         VARCHAR(36),
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(50),
    resource_id     VARCHAR(36),
    job_id          VARCHAR(36),
    detail          JSONB        NOT NULL DEFAULT '{}',
    ip              VARCHAR(64),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_events_tenant_id ON audit_events (tenant_id);
CREATE INDEX ix_audit_events_user_id   ON audit_events (user_id);
CREATE INDEX ix_audit_events_action    ON audit_events (action);
CREATE INDEX ix_audit_events_job_id    ON audit_events (job_id);

CREATE TABLE uploads (
    id              VARCHAR(36)   PRIMARY KEY,
    tenant_id       VARCHAR(36)   NOT NULL,
    filename        VARCHAR(500)  NOT NULL,
    stored_path     VARCHAR(1000) NOT NULL,
    size            BIGINT        NOT NULL DEFAULT 0,
    sha256          VARCHAR(64),
    status          VARCHAR(20)   NOT NULL DEFAULT 'UPLOADED',
    created_by      VARCHAR(36),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX ix_uploads_tenant_id ON uploads (tenant_id);

-- ------------------------------------------- Q4 POC: migration 0005_q4_operations
-- Migration 0005 creates these columns as nullable; NOT NULL below is the model.

-- When a pipeline runs by itself (ING-26). One schedule per pipeline.
CREATE TABLE schedules (
    id              VARCHAR(36)  PRIMARY KEY,
    tenant_id       VARCHAR(36)  NOT NULL,
    pipeline_id     VARCHAR(36)  NOT NULL UNIQUE REFERENCES pipelines (id),
    cron            VARCHAR(100) NOT NULL,                  -- 5-field cron, in timezone
    timezone        VARCHAR(64)  NOT NULL DEFAULT 'UTC',
    mode            VARCHAR(20)  NOT NULL DEFAULT 'full',   -- full | incremental
    enabled         BOOLEAN      NOT NULL DEFAULT true,
    overlap         VARCHAR(10)  NOT NULL DEFAULT 'skip',   -- skip while the last run is unfinished
    next_run_at     TIMESTAMPTZ,
    last_run_at     TIMESTAMPTZ,
    last_job_id     VARCHAR(36),                            -- logical link to jobs, no FK
    last_outcome    VARCHAR(40),                            -- started | skipped_overlap | error
    created_by      VARCHAR(36),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_schedules_tenant_id   ON schedules (tenant_id);
CREATE INDEX ix_schedules_next_run_at ON schedules (next_run_at);

-- Where a tenant's alerts go (ING-19). The webhook URL is a credential_ref.
CREATE TABLE alert_channels (
    id              VARCHAR(36)  PRIMARY KEY,
    tenant_id       VARCHAR(36)  NOT NULL,
    name            VARCHAR(200) NOT NULL,
    kind            VARCHAR(20)  NOT NULL,                  -- teams | slack
    credential_ref  VARCHAR(200) NOT NULL,
    events          JSONB        NOT NULL DEFAULT '[]',
    enabled         BOOLEAN      NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_alert_channels_tenant_id ON alert_channels (tenant_id);

-- One row per alert sent. dedupe_key is unique, so one failure = one alert.
CREATE TABLE alert_deliveries (
    id              VARCHAR(36)  PRIMARY KEY,
    tenant_id       VARCHAR(36)  NOT NULL,
    channel_id      VARCHAR(36)  NOT NULL REFERENCES alert_channels (id),
    event           VARCHAR(40)  NOT NULL,
    dedupe_key      VARCHAR(200) NOT NULL UNIQUE,
    status          VARCHAR(10)  NOT NULL,                  -- sent | failed
    http_status     INTEGER,
    title           VARCHAR(300) NOT NULL,
    detail          JSONB,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_alert_deliveries_tenant_id  ON alert_deliveries (tenant_id);
CREATE INDEX ix_alert_deliveries_channel_id ON alert_deliveries (channel_id);

-- How one object is compared with the legacy pipeline's output (ING-15/21/24).
CREATE TABLE reconciliation_specs (
    id                  VARCHAR(36)  PRIMARY KEY,
    tenant_id           VARCHAR(36)  NOT NULL,
    pipeline_id         VARCHAR(36)  NOT NULL REFERENCES pipelines (id),
    pipeline_object_id  VARCHAR(36)  NOT NULL REFERENCES pipeline_objects (id),
    legacy_target_id    VARCHAR(36)  NOT NULL REFERENCES targets (id),
    legacy_path         VARCHAR(600) NOT NULL,              -- glob under the target's base path
    legacy_format       VARCHAR(20)  NOT NULL DEFAULT 'csv', -- csv | parquet
    key_columns         JSONB        NOT NULL DEFAULT '[]',
    ignore_columns      JSONB        NOT NULL DEFAULT '[]',
    numeric_tolerance   DOUBLE PRECISION NOT NULL DEFAULT 0,
    enabled             BOOLEAN      NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_recon_object UNIQUE (pipeline_object_id)
);
CREATE INDEX ix_reconciliation_specs_tenant_id   ON reconciliation_specs (tenant_id);
CREATE INDEX ix_reconciliation_specs_pipeline_id ON reconciliation_specs (pipeline_id);

CREATE TABLE reconciliation_runs (
    id              VARCHAR(36)  PRIMARY KEY,
    tenant_id       VARCHAR(36)  NOT NULL,
    spec_id         VARCHAR(36)  NOT NULL REFERENCES reconciliation_specs (id),
    pipeline_id     VARCHAR(36)  NOT NULL,                  -- logical link, no FK
    job_id          VARCHAR(36),                            -- logical link, no FK
    status          VARCHAR(10)  NOT NULL,                  -- PASS | FAIL | ERROR
    platform_rows   BIGINT,
    legacy_rows     BIGINT,
    result          JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_reconciliation_runs_tenant_id   ON reconciliation_runs (tenant_id);
CREATE INDEX ix_reconciliation_runs_spec_id     ON reconciliation_runs (spec_id);
CREATE INDEX ix_reconciliation_runs_pipeline_id ON reconciliation_runs (pipeline_id);
CREATE INDEX ix_reconciliation_runs_job_id      ON reconciliation_runs (job_id);
CREATE INDEX ix_reconciliation_runs_created_at  ON reconciliation_runs (created_at);
