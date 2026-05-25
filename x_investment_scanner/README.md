# X 投资信息扫描器（MVP 代码框架）

本项目是一个可扩展的 **X/Twitter 投资信息扫描器** 骨架，目标是：
- 监控高质量账号与关键词；
- 自动提取“资产/方向/逻辑/风险”；
- 使用你的投研框架做二次判断；
- 支持日总结与后续预警扩展。

---

## 1. 项目结构

```text
x_investment_scanner/
├── app/
│   ├── config.py                  # 统一参数中心（重点）
│   ├── database.py
│   ├── main.py
│   ├── ingestion/
│   │   ├── api_clients.py         # Magical / TwitterAPI.io / Desearch 适配层
│   │   ├── models.py              # 统一帖子与查询模型
│   │   ├── scanner.py             # 扫描主流程
│   │   ├── storage.py             # JSONL 轻量存储
│   │   └── workflows.py           # 实时、历史、候选账户流程
│   ├── processing/
│   │   └── relevance_filter.py    # 规则过滤
│   └── llm/
│       ├── classify_post.py       # 轻量分类
│       ├── extract_view.py        # 结构化提取
│       └── investment_judge.py    # 投研框架判断
├── scripts/
│   ├── run_scan.py                # 命令行测试脚本
│   ├── run_monitor.py             # 实时监控测试
│   ├── run_history_fetch.py       # 历史抓取测试
│   ├── run_candidate_accounts.py  # 潜在关注账户测试
│   └── run_ingestion_tests.py     # 类单元测试入口
├── tests/
│   └── test_ingestion_workflows.py
├── notebooks/
│   └── debug_pipeline.ipynb       # Jupyter 调试入口
└── requirements.txt
```

---

## 2. 你提出的 4 点要求对应说明

### 2.1 API 适配层
新增 `app/ingestion/api_clients.py`：
- `MagicalExportClient`：优先用于测试，读取 Magical/表格工具导出的 JSONL、JSON、CSV；
- `TwitterApiIOClient`：用于 TwitterAPI.io 高级搜索接口；
- `DesearchClient`：保留 Desearch 适配架构，端点可通过配置调整；
- `make_post_client()`：根据 `X_PROVIDER` 自动创建客户端。

项目内部统一使用 `SocialPost`，因此后续换 API 供应商时，主要只改适配层。

### 2.2 可变参数统一配置
全部集中在 `app/config.py`，包括：
- 数据库连接；
- API 提供商与密钥；
- Magical 导出文件路径；
- 结果 JSONL 存储路径；
- OpenAI 模型配置；
- 分层扫描频率与抓取上限；
- 关键词/cashtag/噪音词；
- 预警阈值和触发词。

> 日常只改 `app/config.py` 或环境变量即可。

### 2.3 关键代码中文注释
核心流程文件已加中文注释：
- `app/ingestion/scanner.py`
- `app/ingestion/api_clients.py`
- `app/ingestion/workflows.py`
- `app/processing/relevance_filter.py`
- `app/config.py`

### 2.4 Jupyter 可调试框架
提供 `notebooks/debug_pipeline.ipynb`：
- 可在 Notebook 中临时改参数；
- 可逐条构造 mock post 调试过滤与提取；
- 适合后续替换成真实 API 返回。

### 2.5 完整说明文档
即本 README，覆盖：架构、配置、运行方式、扩展点。

---

## 3. 快速开始

### 3.1 安装
```bash
cd x_investment_scanner
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3.2 配置
先修改 `app/config.py` 或设置环境变量（推荐）：
- `X_PROVIDER=magical_export`（默认，用于本地测试）
- `X_PROVIDER=twitterapi_io`（接 TwitterAPI.io）
- `X_PROVIDER=desearch`（接 Desearch）
- `X_MAGICAL_EXPORT_PATH=data/sample_exports/magical_posts.jsonl`
- `DB_URL`
- `X_API_KEY`
- `OPENAI_API_KEY`

### 3.3 运行命令行示例
```bash
PYTHONPATH=. python app/main.py
PYTHONPATH=. python scripts/run_scan.py
```

### 3.4 测试实时监控流功能
默认读取 `data/sample_exports/magical_posts.jsonl`，模拟 Magical 导出的帖子：
```bash
PYTHONPATH=. python scripts/run_monitor.py --keyword "AI infrastructure" --user macro_focus
```

持续轮询模拟实时流：
```bash
PYTHONPATH=. python scripts/run_monitor.py --loop --interval 60
```

输出会保存到：
```text
data/raw_posts/realtime/YYYY-MM-DD.jsonl
```

### 3.5 测试历史 post 抓取功能
```bash
PYTHONPATH=. python scripts/run_history_fetch.py \
  --start 2026-05-22T00:00:00+00:00 \
  --end 2026-05-25T00:00:00+00:00 \
  --keyword guidance
```

输出会保存到：
```text
data/raw_posts/history/YYYY-MM-DD.jsonl
```

### 3.6 测试潜在相关账户功能
```bash
PYTHONPATH=. python scripts/run_candidate_accounts.py --top-n 10
```

逻辑：
- 被当前关注用户多次 `@` 的账户加分；
- 被 repost 的账户权重更高；
- 被 quote 的账户权重居中；
- 已经在 `CONFIG.scan_policy.tracked_users` 中的账户不会重复推荐。

输出会保存到：
```text
data/candidate_accounts.json
```

### 3.7 运行类单元测试
```bash
PYTHONPATH=. python scripts/run_ingestion_tests.py
```

### 3.8 运行 Notebook
```bash
cd x_investment_scanner
jupyter notebook
```
打开 `notebooks/debug_pipeline.ipynb` 即可调试。

---

## 4. 当前实现边界（MVP）

当前是骨架实现，便于你快速落地：
- 已具备：API 适配层、实时监控测试、历史抓取测试、候选账户发现、三层过滤思路、结构化输出接口、配置中心；
- 未接入：真实 OpenAI API 请求、数据库 ORM 模型迁移、Telegram 推送；
- TwitterAPI.io/Desearch 已保留适配入口，真实运行前需要填入 API key，并按实际账号套餐确认端点与返回字段。

---

## 5. 下一步落地建议

1. **先接数据源**：在 `app/ingestion/scanner.py` 把 `fetch_new_posts` 替换为真实 API 客户端。  
2. **再接 LLM**：把 `llm/` 下桩函数改为真实 Responses API 调用，并固定 JSON Schema。  
3. **再接数据库**：补充 SQLAlchemy models 与 Alembic migration。  
4. **最后接推送**：基于 `AlertConfig` 增加 Telegram/邮箱 webhook。

---

## 6. 设计原则回顾

- **先过滤后推理**：节约 LLM 成本；
- **先结构化再总结**：避免“热帖罗列”；
- **以资产/主题为中心**：而不是按账号碎片阅读；
- **参数集中可控**：便于策略迭代与回测。
