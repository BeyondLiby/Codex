"""结构化提取（示例桩函数）。"""


def extract_investment_view(text: str) -> dict:
    """将文本抽取为结构化投资观点。"""
    return {
        "assets": [
            {
                "ticker": "UNKNOWN",
                "direction": "unclear",
                "core_thesis": text[:120],
                "risk": "需要结合财报与融资情况验证",
                "confidence": 0.5,
            }
        ]
    }
