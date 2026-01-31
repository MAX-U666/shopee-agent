# Shopee Agent MVP

基于紫鸟浏览器 + Selenium 的 Shopee 后台自动化执行器。

## 功能

MVP 版本支持 3 个 Action：

| Action | 说明 | 风险 |
|--------|------|------|
| `fetch_ads_summary` | 获取广告汇总数据 | 只读，低 |
| `fetch_product_snapshot` | 获取商品列表快照 | 只读，低 |
| `update_title` | 更新商品标题 | 写操作，中 |

## 目录结构

```
shopee-agent/
├── config/
│   ├── __init__.py
│   └── settings.py          # 配置文件（需修改）
├── core/
│   ├── __init__.py
│   ├── ziniao_client.py     # 紫鸟客户端连接
│   ├── browser_controller.py # Selenium 控制器
│   └── supabase_store.py    # 数据存储
├── actions/
│   ├── __init__.py
│   ├── base_action.py       # Action 基类
│   ├── locators.py          # 页面定位器配置
│   ├── fetch_ads_summary.py
│   ├── fetch_product_snapshot.py
│   └── update_title.py
├── drivers/                  # ChromeDriver 放这里
├── evidence/                 # 截图存储
├── worker.py                 # 主程序
├── test_runner.py           # 测试脚本
├── requirements.txt
├── supabase_schema.sql      # 数据库表结构
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `config/settings.py`：

```python
@dataclass
class ZiNiaoConfig:
    # 紫鸟客户端路径
    client_path: str = r"C:\Program Files\ziniao\ziniao.exe"
    
    # 紫鸟账号
    company: str = "你的公司名"
    username: str = "你的用户名"
    password: str = "你的密码"
    
    # 通讯端口
    socket_port: int = 19888

@dataclass
class SupabaseConfig:
    url: str = "https://xxx.supabase.co"
    key: str = "your-anon-key"
```

### 3. 下载 ChromeDriver

根据紫鸟返回的内核版本，下载对应的 ChromeDriver：

1. 运行 `test_runner.py`，会显示内核版本（如 `131`）
2. 从紫鸟文档下载对应版本的 chromedriver
3. 放到 `drivers/` 目录，命名为 `chromedriver_131.exe`

### 4. 初始化数据库

在 Supabase SQL Editor 中执行 `supabase_schema.sql`。

### 5. 测试

```bash
python test_runner.py
```

### 6. 运行 Worker

```bash
python worker.py
```

## 创建任务

### 方式 1：直接写入 Supabase

```sql
INSERT INTO agent_tasks (shop_id, action, payload, priority)
VALUES (
    'your_shop_name',
    'fetch_product_snapshot',
    '{"keyword": "", "limit": 10}',
    5
);
```

### 方式 2：通过代码

```python
from core.supabase_store import get_store

store = get_store()
task_id = store.create_task(
    shop_id="your_shop_name",
    action="update_title",
    payload={
        "product_id": "123456789",
        "new_title": "新标题..."
    },
    priority=5
)
```

### 方式 3：通过 n8n

在 n8n 中添加 Supabase 节点，写入 `agent_tasks` 表即可。

## Action 参数说明

### fetch_ads_summary

```json
{
  "date_range": "today"  // 可选：today, 7days, 30days
}
```

### fetch_product_snapshot

```json
{
  "keyword": "",    // 搜索关键词（可选）
  "limit": 10       // 最多获取数量
}
```

### update_title

```json
{
  "product_id": "123456789",  // 商品ID（必需）
  "new_title": "新标题...",   // 新标题（必需）
  "product_name": "搜索关键词" // 用于搜索定位（可选）
}
```

## 定位器维护

当 Shopee 页面结构变化时，需要更新 `actions/locators.py` 中的选择器。

建议：
1. 定期运行一个"健康检查"任务
2. 失败时触发告警
3. 人工更新 locators

## 注意事项

1. **登录态**：紫鸟会自动管理登录态，无需额外处理
2. **风控**：建议每小时操作不超过 5-10 次
3. **多店铺**：每个店铺独立的浏览器实例，不会串 session
4. **证据**：所有操作都会截图，存储在 `evidence/` 目录

## 与你现有系统对接

```
AI 决策层（你现有）
   ↓ 生成 task JSON
n8n（写入 Supabase）
   ↓
agent_tasks 表
   ↓
Worker（本项目）
   ↓ 执行 & 回写
agent_runs / agent_artifacts
   ↓
n8n（读取结果，更新实验卡）
```

## 常见问题

### Q: ChromeDriver 版本不匹配
A: 运行 test_runner.py 查看内核版本，下载对应的 chromedriver。

### Q: 连接紫鸟失败
A: 确保紫鸟客户端已关闭（不能同时运行 GUI 和 webdriver 模式）。

### Q: 元素定位失败
A: Shopee 可能改版了，需要更新 locators.py 中的选择器。

### Q: 操作被风控
A: 降低操作频率，增加 action_delay 配置。
