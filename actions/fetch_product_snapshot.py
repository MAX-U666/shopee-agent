"""
Action: fetch_product_snapshot
获取商品快照（标题、价格、库存等）
"""
import time
from typing import Dict, Any, List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from core.browser_controller import ActionResult
from actions.base_action import BaseAction, ActionContext


class FetchProductSnapshotAction(BaseAction):
    """获取商品快照"""
    
    action_name = "fetch_product_snapshot"
    
    def _do_action(self, context: ActionContext, payload: Dict[str, Any]) -> ActionResult:
        """
        获取商品列表中商品的快照数据
        
        payload 参数:
            product_ids: 商品ID列表（可选）
            keyword: 搜索关键词（可选）
            limit: 最多获取多少个商品，默认 10
        """
        product_ids = payload.get("product_ids", [])
        keyword = payload.get("keyword", "")
        limit = payload.get("limit", 10)
        
        # 1. 导航到商品列表
        product_list_url = self.locators.get("product_list", {}).get("entry_url")
        if not self.browser.navigate(product_list_url, wait_seconds=5):
            return ActionResult(
                ok=False,
                action=self.action_name,
                error_code="NAVIGATION_ERROR",
                error_message="无法打开商品列表页"
            )
        
        # 2. 如果有关键词，先搜索
        if keyword:
            self._search_product(keyword)
        
        # 3. 提取商品数据
        products = self._extract_products(limit)
        
        if products:
            return ActionResult(
                ok=True,
                action=self.action_name,
                data={
                    "keyword": keyword,
                    "count": len(products),
                    "products": products
                }
            )
        else:
            return ActionResult(
                ok=False,
                action=self.action_name,
                error_code="NO_PRODUCTS",
                error_message="未找到任何商品"
            )
    
    def _search_product(self, keyword: str) -> bool:
        """搜索商品"""
        search_input_loc = self.loc("product_list", "search_input")
        
        if not search_input_loc:
            return False
        
        if not self.browser.safe_send_keys(search_input_loc, keyword, clear_first=True):
            return False
        
        # 按回车搜索
        element = self.browser.wait_for_element(search_input_loc, timeout=5)
        if element:
            element.send_keys(Keys.RETURN)
        
        time.sleep(3)
        return True
    
    def _extract_products(self, limit: int) -> List[Dict[str, Any]]:
        """提取商品列表数据"""
        products = []
        
        # 获取所有商品行
        product_row_loc = self.loc("product_list", "product_row")
        if not product_row_loc:
            # 尝试备用方案：直接获取表格行
            product_row_loc = (By.CSS_SELECTOR, "tr[data-product-id], .product-item")
        
        try:
            rows = self.browser.driver.find_elements(*product_row_loc)
            
            for i, row in enumerate(rows[:limit]):
                product = self._extract_product_from_row(row, i)
                if product:
                    products.append(product)
                    
        except Exception as e:
            print(f"提取商品数据异常: {e}")
        
        return products
    
    def _extract_product_from_row(self, row, index: int) -> Optional[Dict[str, Any]]:
        """从表格行提取单个商品数据"""
        try:
            product = {
                "index": index,
                "name": None,
                "sku": None,
                "price": None,
                "stock": None,
                "status": None
            }
            
            # 提取商品名称
            try:
                name_elem = row.find_element(By.CSS_SELECTOR, ".product-name, .product-title, td:nth-child(2)")
                product["name"] = name_elem.text.strip()
            except:
                pass
            
            # 提取 SKU
            try:
                sku_elem = row.find_element(By.CSS_SELECTOR, ".product-sku, .sku")
                product["sku"] = sku_elem.text.strip()
            except:
                pass
            
            # 提取价格
            try:
                price_elem = row.find_element(By.CSS_SELECTOR, ".product-price, .price")
                product["price"] = price_elem.text.strip()
            except:
                pass
            
            # 提取库存
            try:
                stock_elem = row.find_element(By.CSS_SELECTOR, ".product-stock, .stock")
                product["stock"] = stock_elem.text.strip()
            except:
                pass
            
            # 提取商品ID（从 data 属性）
            try:
                product["product_id"] = row.get_attribute("data-product-id")
            except:
                pass
            
            # 至少要有名称才算有效
            if product["name"]:
                return product
            
            return None
            
        except Exception as e:
            return None
