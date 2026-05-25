"""轻量分类（示例桩函数）。"""


def classify_post_quick(text: str) -> dict:
    """快速判断是否值得深度分析。

    真实环境请接入 OpenAI Responses API。
    """
    important_words = ["guidance", "offering", "acquisition", "earnings", "$"]
    if any(w in text.lower() for w in important_words):
        return {"is_investment_relevant": True, "priority": "high"}
    return {"is_investment_relevant": True, "priority": "medium"}
