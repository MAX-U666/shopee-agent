"""
Shopee Seller Center 页面定位器配置
=================================

这是你的"护城河"之一：规则化定位
Shopee 改 UI 时，只需要更新这里的选择器

定位器格式说明：
- css: xxx     → By.CSS_SELECTOR
- xpath: xxx   → By.XPATH
- id: xxx      → By.ID
- name: xxx    → By.NAME

注意：这些选择器基于印尼站（seller.shopee.co.id）
其他站点可能需要调整
"""

# Shopee 印尼站 Seller Center
SHOPEE_ID = {
    # ==================== 通用 ====================
    "base_url": "https://seller.shopee.co.id",
    "login_url": "https://seller.shopee.co.id/account/signin",
    
    # 登录状态检测
    "login_check": {
        "logged_in": "css:.navbar-username",  # 已登录时显示用户名
        "login_form": "css:input[name='loginKey']",  # 登录表单
    },
    
    # ==================== 广告中心（GMV MAX / 商品广告）====================
    "ads_center": {
        "entry_url": "https://seller.shopee.co.id/portal/marketing/pas/assembly",
        
        # 广告汇总数据（根据实际页面调整）
        "summary_section": "css:.ads-summary, .marketing-summary",
        "total_spend": "css:[data-testid='total-spend'], .spend-value",
        "total_impressions": "css:[data-testid='impressions'], .impressions-value",
        "total_clicks": "css:[data-testid='clicks'], .clicks-value",
        "total_orders": "css:[data-testid='orders'], .orders-value",
        "roas": "css:[data-testid='roas'], .roas-value",
        
        # 日期选择器
        "date_picker": "css:.date-range-picker, [data-testid='date-picker']",
        "date_today": "css:button:has-text('Hari ini'), button:has-text('Today')",
        "date_7days": "css:button:has-text('7 hari'), button:has-text('7 days')",
        "date_30days": "css:button:has-text('30 hari'), button:has-text('30 days')",
    },
    
    # ==================== 商品管理 ====================
    "product_list": {
        "entry_url": "https://seller.shopee.co.id/portal/product/list/all",
        
        # 搜索
        "search_input": "css:input[placeholder*='Cari'], input[placeholder*='Search']",
        "search_button": "css:button[type='submit'], .search-btn",
        
        # 商品列表
        "product_table": "css:.product-table, table",
        "product_row": "css:.product-row, tr.product-item",
        "product_name": "css:.product-name, .product-title",
        "product_sku": "css:.product-sku",
        "product_price": "css:.product-price",
        "product_stock": "css:.product-stock",
        
        # 操作按钮
        "edit_btn": "css:button:has-text('Ubah'), button:has-text('Edit')",
        "more_actions_btn": "css:.more-actions, .dropdown-toggle",
    },
    
    # ==================== 商品编辑 ====================
    "product_edit": {
        # 基本信息
        "title_input": "css:input[name='name'], input[placeholder*='Nama produk'], textarea[name='name']",
        "description_textarea": "css:textarea[name='description'], .product-description textarea",
        
        # 价格库存
        "price_input": "css:input[name='price'], input[type='number'][placeholder*='Harga']",
        "stock_input": "css:input[name='stock'], input[type='number'][placeholder*='Stok']",
        "sku_input": "css:input[name='sku']",
        
        # 保存
        "save_btn": "css:button:has-text('Simpan'), button:has-text('Save'), button[type='submit']",
        "save_and_publish_btn": "css:button:has-text('Simpan & Tampilkan')",
        "cancel_btn": "css:button:has-text('Batal'), button:has-text('Cancel')",
        
        # 成功提示
        "success_toast": "css:.toast-success, [role='alert']:has-text('Berhasil'), .ant-message-success",
        "error_toast": "css:.toast-error, [role='alert']:has-text('Gagal'), .ant-message-error",
    },
    
    # ==================== 订单管理 ====================
    "order_list": {
        "entry_url": "https://seller.shopee.co.id/portal/sale/order",
        
        # 订单状态 Tab
        "tab_all": "css:[data-tab='all']",
        "tab_pending": "css:[data-tab='toship']",
        "tab_shipping": "css:[data-tab='shipping']",
        "tab_completed": "css:[data-tab='completed']",
        
        # 订单列表
        "order_table": "css:.order-table, table",
        "order_row": "css:.order-row, tr.order-item",
        "order_id": "css:.order-id",
        "order_status": "css:.order-status",
        "order_total": "css:.order-total",
    },
}


# 你可以添加其他站点的配置
SHOPEE_MY = {
    "base_url": "https://seller.shopee.com.my",
    # ... 马来西亚站点配置
}

SHOPEE_TH = {
    "base_url": "https://seller.shopee.co.th",
    # ... 泰国站点配置
}

SHOPEE_VN = {
    "base_url": "https://banhang.shopee.vn",
    # ... 越南站点配置
}

SHOPEE_PH = {
    "base_url": "https://seller.shopee.ph",
    # ... 菲律宾站点配置
}

SHOPEE_SG = {
    "base_url": "https://seller.shopee.sg",
    # ... 新加坡站点配置
}


def get_locators(site: str = "id") -> dict:
    """
    获取指定站点的定位器配置
    
    Args:
        site: 站点代码 (id/my/th/vn/ph/sg)
    """
    sites = {
        "id": SHOPEE_ID,
        "my": SHOPEE_MY,
        "th": SHOPEE_TH,
        "vn": SHOPEE_VN,
        "ph": SHOPEE_PH,
        "sg": SHOPEE_SG,
    }
    return sites.get(site, SHOPEE_ID)


def parse_locator(locator_str: str) -> tuple:
    """
    解析定位器字符串为 Selenium 格式
    
    Args:
        locator_str: "css:.class" 或 "xpath://div" 等
    
    Returns:
        (By.XXX, "selector")
    """
    from selenium.webdriver.common.by import By
    
    if locator_str.startswith("css:"):
        return (By.CSS_SELECTOR, locator_str[4:])
    elif locator_str.startswith("xpath:"):
        return (By.XPATH, locator_str[6:])
    elif locator_str.startswith("id:"):
        return (By.ID, locator_str[3:])
    elif locator_str.startswith("name:"):
        return (By.NAME, locator_str[5:])
    else:
        # 默认当作 CSS 选择器
        return (By.CSS_SELECTOR, locator_str)
