"""
Action: update_title
更新商品标题
"""
import time
from typing import Dict, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from core.browser_controller import ActionResult
from actions.base_action import BaseAction, ActionContext


class UpdateTitleAction(BaseAction):
    """更新商品标题"""
    
    action_name = "update_title"
    
    def _do_action(self, context: ActionContext, payload: Dict[str, Any]) -> ActionResult:
        """
        更新指定商品的标题
        
        payload 参数:
            product_id: 商品ID（必需）
            new_title: 新标题（必需）
            product_name: 商品名称（可选，用于搜索）
        """
        # 验证参数
        validation_error = self._validate_payload(payload, ["product_id", "new_title"])
        if validation_error:
            return ActionResult(
                ok=False,
                action=self.action_name,
                error_code="VALIDATION_ERROR",
                error_message=validation_error
            )
        
        product_id = payload["product_id"]
        new_title = payload["new_title"]
        product_name = payload.get("product_name", product_id)
        
        # dry_run 模式：不实际执行
        if context.dry_run:
            return ActionResult(
                ok=True,
                action=self.action_name,
                data={
                    "product_id": product_id,
                    "new_title": new_title,
                    "dry_run": True,
                    "message": "Dry run 模式，未实际执行"
                }
            )
        
        # 1. 导航到商品列表
        product_list_url = self.locators.get("product_list", {}).get("entry_url")
        if not self.browser.navigate(product_list_url, wait_seconds=5):
            return ActionResult(
                ok=False,
                action=self.action_name,
                error_code="NAVIGATION_ERROR",
                error_message="无法打开商品列表页"
            )
        
        # 2. 搜索商品
        if not self._search_product(product_name):
            return ActionResult(
                ok=False,
                action=self.action_name,
                error_code="SEARCH_ERROR",
                error_message=f"搜索商品失败: {product_name}"
            )
        
        # 3. 找到并点击编辑按钮
        old_title = self._click_edit_button()
        if old_title is None:
            return ActionResult(
                ok=False,
                action=self.action_name,
                error_code="PRODUCT_NOT_FOUND",
                error_message=f"未找到商品或无法点击编辑: {product_id}"
            )
        
        # 4. 修改标题
        if not self._update_title_field(new_title):
            return ActionResult(
                ok=False,
                action=self.action_name,
                error_code="UPDATE_ERROR",
                error_message="无法修改标题字段"
            )
        
        # 5. 保存
        save_result = self._click_save()
        if not save_result["success"]:
            return ActionResult(
                ok=False,
                action=self.action_name,
                error_code="SAVE_ERROR",
                error_message=save_result.get("message", "保存失败")
            )
        
        return ActionResult(
            ok=True,
            action=self.action_name,
            data={
                "product_id": product_id,
                "before_title": old_title,
                "after_title": new_title
            }
        )
    
    def _search_product(self, keyword: str) -> bool:
        """在商品列表中搜索"""
        search_input_loc = self.loc("product_list", "search_input")
        search_btn_loc = self.loc("product_list", "search_button")
        
        if not search_input_loc:
            return False
        
        # 输入搜索关键词
        if not self.browser.safe_send_keys(search_input_loc, keyword, clear_first=True):
            return False
        
        time.sleep(0.5)
        
        # 点击搜索按钮或按回车
        if search_btn_loc:
            self.browser.wait_and_click(search_btn_loc, timeout=5)
        else:
            # 按回车搜索
            element = self.browser.wait_for_element(search_input_loc, timeout=5)
            if element:
                element.send_keys(Keys.RETURN)
        
        # 等待搜索结果
        time.sleep(3)
        return True
    
    def _click_edit_button(self) -> str:
        """
        点击第一个商品的编辑按钮
        
        Returns:
            原标题（如果成功），None（如果失败）
        """
        # 先获取当前标题
        product_name_loc = self.loc("product_list", "product_name")
        old_title = None
        if product_name_loc:
            old_title = self.browser.get_text(product_name_loc, timeout=5)
        
        # 点击编辑按钮
        edit_btn_loc = self.loc("product_list", "edit_btn")
        if not edit_btn_loc:
            return None
        
        if not self.browser.wait_and_click(edit_btn_loc, timeout=10):
            return None
        
        # 等待编辑页面加载
        time.sleep(3)
        
        return old_title or "[未获取到原标题]"
    
    def _update_title_field(self, new_title: str) -> bool:
        """修改标题字段"""
        title_input_loc = self.loc("product_edit", "title_input")
        if not title_input_loc:
            return False
        
        # 等待标题输入框出现
        element = self.browser.wait_for_element(title_input_loc, timeout=10)
        if not element:
            return False
        
        # 滚动到元素位置
        self.browser.scroll_to_element(title_input_loc)
        time.sleep(0.5)
        
        # 清空并输入新标题
        # 使用 JavaScript 来清空，更可靠
        self.browser.execute_script(
            "arguments[0].value = '';",
            element
        )
        time.sleep(0.3)
        
        # 输入新标题
        element.send_keys(new_title)
        time.sleep(0.5)
        
        # 触发 input 事件（有些前端框架需要）
        self.browser.execute_script(
            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
            element
        )
        
        return True
    
    def _click_save(self) -> Dict[str, Any]:
        """点击保存按钮"""
        save_btn_loc = self.loc("product_edit", "save_btn")
        if not save_btn_loc:
            return {"success": False, "message": "保存按钮定位器未配置"}
        
        # 滚动到页面底部（保存按钮通常在底部）
        self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)
        
        # 点击保存
        if not self.browser.wait_and_click(save_btn_loc, timeout=10):
            return {"success": False, "message": "无法点击保存按钮"}
        
        # 等待保存完成
        time.sleep(3)
        
        # 检查是否有成功提示
        success_toast_loc = self.loc("product_edit", "success_toast")
        error_toast_loc = self.loc("product_edit", "error_toast")
        
        if success_toast_loc and self.browser.check_element_exists(success_toast_loc):
            return {"success": True, "message": "保存成功"}
        
        if error_toast_loc and self.browser.check_element_exists(error_toast_loc):
            error_text = self.browser.get_text(error_toast_loc, timeout=2)
            return {"success": False, "message": f"保存失败: {error_text}"}
        
        # 没有明确的成功/失败提示，假设成功
        return {"success": True, "message": "保存完成（未检测到明确提示）"}
