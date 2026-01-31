"""
Actions 模块
包含所有可执行的 Action
"""
from typing import Dict, Type

from actions.base_action import BaseAction, ActionContext
from actions.fetch_ads_summary import FetchAdsSummaryAction
from actions.update_title import UpdateTitleAction
from actions.fetch_product_snapshot import FetchProductSnapshotAction


# Action 注册表
ACTION_REGISTRY: Dict[str, Type[BaseAction]] = {
    "fetch_ads_summary": FetchAdsSummaryAction,
    "update_title": UpdateTitleAction,
    "fetch_product_snapshot": FetchProductSnapshotAction,
}


def get_action_class(action_name: str) -> Type[BaseAction]:
    """获取 Action 类"""
    if action_name not in ACTION_REGISTRY:
        raise ValueError(f"未知的 Action: {action_name}，可用: {list(ACTION_REGISTRY.keys())}")
    return ACTION_REGISTRY[action_name]


def list_available_actions() -> list:
    """列出所有可用的 Action"""
    return list(ACTION_REGISTRY.keys())


__all__ = [
    "BaseAction", "ActionContext",
    "FetchAdsSummaryAction", "UpdateTitleAction", "FetchProductSnapshotAction",
    "ACTION_REGISTRY", "get_action_class", "list_available_actions"
]
