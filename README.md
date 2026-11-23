# Who's Your Base Model? — 开放模型谱系查询与证据核验平台

课程大作业（北航 · 开源软件开发导论）。输入一个模型，查它基于谁、有哪些下游，
以及每条关系的**依据**：原文、出处、版本与检索状态。

核心交付是**可追溯的自动依赖核验与补全**：检查公开文档是否支持一条直接上游关系，
保留出处，并展示补全如何改变图和统计。

数据来自 hub-stats 每日 dump（约 326 万个模型、97 万条 `base_model` 父链接），
字段口径与布局参考 [model-family-tree](https://github.com/h9-tec/model-family-tree)。

## 四个工作包

分工与验收见 [docs/平台搭建两周任务分工.md](docs/平台搭建两周任务分工.md)（v5，2026-11-23）。

| 任务 | 负责什么 | 负责人 | 代码 | 状态 |
|---|---|---|---|---|
| **1** | 模型目录、数据与生态分析 | 李默涵 | `backend/modules/{catalog,analysis}/`、`src/modules/{catalog,data,analysis}/` | 可用；分析首版待补核验汇总表 |
| **2** | 谱系探索与可视化 | 待认领 | `backend/modules/lineage/`、`shared/graph_read.py`、`src/modules/lineage/` | 可用；分批展开与点边跳证据待补 |
| **3** | 证据检索与候选提取 | 待认领 | `backend/modules/evidence/retrieval/` | 本地规则可用；线上补查待实现 |
| **4** | 自动核验与谱系补全 | 待认领 | `backend/modules/evidence/verification/`、`src/modules/evidence/` | 候选/复核可用；自动判定与批处理待实现 |

任务 3 与任务 4 共用 `backend/modules/evidence/`，按子目录分：检索归 3，
判定 / 核验记录 / 入图归 4。交接字段与四类结论见
[docs/EVIDENCE_HANDOFF.md](docs/EVIDENCE_HANDOFF.md)。


## 快速开始

### 1. 后端

```bash
# 在仓库根目录（platform/）
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt

cd backend
python -m scripts.seed                       # 样例数据（秒级，够开发）
# 或直接同步 Hugging Face 上最新的模型快照
# python -m scripts.sync_hubstats --limit 20000

uvicorn app:app --reload --port 8000
```

打开 <http://127.0.0.1:8000/docs> 看接口文档。

### 同步 hub-stats

在「数据管理」选择 Hugging Face 最新快照并点击「同步最新快照」，或从 `backend/` 运行：

```bash
../.venv/bin/python -m scripts.sync_hubstats --limit 20000
# 导入全量模型时传 --limit 0
```

默认按下载量取前 20,000 个模型，另外收录它们的直接上游。全量模式也包含没有声明上游的模型。首次同步或上游版本变化时会下载约 1.8 GB。系统按 `models.parquet` 的提交 SHA 下载并校验 SHA-256。同一版本和范围重复同步会跳过下载。新快照成功入库后才可见，原有快照可继续在目录和数据页查看。基线读取 `baseModels` 和旧式 `base_model:` 标签，目录同时收录模型卡元数据中的许可证和数据集声明。

需要定期检查时，可以把同一命令交给系统的任务计划程序，每天运行一次。定时任务和服务应使用同一个数据库路径（默认 `platform/data/platform.db`，或通过 `PLATFORM_DB` 指定）。数据库会保留各次成功同步的快照。开发与日常同步可用限量模式，一个全量快照的 SQLite 存储约 2 GB。线下也可以通过 `scripts.seed --source hubstats` 导入已有的本地 `models.parquet`。

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

### 4. 测试

```bash
make test          # 等价于 .venv/bin/python -m pytest -q
```

## 目录

```text
backend/
  app.py                  只注册路由
  shared/                 冻结契约：contracts / db / errors / config / graph_read / migrations
  modules/
    catalog/              任务 1：导入、搜索、详情、数据集
    analysis/             任务 1：核验汇总、差分、CSV
    lineage/              任务 2：局部谱系图
    evidence/
      retrieval/          任务 3：来源读取、规则提取、候选与证据
      verification/       任务 4：判定、核验记录、入图状态、批处理
    galaxy/               扩展：大图（不在 v5 验收范围）
  scripts/seed.py         初始化数据
frontend/
  src/app/                导航、路由、占位页
  src/shared/             请求客户端、类型、样式（冻结层）
  src/modules/            每个工作包一个目录
fixtures/                 公共样例数据（冻结层，改动需四人同意）
tests/                    按工作包分目录：catalog / analysis / lineage /
                          evidence/retrieval / evidence/verification / integration
docs/                     契约、证据交接、分工与排期
```

## 接口一览

| 方法与路径 | 归属 | 说明 |
|---|---|---|
| `GET /api/health` | 公共 | 就绪检查 |
| `GET /api/meta` | 公共 | 上限常量、关系类型 |
| `POST /api/imports` | 1 | 导入（fixtures / hubstats / modeltree） |
| `GET /api/imports` | 1 | 导入记录 |
| `GET /api/snapshots` | 1 | 数据版本 |
| `GET /api/snapshots/{id}/stats` | 1 | 快照概况 |
| `GET /api/datasets` | 1 | 数据集关联 |
| `GET /api/models` | 1 | 搜索与分页 |
| `GET /api/model` | 1 | 模型详情 |
| `GET /api/graph` | 2 | 局部上下游图（`view=declared\|completed`） |
| `GET /api/analysis` | 1 | 统计指标（`view=declared\|completed`） |
| `GET /api/diff` | 1 | 补全前后差分 |
| `GET /api/analysis/export.csv` | 1 | 带快照与口径的 CSV |
| `POST /api/extractions` | 3 | 规则抽取，生成候选与证据 |
| `GET /api/candidates` | 4 | 候选列表（按状态过滤） |
| `GET /api/relations/{id}` | 4 | 关系详情 + 证据 + 核验历史 |
| `POST /api/relations/{id}/reviews` | 4 | 人工复核（兜底，自动核验为主） |

详细字段与示例见 [docs/CONTRACTS.md](docs/CONTRACTS.md)。

## 验收主线

用 `stabilityai/stable-video-diffusion-img2vid-xt` 走一遍：

1. 模型详情：快照里五个父模型字段为空；
2. 核验页运行单模型核验：从 README 找到 `finetuned from` 指向
   `stabilityai/stable-video-diffusion-img2vid`；
3. 证据详情：展示原文、上游模型、快照来源，记录支持结论；
4. 谱系与分析：补全图出现这条微调关系，差分表显示新增边与受影响指标，可导出 CSV。

样例证据（支持 / 反驳 / 来源冲突 / 证据不足）见
[docs/EVIDENCE_HANDOFF.md](docs/EVIDENCE_HANDOFF.md) 第 5 节。

## 已知缺口（会影响验收）

- **演示数据还没对齐。** hub-stats 提供结构化模型卡字段，证据演示仍需带 README 正文的样本。
  v5 主线要求「Model Biome 快照 + README 正文」，需要先导入带 modelCard 的快照，
  任务 3 的 `sources.py` 才能读真实正文。
- **自动核验还是占位。** `judge.py` / `batch.py` 只留了入口与结论词汇，
  当前入图仍靠人工确认；任务 4 接上规则前，差分表只能展示人工确认的边。
- **分析首版没做完。** 现有 `/analysis` 是生态指标页，v5 要的
  「按关系类型的核验汇总 + 受影响模型直接下游差分 + 证据 ID 导出」还没接。

## 文档

- [docs/CONTRACTS.md](docs/CONTRACTS.md) — 接口契约（冻结层，改动需四人同意）
- [docs/EVIDENCE_HANDOFF.md](docs/EVIDENCE_HANDOFF.md) — 任务 3 → 4 的字段、四类结论与入图门槛
- [CONTRIBUTING.md](CONTRIBUTING.md) — 代码归属、分支、迁移编号
- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) — 第三方代码与数据许可
- [docs/平台搭建两周任务分工.md](docs/平台搭建两周任务分工.md) — 四人分工与排期

## 数据与许可

- 原始数据：[hub-stats](https://huggingface.co/datasets/cfahlgren1/hub-stats)（Apache-2.0），`models.parquet` 不进 Git。
- 参考实现：model-family-tree（MIT）。
- 本项目代码许可见仓库根目录 `LICENSE`（待小组确认后补）。
