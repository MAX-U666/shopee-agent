-- Shopee Agent 数据库表结构
-- 在 Supabase SQL Editor 中执行

-- ============================================
-- 1. agent_tasks - 任务表
-- ============================================
CREATE TABLE IF NOT EXISTS agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shop_id TEXT NOT NULL,
    action TEXT NOT NULL,
    payload JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'queued',
    priority INTEGER DEFAULT 5,
    dry_run BOOLEAN DEFAULT FALSE,
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON agent_tasks(status);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_priority ON agent_tasks(priority DESC);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_shop_id ON agent_tasks(shop_id);

-- 注释
COMMENT ON TABLE agent_tasks IS '执行任务表';
COMMENT ON COLUMN agent_tasks.shop_id IS '店铺ID';
COMMENT ON COLUMN agent_tasks.action IS '动作类型：fetch_ads_summary, update_title, fetch_product_snapshot';
COMMENT ON COLUMN agent_tasks.payload IS '任务参数（JSON）';
COMMENT ON COLUMN agent_tasks.status IS '状态：queued, running, success, failed';
COMMENT ON COLUMN agent_tasks.priority IS '优先级，数字越大越优先';
COMMENT ON COLUMN agent_tasks.dry_run IS '是否测试模式（不实际执行）';


-- ============================================
-- 2. agent_runs - 执行记录表
-- ============================================
CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES agent_tasks(id) ON DELETE CASCADE,
    worker_id TEXT DEFAULT 'default',
    start_at TIMESTAMPTZ DEFAULT NOW(),
    end_at TIMESTAMPTZ,
    result JSONB DEFAULT '{}',
    error TEXT
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_agent_runs_task_id ON agent_runs(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_start_at ON agent_runs(start_at DESC);

-- 注释
COMMENT ON TABLE agent_runs IS '任务执行记录表';
COMMENT ON COLUMN agent_runs.task_id IS '关联的任务ID';
COMMENT ON COLUMN agent_runs.worker_id IS '执行该任务的 Worker 标识';
COMMENT ON COLUMN agent_runs.result IS '执行结果（JSON）';


-- ============================================
-- 3. agent_artifacts - 证据/产物表
-- ============================================
CREATE TABLE IF NOT EXISTS agent_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    url TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_agent_artifacts_run_id ON agent_artifacts(run_id);

-- 注释
COMMENT ON TABLE agent_artifacts IS '执行证据表（截图、日志等）';
COMMENT ON COLUMN agent_artifacts.type IS '类型：before, after, error, trace';
COMMENT ON COLUMN agent_artifacts.url IS '文件地址（Supabase Storage URL 或本地路径）';


-- ============================================
-- 4. 创建 Storage Bucket（可选）
-- ============================================
-- 在 Supabase Dashboard -> Storage 中手动创建名为 "agent-artifacts" 的 Bucket
-- 或使用以下 SQL（需要 storage admin 权限）：

-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('agent-artifacts', 'agent-artifacts', true)
-- ON CONFLICT (id) DO NOTHING;


-- ============================================
-- 5. RLS 策略（可选，根据安全需求配置）
-- ============================================
-- 默认禁用 RLS，方便开发调试
-- 生产环境建议启用

-- ALTER TABLE agent_tasks ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE agent_artifacts ENABLE ROW LEVEL SECURITY;


-- ============================================
-- 6. 辅助函数
-- ============================================

-- 自动更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_agent_tasks_updated_at
    BEFORE UPDATE ON agent_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();


-- ============================================
-- 7. 示例数据（测试用）
-- ============================================
-- 插入一个测试任务
-- INSERT INTO agent_tasks (shop_id, action, payload, priority, dry_run)
-- VALUES (
--     'test_shop',
--     'fetch_product_snapshot',
--     '{"keyword": "test", "limit": 5}',
--     5,
--     true
-- );
