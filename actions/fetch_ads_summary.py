"""
Action: fetch_ads_summary
获取广告汇总数据
"""
import time
import re
from typing import Dict, Any, Optional

from selenium.webdriver.common.by import By

from core.browser_controller import ActionResult
from actions.base_action import BaseAction, ActionContext


class FetchAdsSummaryAction(BaseAction):
    """获取广告汇总数据"""
    
    action_name = "fetch_ads_summary"
    
    def _do_action(self, context: ActionContext, payload: Dict[str, Any]) -> ActionResult:
        """
        获取广告中心的汇总数据
        
        payload 参数:
            date_range: 可选，"today" / "7days" / "30days"，默认 "today"
        """
        date_range = payload.get("date_range", "today")
        
        # 1. 导航到广告中心
        ads_url = self.locators.get("ads_center", {}).get("entry_url")
        if not ads_url:
            return ActionResult(
                ok=False,
                action=self.action_name,
                error_code="CONFIG_ERROR",
                error_message="广告中心 URL 未配置"
            )
        
        if not self.browser.navigate(ads_url, wait_seconds=5):
            return ActionResult(
                ok=False,
                action=self.action_name,
                error_code="NAVIGATION_ERROR",
                error_message=f"无法导航到: {ads_url}"
            )
        
        # 2. 选择日期范围（如果需要）
        self._select_date_range(date_range)
        
        # 3. 等待数据加载
        time.sleep(3)
        
        # 4. 提取数据
        data = self._extract_summary_data()
        
        if data:
            return ActionResult(
                ok=True,
                action=self.action_name,
                data={
                    "date_range": date_range,
                    "metrics": data
                }
            )
        else:
            return ActionResult(
                ok=False,
                action=self.action_name,
                error_code="DATA_EXTRACTION_ERROR",
                error_message="无法提取广告数据，可能页面结构已变化"
            )
    
    def _select_date_range(self, date_range: str):
        """选择日期范围"""
        date_picker_loc = self.loc("ads_center", "date_picker")
        if not date_picker_loc:
            return
        
        # 点击日期选择器
        if self.browser.wait_and_click(date_picker_loc, timeout=5):
            time.sleep(0.5)
            
            # 选择对应的日期范围
            range_key_map = {
                "today": "date_today",
                "7days": "date_7days",
                "30days": "date_30days"
            }
            
            range_loc = self.loc("ads_center", range_key_map.get(date_range, "date_today"))
            if range_loc:
                self.browser.wait_and_click(range_loc, timeout=5)
                time.sleep(2)  # 等待数据刷新
    
    def _extract_summary_data(self) -> Optional[Dict[str, Any]]:
        """提取汇总数据"""
        metrics = {}
        
        # 尝试提取各个指标
        fields = [
            ("spend", "total_spend"),
            ("impressions", "total_impressions"),
            ("clicks", "total_clicks"),
            ("orders", "total_orders"),
            ("roas", "roas"),
        ]
        
        for metric_name, locator_key in fields:
            loc = self.loc("ads_center", locator_key)
            if loc:
                text = self.browser.get_text(loc, timeout=5)
                if text:
                    metrics[metric_name] = self._parse_number(text)
        
        # 如果一个指标都没拿到，说明定位器可能都失效了
        if not metrics:
            # 尝试用更通用的方式获取
            metrics = self._extract_by_fallback()
        
        return metrics if metrics else None
    
    def _extract_by_fallback(self) -> Dict[str, Any]:
        """
        备用数据提取方式
        当主定位器失效时，尝试用更通用的方式
        """
        metrics = {}
        
        # 尝试获取页面上所有看起来像数值的元素
        # 这是一个兜底方案，实际使用中需要根据页面结构调整
        try:
            # 获取页面 HTML 进行分析（用于调试）
            page_source = self.browser.driver.page_source
            
            # 尝试匹配常见的数值模式
            # 例如：Rp 1.234.567 或 1,234 或 12.34%
            # 这里只是示例，实际需要根据 Shopee 页面调整
            
        except:
            pass
        
        return metrics
    
    def _parse_number(self, text: str) -> Any:
        """
        解析数字文本
        
        处理格式：
        - "Rp 1.234.567" → 1234567
        - "1,234" → 1234
        - "12.34%" → 12.34
        - "1.2K" → 1200
        """
        if not text:
            return None
        
        text = text.strip()
        
        # 移除货币符号
        text = re.sub(r'Rp\s*', '', text)
        text = re.sub(r'\$\s*', '', text)
        
        # 处理 K/M 后缀
        if text.endswith('K') or text.endswith('k'):
            text = text[:-1]
            try:
                return float(text.replace(',', '.')) * 1000
            except:
                pass
        
        if text.endswith('M') or text.endswith('m'):
            text = text[:-1]
            try:
                return float(text.replace(',', '.')) * 1000000
            except:
                pass
        
        # 处理百分比
        if text.endswith('%'):
            text = text[:-1]
            try:
                return float(text.replace(',', '.'))
            except:
                return text
        
        # 处理印尼格式数字 (1.234.567 → 1234567)
        if re.match(r'^[\d.]+$', text) and text.count('.') > 1:
            text = text.replace('.', '')
        
        # 处理英文格式数字 (1,234,567 → 1234567)
        text = text.replace(',', '')
        
        try:
            if '.' in text:
                return float(text)
            return int(text)
        except:
            return text
