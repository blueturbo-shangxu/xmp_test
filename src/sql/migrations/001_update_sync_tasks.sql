-- 同步任务表结构更新迁移脚本
-- 新增字段: sync_params, initiator_type, initiator_id, error_traceback, max_retry_count, retry_interval_seconds
-- 删除字段: next_retry_at

-- 1. 添加新字段
ALTER TABLE sync_tasks ADD COLUMN IF NOT EXISTS sync_params JSONB DEFAULT '{}';
COMMENT ON COLUMN sync_tasks.sync_params IS '同步参数条件(如: {"ad_group_id": "123", "campaign_id": "456"})';

ALTER TABLE sync_tasks ADD COLUMN IF NOT EXISTS initiator_type VARCHAR(20) DEFAULT 'PROGRAM';
COMMENT ON COLUMN sync_tasks.initiator_type IS '发起者类型: USER, PROGRAM';

ALTER TABLE sync_tasks ADD COLUMN IF NOT EXISTS initiator_id VARCHAR(100);
COMMENT ON COLUMN sync_tasks.initiator_id IS '发起者ID: 用户ID或程序代号';

ALTER TABLE sync_tasks ADD COLUMN IF NOT EXISTS error_traceback TEXT;
COMMENT ON COLUMN sync_tasks.error_traceback IS '错误堆栈详情';

ALTER TABLE sync_tasks ADD COLUMN IF NOT EXISTS max_retry_count INTEGER DEFAULT 3;
COMMENT ON COLUMN sync_tasks.max_retry_count IS '最大重试次数';

ALTER TABLE sync_tasks ADD COLUMN IF NOT EXISTS retry_interval_seconds INTEGER DEFAULT 60;
COMMENT ON COLUMN sync_tasks.retry_interval_seconds IS '重试间隔(秒)';

-- 2. 删除旧字段 (如果存在)
ALTER TABLE sync_tasks DROP COLUMN IF EXISTS next_retry_at;

-- 3. 添加约束 (如果不存在)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_initiator_type'
    ) THEN
        ALTER TABLE sync_tasks ADD CONSTRAINT ck_initiator_type
        CHECK (initiator_type IN ('USER', 'PROGRAM'));
    END IF;
END $$;

-- 4. 更新现有数据的默认值
UPDATE sync_tasks SET sync_params = '{}' WHERE sync_params IS NULL;
UPDATE sync_tasks SET initiator_type = 'PROGRAM' WHERE initiator_type IS NULL;
UPDATE sync_tasks SET max_retry_count = 3 WHERE max_retry_count IS NULL;
UPDATE sync_tasks SET retry_interval_seconds = 60 WHERE retry_interval_seconds IS NULL;
