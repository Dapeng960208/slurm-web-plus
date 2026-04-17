-- Slurm-web job history persistence schema
-- Table is partitioned by submit_time (monthly) for query performance at scale.
-- Partitions are created automatically by the persistence layer (jobs_store.py).
-- Run this script once to initialise the database:
--   psql -U slurmweb -d slurmweb -f conf/init_db.sql

CREATE TABLE IF NOT EXISTS job_snapshots (
    id                 BIGSERIAL,
    job_id             INTEGER      NOT NULL,
    submit_time        TIMESTAMPTZ  NOT NULL,   -- partition key; never NULL (filtered at app layer)
    first_seen         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_seen          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    job_name           TEXT,
    job_state          TEXT,
    state_reason       TEXT,
    user_name          TEXT,
    account            TEXT,
    "group"            TEXT,
    partition          TEXT,
    qos                TEXT,
    nodes              TEXT,
    node_count         INTEGER,
    cpus               INTEGER,
    priority           INTEGER,
    tres_req_str       TEXT,
    tres_per_job       TEXT,
    tres_per_node      TEXT,
    gres_detail        TEXT,
    start_time         TIMESTAMPTZ,
    end_time           TIMESTAMPTZ,
    time_limit_minutes INTEGER,
    exit_code          TEXT,
    working_directory  TEXT,
    command            TEXT,
    PRIMARY KEY (id, submit_time)
) PARTITION BY RANGE (submit_time);

-- Unique constraint for UPSERT conflict detection.
-- Must include the partition key (submit_time) for partitioned tables.
CREATE UNIQUE INDEX IF NOT EXISTS idx_js_job_submit
    ON job_snapshots (job_id, submit_time);

-- Supporting indexes for common query filters
CREATE INDEX IF NOT EXISTS idx_js_last_seen   ON job_snapshots (last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_js_user_name   ON job_snapshots (user_name);
CREATE INDEX IF NOT EXISTS idx_js_account     ON job_snapshots (account);
CREATE INDEX IF NOT EXISTS idx_js_partition   ON job_snapshots (partition);
CREATE INDEX IF NOT EXISTS idx_js_job_state   ON job_snapshots (job_state);

-- Default partition to catch any rows that fall outside explicit monthly partitions.
-- This prevents INSERT errors if the auto-partition logic hasn't run yet.
CREATE TABLE IF NOT EXISTS job_snapshots_default
    PARTITION OF job_snapshots DEFAULT;
