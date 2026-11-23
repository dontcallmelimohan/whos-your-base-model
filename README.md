# AI 模型供应链交互与分析平台

课程大作业（北航 · 开源软件开发导论）。浏览器里查看 Hugging Face 模型的上游与下游、证据来源，以及整个生态的分布。

数据来自 hub-stats 每日 dump（约 326 万个模型、97 万条 `base_model` 父链接），字段口径与布局参考 [model-family-tree](https://github.com/h9-tec/model-family-tree)。

## 模块与状态

| 工作包 | 内容 | 负责人 | 状态 |
|---|---|---|---|
| **1** | 模型目录与数据（`/catalog`、`/data`） | 李默涵 | 可用 |
| **2** | 谱系探索与可视化（`/lineage`） | 待认领 | 可用，含声明图 / 补全图切换 |
| **3** | 依赖发现与证据核验（`/evidence`） | 待认领 | 可用，抽取 → 证据 → 核验闭环 |
| **4** | 生态分析与导出（`/analysis`） | 待认领 | 可用，含补全前后对比与 CSV |


占位页上写着“接入方式”，认领者按那三步接进来即可。

## 快速开始

### 1. 后端

```bash
# 在仓库根目录
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt

cd backend
python -m scripts.seed                       # 样例数据（秒级，够开发）
# 或真实数据（需要仓库外的 models.parquet）：
# python -m scripts.seed --source hubstats --limit 20000

uvicorn app:app --reload --port 8000
```

打开 <http://127.0.0.1:8000/docs> 看接口文档。

### 2. 前端

```bash
cd frontend
npm install
npm run dev        # http://127.0.0.1:5173，/api 自动代理到 8000
```

### 3. 单进程演示版（断网可用）

```bash
cd frontend && npm run build
cd backend && uvicorn app:app --port 8000
```

后端会自动托管 `frontend/dist`，一个地址即可演示。

## 目录

```text
backend/
  app.py                  只注册路由
  shared/                 冻结契约：contracts / db / errors / config / migrations
  modules/
    data/                 A：导入、快照、数据集
    catalog/              1：导入、搜索、详情、数据集
    lineage/              2：局部图
    evidence/             3：抽取、证据、核验
    analysis/             4：统计、对比、导出
    galaxy/               扩展：大图（待实现）
  scripts/seed.py         初始化数据
  tests/                  按工作包分目录
frontend/
  src/app/                导航、路由、占位页
  src/shared/             请求客户端、类型、样式
  src/modules/            每个工作包一个目录
fixtures/                 公共样例数据（12 条边，含环与 ghost 节点）
docs/                     契约、部署、第三方声明
```

## 接口一览

| 方法与路径 | 归属 | 说明 |
|---|---|---|
| `GET /api/health` | 1 | 就绪检查 |
| `GET /api/meta` | 1 | 上限常量、关系类型 |
| `POST /api/imports` | 1 | 导入（fixtures / hubstats / modeltree） |
| `GET /api/imports` | 1 | 导入记录 |
| `GET /api/snapshots` | 1 | 数据版本 |
| `GET /api/snapshots/{id}/stats` | 1 | 快照概况 |
| `GET /api/datasets` | 1 | 数据集关联 |
| `GET /api/models` | 1 | 搜索与分页 |
| `GET /api/model` | 1 | 模型详情 |
| `GET /api/graph` | 2 | 局部上下游图（`view=declared\|completed`） |
| `GET /api/analysis` | 4 | 统计指标（`view=declared\|completed`） |
| `POST /api/extractions` | 3 | 运行规则抽取，生成候选与证据 |
| `GET /api/candidates` | 3 | 候选列表（按状态过滤） |
| `GET /api/relations/{id}` | 3 | 关系详情 + 证据 + 核验历史 |
| `POST /api/relations/{id}/reviews` | 3 | 确认 / 驳回 / 未知 |
| `GET /api/diff` | 4 | 补全前后对比 |
| `GET /api/analysis/export.csv` | 4 | 导出带快照与口径的 CSV |

详细字段与示例见 [docs/CONTRACTS.md](docs/CONTRACTS.md)。

## 文档

- [docs/CONTRACTS.md](docs/CONTRACTS.md) — 接口契约（冻结层，改动需四人同意）
- [CONTRIBUTING.md](CONTRIBUTING.md) — 分支、提交、合并规则
- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) — 第三方代码与数据许可
- [docs/平台搭建两周任务分工.md](docs/平台搭建两周任务分工.md) — 四人分工与排期

## 数据与许可

- 原始数据：[hub-stats](https://huggingface.co/datasets/cfahlgren1/hub-stats)（Apache-2.0），`models.parquet` 不进 Git。
- 参考实现：model-family-tree（MIT）。
- 本项目代码许可见仓库根目录 `LICENSE`（待小组确认后补）。
