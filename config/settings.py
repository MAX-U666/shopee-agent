"""
紫鸟 + Shopee Agent 配置文件
请根据实际情况修改以下配置
"""
import os
from dataclasses import dataclass

@dataclass
class ZiNiaoConfig:
    """紫鸟浏览器配置"""
    # 紫鸟客户端路径 (Windows)
    client_path: str = r"C:\Program Files\ziniao\ziniao.exe"
    
    # 紫鸟账号信息
    company: str = "你的公司名"
    username: str = "你的用户名"
    password: str = "你的密码"
    
    # 通讯端口
    socket_port: int = 19888
    
    # HTTP 超时时间（秒）
    timeout: int = 120


@dataclass
class SupabaseConfig:
    """Supabase 配置"""
    url: str = os.getenv("SUPABASE_URL", "https://xxx.supabase.co")
    key: str = os.getenv("SUPABASE_KEY", "your-anon-key")


@dataclass
class AgentConfig:
    """Agent 执行器配置"""
    # 截图保存路径
    screenshot_dir: str = "./evidence"
    
    # 是否启用无头模式（建议开发时关闭，方便调试）
    headless: bool = False
    
    # 操作间隔（秒），防止过快触发风控
    action_delay: float = 1.0
    
    # 最大重试次数
    max_retries: int = 2


# 全局配置实例
ziniao_config = ZiNiaoConfig()
supabase_config = SupabaseConfig()
agent_config = AgentConfig()
