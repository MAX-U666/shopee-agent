"""
紫鸟浏览器客户端连接模块
负责：启动紫鸟、调用 API、获取 debuggingPort
"""
import subprocess
import platform
import time
import requests
import traceback
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from config import ziniao_config


@dataclass
class BrowserInfo:
    """店铺浏览器信息"""
    browser_oauth: str  # 加密店铺ID
    browser_id: str     # 数字店铺ID
    browser_name: str   # 店铺名称
    site_id: str        # 站点
    platform_name: str  # 平台名称
    is_expired: bool    # IP是否过期


@dataclass
class StartBrowserResult:
    """启动浏览器返回结果"""
    success: bool
    debugging_port: Optional[int] = None
    core_type: Optional[str] = None
    core_version: Optional[str] = None
    download_path: Optional[str] = None
    error: Optional[str] = None


class ZiNiaoClient:
    """紫鸟客户端控制器"""
    
    def __init__(self, config=None):
        self.config = config or ziniao_config
        self.base_url = f"http://127.0.0.1:{self.config.socket_port}"
        self._process = None
    
    def start_client(self) -> bool:
        """启动紫鸟客户端主进程"""
        try:
            system = platform.system()
            
            if system == 'Windows':
                cmd = [
                    self.config.client_path,
                    '--run_type=web_driver',
                    '--ipc_type=http',
                    f'--port={self.config.socket_port}'
                ]
            elif system == 'Darwin':  # macOS
                cmd = [
                    'open', '-a', self.config.client_path,
                    '--args',
                    '--run_type=web_driver',
                    '--ipc_type=http',
                    f'--port={self.config.socket_port}'
                ]
            elif system == 'Linux':
                cmd = [
                    self.config.client_path,
                    '--no-sandbox',
                    '--run_type=web_driver',
                    '--ipc_type=http',
                    f'--port={self.config.socket_port}'
                ]
            else:
                print(f"不支持的操作系统: {system}")
                return False
            
            print(f"启动紫鸟客户端: {' '.join(cmd)}")
            self._process = subprocess.Popen(cmd)
            
            # 等待客户端启动
            time.sleep(5)
            
            # 验证是否启动成功
            if self._is_client_running():
                print("紫鸟客户端启动成功")
                return True
            else:
                print("紫鸟客户端启动失败")
                return False
                
        except Exception as e:
            print(f"启动紫鸟客户端异常: {traceback.format_exc()}")
            return False
    
    def _is_client_running(self) -> bool:
        """检查客户端是否在运行"""
        try:
            # 尝试调用一个简单的 API 来验证
            response = requests.post(
                self.base_url,
                json={"action": "getRunningInfo", "requestId": "health_check"},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def _call_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """调用紫鸟 API"""
        # 自动添加认证信息
        payload.update({
            "company": self.config.company,
            "username": self.config.username,
            "password": self.config.password,
        })
        
        response = requests.post(
            self.base_url,
            json=payload,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def apply_auth(self) -> bool:
        """申请设备授权（首次使用时需要）"""
        try:
            result = self._call_api({
                "action": "applyAuth",
                "requestId": f"auth_{int(time.time())}"
            })
            
            if result.get("statusCode") == 0:
                print("设备授权成功")
                return True
            else:
                print(f"设备授权失败: {result.get('err')}")
                return False
        except Exception as e:
            print(f"设备授权异常: {e}")
            return False
    
    def get_browser_list(self) -> List[BrowserInfo]:
        """获取店铺列表"""
        try:
            result = self._call_api({
                "action": "getBrowserList",
                "requestId": f"list_{int(time.time())}"
            })
            
            if result.get("statusCode") != 0:
                print(f"获取店铺列表失败: {result.get('err')}")
                return []
            
            browsers = []
            for item in result.get("browserList", []):
                browsers.append(BrowserInfo(
                    browser_oauth=item.get("browserOauth", ""),
                    browser_id=str(item.get("browserId", item.get("browserOauth", ""))),
                    browser_name=item.get("browserName", ""),
                    site_id=item.get("siteId", ""),
                    platform_name=item.get("platform_name", ""),
                    is_expired=item.get("isExpired", False)
                ))
            
            return browsers
            
        except Exception as e:
            print(f"获取店铺列表异常: {e}")
            return []
    
    def start_browser(
        self, 
        browser_id: str,
        headless: bool = False,
        download_path: Optional[str] = None
    ) -> StartBrowserResult:
        """
        启动指定店铺的浏览器
        
        Args:
            browser_id: 店铺ID
            headless: 是否无头模式
            download_path: 文件下载路径
        
        Returns:
            StartBrowserResult: 包含 debugging_port 等信息
        """
        try:
            payload = {
                "action": "startBrowser",
                "browserId": browser_id,
                "isHeadless": headless,
                "requestId": f"start_{browser_id}_{int(time.time())}"
            }
            
            if download_path:
                payload["forceDownloadPath"] = download_path
            
            result = self._call_api(payload)
            
            if result.get("statusCode") == 0:
                return StartBrowserResult(
                    success=True,
                    debugging_port=int(result.get("debuggingPort")),
                    core_type=result.get("core_type") or result.get("coreType"),
                    core_version=result.get("core_version") or result.get("coreVersion"),
                    download_path=result.get("downloadPath")
                )
            else:
                return StartBrowserResult(
                    success=False,
                    error=result.get("err") or result.get("LastError") or f"状态码: {result.get('statusCode')}"
                )
                
        except Exception as e:
            return StartBrowserResult(
                success=False,
                error=str(e)
            )
    
    def stop_browser(self, browser_id: str) -> bool:
        """关闭指定店铺的浏览器"""
        try:
            result = self._call_api({
                "action": "stopBrowser",
                "browserId": browser_id,
                "requestId": f"stop_{browser_id}_{int(time.time())}"
            })
            
            return result.get("statusCode") == 0
            
        except Exception as e:
            print(f"关闭浏览器异常: {e}")
            return False
    
    def get_running_info(self) -> List[Dict]:
        """获取当前运行中的店铺"""
        try:
            result = self._call_api({
                "action": "getRunningInfo",
                "requestId": f"running_{int(time.time())}"
            })
            return result.get("browsers", [])
        except:
            return []
    
    def exit_client(self) -> bool:
        """退出紫鸟客户端"""
        try:
            result = self._call_api({
                "action": "exit",
                "requestId": f"exit_{int(time.time())}"
            })
            return result.get("statusCode") == 0
        except:
            return False


# 便捷函数
def get_ziniao_client() -> ZiNiaoClient:
    """获取紫鸟客户端实例"""
    return ZiNiaoClient()
