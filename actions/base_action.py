"""
Action 基类
所有具体 Action 都继承这个类
"""
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from core.browser_controller import BrowserController, ActionResult
from core.supabase_store import SupabaseStore, ArtifactType
from actions.locators import get_locators, parse_locator


@dataclass
class ActionContext:
    """Action 执行上下文"""
    task_id: str
    run_id: str
    shop_id: str
    site: str = "id"  # 站点代码
    dry_run: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseAction(ABC):
    """Action 基类"""
    
    # 子类需要定义 action 名称
    action_name: str = "base"
    
    def __init__(
        self,
        browser: BrowserController,
        store: Optional[SupabaseStore] = None
    ):
        self.browser = browser
        self.store = store
        self.locators = {}
        self.start_time = 0
    
    def set_site(self, site: str):
        """设置站点，加载对应的定位器"""
        self.locators = get_locators(site)
    
    def loc(self, *keys) -> tuple:
        """
        获取定位器
        
        用法：
            self.loc("product_edit", "title_input")
            → 返回 (By.CSS_SELECTOR, "input[name='name']")
        """
        config = self.locators
        for key in keys:
            config = config.get(key, {})
        
        if isinstance(config, str):
            return parse_locator(config)
        return None
    
    def execute(self, context: ActionContext, payload: Dict[str, Any]) -> ActionResult:
        """
        执行 Action（模板方法）
        
        子类不要覆盖这个方法，而是实现 _do_action
        """
        self.start_time = time.time()
        self.set_site(context.site)
        
        # 截图：执行前
        before_screenshot = None
        if self.store:
            before_screenshot = self.browser.screenshot_evidence(context.run_id, "before")
            self.store.save_artifact_record(
                context.run_id, 
                ArtifactType.BEFORE, 
                before_screenshot
            )
        
        try:
            # 执行具体动作
            result = self._do_action(context, payload)
            
            # 截图：执行后
            if self.store and result.ok:
                after_screenshot = self.browser.screenshot_evidence(context.run_id, "after")
                self.store.save_artifact_record(
                    context.run_id,
                    ArtifactType.AFTER,
                    after_screenshot
                )
                result.evidence = {
                    "before_png": before_screenshot,
                    "after_png": after_screenshot
                }
            
            # 计算耗时
            result.timing_ms = int((time.time() - self.start_time) * 1000)
            return result
            
        except Exception as e:
            # 截图：错误
            error_screenshot = None
            if self.store:
                error_screenshot = self.browser.screenshot_evidence(context.run_id, "error")
                self.store.save_artifact_record(
                    context.run_id,
                    ArtifactType.ERROR,
                    error_screenshot
                )
            
            return ActionResult(
                ok=False,
                action=self.action_name,
                error_code="EXCEPTION",
                error_message=str(e),
                evidence={"error_png": error_screenshot} if error_screenshot else None,
                timing_ms=int((time.time() - self.start_time) * 1000)
            )
    
    @abstractmethod
    def _do_action(self, context: ActionContext, payload: Dict[str, Any]) -> ActionResult:
        """
        执行具体动作（子类实现）
        
        Args:
            context: 执行上下文
            payload: 任务参数
        
        Returns:
            ActionResult
        """
        pass
    
    def _validate_payload(self, payload: Dict[str, Any], required_fields: list) -> Optional[str]:
        """验证 payload 是否包含必需字段"""
        for field in required_fields:
            if field not in payload:
                return f"缺少必需字段: {field}"
        return None
