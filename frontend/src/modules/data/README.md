# 数据管理（任务 1）

`/data` 支持同步最新 hub-stats 模型快照，也保留本地 Parquet 和样例导入入口。页面展示快照范围、原始提交、数据统计和导入记录。

- 同步使用 `POST /api/hubstats/sync`，也可以从后端运行 `python -m scripts.sync_hubstats`。
- 每份快照有独立 ID，可用作谱系、证据和差分的版本锚点。导入只写声明边（`is_baseline = 1`）。
- 接口见 `docs/CONTRACTS.md`，测试位于 `tests/catalog/`。
