"""
Supabase 数据层
负责：任务管理、执行记录、证据存储
"""
import os
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from supabase import create_client, Client

from config import supabase_config


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ArtifactType(str, Enum):
    BEFORE = "before"
    AFTER = "after"
    ERROR = "error"
    TRACE = "trace"


class SupabaseStore:
    """Supabase 数据存储"""
    
    def __init__(self, config=None):
        self.config = config or supabase_config
        self.client: Client = create_client(
            self.config.url,
            self.config.key
        )
    
    # ==================== 任务管理 ====================
    
    def create_task(
        self,
        shop_id: str,
        action: str,
        payload: Dict[str, Any],
        priority: int = 5,
        dry_run: bool = False
    ) -> str:
        """
        创建新任务
        
        Returns:
            task_id
        """
        task_id = str(uuid.uuid4())
        
        data = {
            "id": task_id,
            "shop_id": shop_id,
            "action": action,
            "payload": json.dumps(payload),
            "status": TaskStatus.QUEUED.value,
            "priority": priority,
            "dry_run": dry_run,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        self.client.table("agent_tasks").insert(data).execute()
        return task_id
    
    def get_next_task(self) -> Optional[Dict]:
        """获取下一个待执行的任务（按优先级）"""
        result = self.client.table("agent_tasks") \
            .select("*") \
            .eq("status", TaskStatus.QUEUED.value) \
            .order("priority", desc=True) \
            .order("created_at") \
            .limit(1) \
            .execute()
        
        if result.data:
            task = result.data[0]
            task["payload"] = json.loads(task["payload"]) if task.get("payload") else {}
            return task
        return None
    
    def update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus,
        error: Optional[str] = None
    ):
        """更新任务状态"""
        data = {
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat()
        }
        if error:
            data["error"] = error
        
        self.client.table("agent_tasks") \
            .update(data) \
            .eq("id", task_id) \
            .execute()
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务详情"""
        result = self.client.table("agent_tasks") \
            .select("*") \
            .eq("id", task_id) \
            .single() \
            .execute()
        
        if result.data:
            task = result.data
            task["payload"] = json.loads(task["payload"]) if task.get("payload") else {}
            return task
        return None
    
    # ==================== 执行记录 ====================
    
    def create_run(
        self, 
        task_id: str, 
        worker_id: str = "default"
    ) -> str:
        """
        创建执行记录
        
        Returns:
            run_id
        """
        run_id = str(uuid.uuid4())
        
        data = {
            "id": run_id,
            "task_id": task_id,
            "worker_id": worker_id,
            "start_at": datetime.utcnow().isoformat(),
        }
        
        self.client.table("agent_runs").insert(data).execute()
        return run_id
    
    def complete_run(
        self, 
        run_id: str, 
        result: Dict[str, Any],
        error: Optional[str] = None
    ):
        """完成执行记录"""
        data = {
            "end_at": datetime.utcnow().isoformat(),
            "result": json.dumps(result),
        }
        if error:
            data["error"] = error
        
        self.client.table("agent_runs") \
            .update(data) \
            .eq("id", run_id) \
            .execute()
    
    # ==================== 证据存储 ====================
    
    def upload_artifact(
        self, 
        run_id: str, 
        artifact_type: ArtifactType,
        file_path: str
    ) -> Optional[str]:
        """
        上传证据文件到 Supabase Storage
        
        Returns:
            文件 URL
        """
        try:
            # 读取文件
            with open(file_path, "rb") as f:
                file_data = f.read()
            
            # 生成存储路径
            filename = os.path.basename(file_path)
            storage_path = f"evidence/{run_id}/{artifact_type.value}_{filename}"
            
            # 上传到 Storage
            self.client.storage.from_("agent-artifacts").upload(
                storage_path,
                file_data,
                {"content-type": "image/png"}
            )
            
            # 获取公开 URL
            url = self.client.storage.from_("agent-artifacts").get_public_url(storage_path)
            
            # 记录到 artifacts 表
            artifact_id = str(uuid.uuid4())
            self.client.table("agent_artifacts").insert({
                "id": artifact_id,
                "run_id": run_id,
                "type": artifact_type.value,
                "url": url
            }).execute()
            
            return url
            
        except Exception as e:
            print(f"上传证据失败: {e}")
            return None
    
    def save_artifact_record(
        self, 
        run_id: str, 
        artifact_type: ArtifactType,
        local_path: str
    ):
        """仅记录本地证据路径（不上传）"""
        artifact_id = str(uuid.uuid4())
        self.client.table("agent_artifacts").insert({
            "id": artifact_id,
            "run_id": run_id,
            "type": artifact_type.value,
            "url": f"local://{local_path}"
        }).execute()
    
    # ==================== 便捷查询 ====================
    
    def get_pending_tasks_count(self) -> int:
        """获取待处理任务数"""
        result = self.client.table("agent_tasks") \
            .select("id", count="exact") \
            .eq("status", TaskStatus.QUEUED.value) \
            .execute()
        return result.count or 0
    
    def get_recent_runs(self, limit: int = 10) -> List[Dict]:
        """获取最近的执行记录"""
        result = self.client.table("agent_runs") \
            .select("*, agent_tasks(action, shop_id)") \
            .order("start_at", desc=True) \
            .limit(limit) \
            .execute()
        return result.data or []


# 便捷函数
def get_store() -> SupabaseStore:
    """获取数据存储实例"""
    return SupabaseStore()
