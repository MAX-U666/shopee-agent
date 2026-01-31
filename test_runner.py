"""
测试脚本
用于验证各模块是否正常工作
"""
import json
import time
from typing import Optional

from config import ziniao_config, supabase_config


def test_ziniao_connection():
    """测试紫鸟连接"""
    print("\n=== 测试紫鸟连接 ===")
    
    from core.ziniao_client import get_ziniao_client
    
    client = get_ziniao_client()
    
    # 1. 启动客户端
    print("1. 启动紫鸟客户端...")
    if not client.start_client():
        print("   ✗ 启动失败")
        print(f"   请检查客户端路径: {ziniao_config.client_path}")
        return False
    print("   ✓ 启动成功")
    
    # 2. 获取店铺列表
    print("2. 获取店铺列表...")
    browsers = client.get_browser_list()
    if not browsers:
        print("   ✗ 获取失败或无店铺")
        print("   请检查账号信息是否正确")
        return False
    
    print(f"   ✓ 找到 {len(browsers)} 个店铺:")
    for b in browsers:
        print(f"      - {b.browser_name} (ID: {b.browser_id}, 平台: {b.platform_name})")
    
    # 3. 启动第一个店铺的浏览器
    if browsers:
        print(f"3. 启动店铺浏览器: {browsers[0].browser_name}...")
        result = client.start_browser(browsers[0].browser_id)
        
        if result.success:
            print(f"   ✓ 启动成功")
            print(f"      调试端口: {result.debugging_port}")
            print(f"      内核: {result.core_type} {result.core_version}")
            
            # 返回信息供后续测试使用
            return {
                "debugging_port": result.debugging_port,
                "core_version": result.core_version,
                "browser_id": browsers[0].browser_id
            }
        else:
            print(f"   ✗ 启动失败: {result.error}")
            return False
    
    return True


def test_browser_controller(debugging_port: int, core_version: str):
    """测试浏览器控制器"""
    print("\n=== 测试浏览器控制器 ===")
    
    from core.browser_controller import create_browser_controller
    
    # 1. 连接浏览器
    print(f"1. 连接浏览器 (端口: {debugging_port})...")
    controller = create_browser_controller(
        debugging_port=debugging_port,
        core_version=core_version.split('.')[0]
    )
    
    if not controller.connect():
        print("   ✗ 连接失败")
        print("   请确保 ChromeDriver 版本与内核匹配")
        return False
    print("   ✓ 连接成功")
    
    # 2. 获取当前 URL
    print("2. 获取当前 URL...")
    url = controller.get_current_url()
    print(f"   当前页面: {url}")
    
    # 3. 截图测试
    print("3. 截图测试...")
    screenshot_path = controller.screenshot("test")
    print(f"   ✓ 截图保存至: {screenshot_path}")
    
    # 4. 导航测试
    print("4. 导航测试 (Google)...")
    if controller.navigate("https://www.google.com", wait_seconds=3):
        print(f"   ✓ 导航成功，当前: {controller.get_current_url()}")
    else:
        print("   ✗ 导航失败")
    
    return True


def test_supabase_connection():
    """测试 Supabase 连接"""
    print("\n=== 测试 Supabase 连接 ===")
    
    try:
        from core.supabase_store import get_store, TaskStatus
        
        store = get_store()
        
        # 1. 测试连接
        print("1. 连接 Supabase...")
        count = store.get_pending_tasks_count()
        print(f"   ✓ 连接成功，当前待处理任务: {count}")
        
        # 2. 测试创建任务
        print("2. 创建测试任务...")
        task_id = store.create_task(
            shop_id="test_shop",
            action="fetch_product_snapshot",
            payload={"keyword": "test", "limit": 5},
            priority=1,
            dry_run=True
        )
        print(f"   ✓ 任务创建成功: {task_id}")
        
        # 3. 测试获取任务
        print("3. 获取任务...")
        task = store.get_task(task_id)
        if task:
            print(f"   ✓ 获取成功: {task['action']}")
        else:
            print("   ✗ 获取失败")
        
        # 4. 清理测试任务
        print("4. 清理测试任务...")
        store.update_task_status(task_id, TaskStatus.SUCCESS)
        print("   ✓ 清理完成")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 异常: {e}")
        print(f"   请检查 Supabase 配置:")
        print(f"      URL: {supabase_config.url}")
        print(f"      Key: {supabase_config.key[:20]}...")
        return False


def test_action_execution(debugging_port: int, core_version: str):
    """测试 Action 执行"""
    print("\n=== 测试 Action 执行 ===")
    
    from core.browser_controller import create_browser_controller
    from actions import get_action_class, ActionContext
    
    # 连接浏览器
    controller = create_browser_controller(
        debugging_port=debugging_port,
        core_version=core_version.split('.')[0]
    )
    
    if not controller.connect():
        print("连接浏览器失败")
        return False
    
    # 执行 fetch_product_snapshot (只读操作，相对安全)
    print("执行 fetch_product_snapshot...")
    
    action_class = get_action_class("fetch_product_snapshot")
    action = action_class(controller, store=None)
    
    context = ActionContext(
        task_id="test_001",
        run_id="run_001",
        shop_id="test_shop",
        site="id",
        dry_run=True
    )
    
    result = action.execute(context, {
        "keyword": "",
        "limit": 3
    })
    
    print(f"执行结果: {'成功' if result.ok else '失败'}")
    if result.ok:
        print(f"数据: {json.dumps(result.data, ensure_ascii=False, indent=2)[:500]}...")
    else:
        print(f"错误: {result.error_code} - {result.error_message}")
    
    return result.ok


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Shopee Agent 测试")
    print("=" * 60)
    
    # 测试紫鸟
    ziniao_result = test_ziniao_connection()
    
    if isinstance(ziniao_result, dict):
        # 紫鸟连接成功，继续测试浏览器
        test_browser_controller(
            ziniao_result["debugging_port"],
            ziniao_result["core_version"]
        )
        
        # 测试 Action
        # test_action_execution(
        #     ziniao_result["debugging_port"],
        #     ziniao_result["core_version"]
        # )
    
    # 测试 Supabase（独立测试）
    test_supabase_connection()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
