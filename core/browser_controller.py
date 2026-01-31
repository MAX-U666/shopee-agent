"""
Selenium 浏览器控制器
负责：连接紫鸟浏览器、执行页面操作、截图取证
"""
import os
import time
from typing import Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config import agent_config


@dataclass
class ActionResult:
    """操作结果"""
    ok: bool
    action: str
    data: Optional[dict] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    evidence: Optional[dict] = None
    timing_ms: Optional[int] = None


class BrowserController:
    """浏览器控制器"""
    
    def __init__(
        self,
        debugging_port: int,
        core_version: str = "131",
        driver_path: Optional[str] = None
    ):
        """
        初始化浏览器控制器
        
        Args:
            debugging_port: 紫鸟返回的调试端口
            core_version: 内核版本（用于选择 ChromeDriver）
            driver_path: ChromeDriver 路径，不传则使用默认路径
        """
        self.debugging_port = debugging_port
        self.core_version = core_version
        self.driver_path = driver_path or self._get_default_driver_path()
        self.driver: Optional[webdriver.Chrome] = None
        self.config = agent_config
        
        # 确保证据目录存在
        os.makedirs(self.config.screenshot_dir, exist_ok=True)
    
    def _get_default_driver_path(self) -> str:
        """获取默认 ChromeDriver 路径"""
        # 根据操作系统和内核版本返回路径
        # 你需要把对应版本的 chromedriver 放到 drivers 目录
        import platform
        system = platform.system()
        
        if system == 'Windows':
            return f"./drivers/chromedriver_{self.core_version}.exe"
        else:
            return f"./drivers/chromedriver_{self.core_version}"
    
    def connect(self) -> bool:
        """连接到紫鸟浏览器"""
        try:
            options = Options()
            options.add_experimental_option(
                "debuggerAddress", 
                f"127.0.0.1:{self.debugging_port}"
            )
            
            # 如果有指定 driver 路径
            if self.driver_path and os.path.exists(self.driver_path):
                service = Service(self.driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                # 使用系统 PATH 中的 chromedriver
                self.driver = webdriver.Chrome(options=options)
            
            print(f"成功连接到浏览器，端口: {self.debugging_port}")
            return True
            
        except Exception as e:
            print(f"连接浏览器失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接（不关闭浏览器窗口）"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def navigate(self, url: str, wait_seconds: float = 3) -> bool:
        """导航到指定 URL"""
        try:
            self.driver.get(url)
            time.sleep(wait_seconds)
            return True
        except Exception as e:
            print(f"导航失败: {e}")
            return False
    
    def wait_for_element(
        self, 
        locator: Tuple[str, str], 
        timeout: int = 10
    ) -> Optional[any]:
        """
        等待元素出现
        
        Args:
            locator: (By.XXX, "selector") 格式
            timeout: 超时秒数
        
        Returns:
            WebElement 或 None
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return element
        except TimeoutException:
            return None
    
    def wait_and_click(
        self, 
        locator: Tuple[str, str], 
        timeout: int = 10
    ) -> bool:
        """等待元素可点击并点击"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            time.sleep(self.config.action_delay)
            element.click()
            return True
        except:
            return False
    
    def safe_send_keys(
        self, 
        locator: Tuple[str, str], 
        text: str,
        clear_first: bool = True,
        timeout: int = 10
    ) -> bool:
        """安全地输入文本"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            if clear_first:
                element.clear()
            time.sleep(self.config.action_delay)
            element.send_keys(text)
            return True
        except:
            return False
    
    def get_text(self, locator: Tuple[str, str], timeout: int = 10) -> Optional[str]:
        """获取元素文本"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return element.text
        except:
            return None
    
    def get_attribute(
        self, 
        locator: Tuple[str, str], 
        attr: str,
        timeout: int = 10
    ) -> Optional[str]:
        """获取元素属性"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return element.get_attribute(attr)
        except:
            return None
    
    def screenshot(self, name: str) -> str:
        """
        截图并保存
        
        Args:
            name: 截图名称（不含扩展名）
        
        Returns:
            截图文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = os.path.join(self.config.screenshot_dir, filename)
        
        self.driver.save_screenshot(filepath)
        return filepath
    
    def screenshot_evidence(self, run_id: str, stage: str) -> str:
        """
        为某次执行截取证据图
        
        Args:
            run_id: 执行ID
            stage: before / after / error
        
        Returns:
            截图路径
        """
        return self.screenshot(f"{run_id}_{stage}")
    
    def execute_script(self, script: str) -> any:
        """执行 JavaScript"""
        return self.driver.execute_script(script)
    
    def get_current_url(self) -> str:
        """获取当前 URL"""
        return self.driver.current_url
    
    def check_element_exists(self, locator: Tuple[str, str]) -> bool:
        """检查元素是否存在"""
        try:
            self.driver.find_element(*locator)
            return True
        except NoSuchElementException:
            return False
    
    def scroll_to_element(self, locator: Tuple[str, str]) -> bool:
        """滚动到元素位置"""
        try:
            element = self.driver.find_element(*locator)
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element
            )
            time.sleep(0.5)
            return True
        except:
            return False


def create_browser_controller(
    debugging_port: int,
    core_version: str = "131"
) -> BrowserController:
    """创建浏览器控制器的便捷函数"""
    return BrowserController(debugging_port, core_version)
