"""扫描主流程。"""

from datetime import datetime
from app.config import CONFIG
from app.processing.relevance_filter import rule_based_filter
from app.llm.classify_post import classify_post_quick
from app.llm.extract_view import extract_investment_view
from app.llm.investment_judge import judge_by_framework


def fetch_new_posts(account: dict):
    """模拟抓取新增帖子。

    实际项目中请替换为官方 API 或第三方 API 调用。
    """
    return account.get("mock_posts", [])


def run_scan_cycle(accounts: list[dict]):
    """执行一轮扫描。

    关键逻辑：
    1. 按账号抓取新增内容
    2. 规则过滤
    3. LLM 轻量分类
    4. LLM 深度提取
    5. 投研框架二次判断
    """
    results = []

    for account in accounts:
        posts = fetch_new_posts(account)

        for post in posts:
            text = post.get("text", "")

            # 第一层：规则过滤（节省 LLM 成本）
            if not rule_based_filter(text, CONFIG.filter):
                continue

            # 第二层：轻量分类
            quick = classify_post_quick(text)
            if quick.get("priority") == "low":
                continue

            # 第三层：深度结构化提取
            extracted = extract_investment_view(text)

            # 第四层：按你的投研框架做二次判断
            judged = judge_by_framework(extracted)

            results.append(
                {
                    "account": account.get("username"),
                    "post_id": post.get("id"),
                    "extracted": extracted,
                    "judged": judged,
                    "processed_at": datetime.utcnow().isoformat(),
                }
            )

    return results
