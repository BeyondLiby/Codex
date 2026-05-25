"""按投研框架做二次判断（示例桩函数）。"""


def judge_by_framework(extracted: dict) -> dict:
    """二次判断：输出动作建议。"""
    return {
        "logic_quality": "medium",
        "market_is_trading": "事件驱动叙事",
        "action": "watch",
        "final_view": "建议先观察并补充验证数据（财报/指引/融资）。",
    }
