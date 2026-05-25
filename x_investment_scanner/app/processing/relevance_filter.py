"""规则过滤器。"""


def rule_based_filter(text: str, cfg) -> bool:
    """根据关键词和排除词进行初筛。"""
    lower_text = text.lower()

    # 噪音词命中直接过滤
    for drop_kw in cfg.drop_keywords:
        if drop_kw.lower() in lower_text:
            return False

    # 有 cashtag 或关键词才保留
    has_cashtag = any(tag.lower() in lower_text for tag in cfg.cashtags)
    has_keyword = any(kw.lower() in lower_text for kw in cfg.keywords)
    return has_cashtag or has_keyword
