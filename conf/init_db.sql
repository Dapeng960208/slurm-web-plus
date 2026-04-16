-- Slurm-web job history persistence schema
-- Run as: psql -d slurmweb -f init_db.sql

CREATE TABLE IF NOT EXISTS job_snapshots (
    id                 BIGSERIAL PRIMARY KEY,
    snapshot_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    job_id             INTEGER NOT NULL,
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
    submit_time        TIMESTAMPTZ,
    start_time         TIMESTAMPTZ,
    end_time           TIMESTAMPTZ,
    time_limit_minutes INTEGER,
    exit_code          TEXT,
    working_directory  TEXT,
    command            TEXT
);

-- 复合唯一约束：同一 job_id + 提交时间 只保留一条记录（UPSERT 依赖此约束）
CREATE UNIQUE INDEX IF NOT EXISTS idx_js_job_submit
    ON job_snapshots(job_id, submit_time);

CREATE INDEX IF NOT EXISTS idx_js_snapshot_time ON job_snapshots(snapshot_time DESC);
CREATE INDEX IF NOT EXISTS idx_js_user_name     ON job_snapshots(user_name);
CREATE INDEX IF NOT EXISTS idx_js_account       ON job_snapshots(account);
CREATE INDEX IF NOT EXISTS idx_js_partition     ON job_snapshots(partition);
CREATE INDEX IF NOT EXISTS idx_js_job_state     ON job_snapshots(job_state);

-- 授予 slurmweb 用户完整的表和序列权限
GRANT ALL PRIVILEGES ON TABLE job_snapshots TO slurmweb;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO slurmweb;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO slurmweb;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO slurmweb;
