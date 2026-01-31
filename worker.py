"""
Worker 主程序
负责：拉取任务、执行 Action、回写结果
"""
import time
import json
import traceback
from typing import Optional, Dict, Any
from dataclasses import asdict

from core.ziniao_client import ZiNiaoClient, get_ziniao_client
from core.browser_controller import BrowserController, create_browser_controller
from core.supabase_store import SupabaseStore, get_store, TaskStatus
from actions import get_action_class, ActionContext, list_available_actions
from config import ziniao_config, agent_config


class Worker:
    """任务执行 Worker"""
    
    def __init__(
        self,
        worker_id: str = "default",
        shop_browser_map: Optional[Dict[str, str]] = None
    ):
        """
        初始化 Worker
        
        Args:
            worker_id: Worker 标识
            shop_browser_map: 店铺ID到紫鸟浏览器ID的映射
                例如: {"shop_01": "12345", "shop_02": "67890"}
        """
        self.worker_id = worker_id
        self.shop_browser_map = shop_browser_map or {}
        
        self.ziniao: Optional[ZiNiaoClient] = None
        self.store: Optional[SupabaseStore] = None
        self.active_browsers: Dict[str, BrowserController] = {}  # shop_id -> controller
        
        self._running = False
    
    def setup(self) -> bool:
        """初始化 Worker"""
        print(f"[Worker-{self.worker_id}] 初始化中...")
        
        # 初始化紫鸟客户端
        self.ziniao = get_ziniao_client()
        if not self.ziniao.start_client():
            print("紫鸟客户端启动失败")
            return False
        
        # 初始化 Supabase
        try:
            self.store = get_store()
            print("Supabase 连接成功")
        except Exception as e:
            print(f"Supabase 连接失败: {e}")
            return False
        
        # 获取店铺列表（如果没有提供映射）
        if not self.shop_browser_map:
            browsers = self.ziniao.get_browser_list()
            for b in browsers:
                # 简单映射：用 browser_name 作为 shop_id
                self.shop_browser_map[b.browser_name] = b.browser_id
                print(f"  发现店铺: {b.browser_name} -> {b.browser_id}")
        
        print(f"[Worker-{self.worker_id}] 初始化完成")
        return True
    
    def get_browser_for_shop(self, shop_id: str, site: str = "id") -> Optional[BrowserController]:
        """
        获取或创建指定店铺的浏览器控制器
        
        Args:
            shop_id: 店铺ID
            site: 站点代码
        
        Returns:
            BrowserController 或 None
        """
        # 如果已有活跃的浏览器，直接返回
        if shop_id in self.active_browsers:
            return self.active_browsers[shop_id]
        
        # 获取紫鸟浏览器ID
        browser_id = self.shop_browser_map.get(shop_id)
        if not browser_id:
            print(f"未找到店铺 {shop_id} 的浏览器映射")
            return None
        
        # 启动浏览器
        result = self.ziniao.start_browser(
            browser_id=browser_id,
            headless=agent_config.headless
        )
        
        if not result.success:
            print(f"启动浏览器失败: {result.error}")
            return None
        
        print(f"浏览器已启动，端口: {result.debugging_port}, 内核: {result.core_type} {result.core_version}")
        
        # 创建控制器并连接
        controller = create_browser_controller(
            debugging_port=result.debugging_port,
            core_version=result.core_version.split('.')[0] if result.core_version else "131"
        )
        
        if not controller.connect():
            print("连接浏览器失败")
            return None
        
        self.active_browsers[shop_id] = controller
        return controller
    
    def execute_task(self, task: Dict[str, Any]) -> bool:
        """
        执行单个任务
        
        Returns:
            是否执行成功
        """
        task_id = task["id"]
        shop_id = task["shop_id"]
        action_name = task["action"]
        payload = task.get("payload", {})
        dry_run = task.get("dry_run", False)
        
        print(f"\n[Task-{task_id}] 开始执行")
        print(f"  Shop: {shop_id}")
        print(f"  Action: {action_name}")
        print(f"  Payload: {json.dumps(payload, ensure_ascii=False)[:100]}...")
        
        # 1. 标记任务为运行中
        self.store.update_task_status(task_id, TaskStatus.RUNNING)
        
        # 2. 创建执行记录
        run_id = self.store.create_run(task_id, self.worker_id)
        
        try:
            # 3. 获取浏览器控制器
            browser = self.get_browser_for_shop(shop_id)
            if not browser:
                raise Exception(f"无法获取店铺 {shop_id} 的浏览器")
            
            # 4. 获取 Action 类并实例化
            action_class = get_action_class(action_name)
            action = action_class(browser, self.store)
            
            # 5. 构建执行上下文
            context = ActionContext(
                task_id=task_id,
                run_id=run_id,
                shop_id=shop_id,
                site=payload.get("locale", "id").split("-")[0],  # "id-ID" -> "id"
                dry_run=dry_run
            )
            
            # 6. 执行 Action
            result = action.execute(context, payload)
            
            # 7. 记录执行结果
            self.store.complete_run(
                run_id=run_id,
                result=asdict(result),
                error=result.error_message if not result.ok else None
            )
            
            # 8. 更新任务状态
            if result.ok:
                self.store.update_task_status(task_id, TaskStatus.SUCCESS)
                print(f"[Task-{task_id}] ✓ 执行成功，耗时 {result.timing_ms}ms")
            else:
                self.store.update_task_status(
                    task_id, 
                    TaskStatus.FAILED,
                    error=f"{result.error_code}: {result.error_message}"
                )
                print(f"[Task-{task_id}] ✗ 执行失败: {result.error_code}")
            
            return result.ok
            
        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"[Task-{task_id}] ✗ 异常: {e}")
            
            self.store.complete_run(run_id, result={}, error=str(e))
            self.store.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
            
            return False
    
    def run_once(self) -> bool:
        """
        执行一次任务循环
        
        Returns:
            是否有任务被执行
        """
        task = self.store.get_next_task()
        if not task:
            return False
        
        self.execute_task(task)
        return True
    
    def run_loop(self, poll_interval: int = 10):
        """
        持续运行任务循环
        
        Args:
            poll_interval: 无任务时的轮询间隔（秒）
        """
        self._running = True
        print(f"[Worker-{self.worker_id}] 开始任务循环...")
        
        while self._running:
            try:
                has_task = self.run_once()
                
                if not has_task:
                    print(f"无待处理任务，等待 {poll_interval} 秒...")
                    time.sleep(poll_interval)
                else:
                    # 任务间隔
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n收到中断信号，停止...")
                break
            except Exception as e:
                print(f"循环异常: {e}")
                time.sleep(5)
        
        self.cleanup()
    
    def stop(self):
        """停止 Worker"""
        self._running = False
    
    def cleanup(self):
        """清理资源"""
        print(f"[Worker-{self.worker_id}] 清理中...")
        
        # 断开所有浏览器连接
        for shop_id, controller in self.active_browsers.items():
            try:
                controller.disconnect()
            except:
                pass
        
        # 关闭紫鸟客户端
        if self.ziniao:
            try:
                self.ziniao.exit_client()
            except:
                pass
        
        print(f"[Worker-{self.worker_id}] 清理完成")


def main():
    """主函数"""
    print("=" * 50)
    print("Shopee Agent Worker")
    print("=" * 50)
    print(f"可用 Actions: {list_available_actions()}")
    print()
    
    worker = Worker(worker_id="worker-01")
    
    if not worker.setup():
        print("Worker 初始化失败")
        return
    
    try:
        worker.run_loop(poll_interval=10)
    except KeyboardInterrupt:
        print("\n正在退出...")
    finally:
        worker.cleanup()


if __name__ == "__main__":
    main()
