# AI 模型供应链交互与分析平台

课程大作业（北航 · 开源软件开发导论）。浏览器里查看 Hugging Face 模型的上游与下游、证据来源，以及整个生态的分布。

数据来自 hub-stats 每日 dump（约 326 万个模型、97 万条 `base_model` 父链接），字段口径与布局参考 [model-family-tree](https://github.com/h9-tec/model-family-tree)。

## 模块与状态

| 工作包 | 内容 | 负责人 | 状态 |
|---|---|---|---|
| **A** | 数据与框架：导入、快照、契约、骨架、部署 | 李默涵 | 后端可用，前端骨架已搭 |
| **B** | 模型目录 + 供应链小图（`/catalog`、`/lineage`） | 待认领 | 小图已由 A 迁移可用，目录仍占位 |
| **C** | 大图 Galaxy（`/galaxy`） | 待认领 | 占位页 |
| **D** | 生态分析（`/analysis`） | 待认领 | 初版可用（指标卡 + 集中度 + 两张榜） |

顶栏右上角的 ☀/☾ 按钮切换亮/暗主题（也会记住选择）；`?theme=dark` 可直接分享暗色链接。

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
    catalog/  lineage/    B：搜索、局部图
    galaxy/               C：大图（待实现）
    analysis/             D：统计
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
| `GET /api/health` | A | 就绪检查 |
| `GET /api/meta` | A | 上限常量、关系类型 |
| `POST /api/imports` | A | 导入（fixtures / hubstats / modeltree） |
| `GET /api/imports` | A | 导入记录 |
| `GET /api/snapshots` | A | 数据版本 |
| `GET /api/snapshots/{id}/stats` | A | 快照概况 |
| `GET /api/datasets` | A | 数据集关联 |
| `GET /api/models` | B | 搜索与分页 |
| `GET /api/model` | B | 模型详情 |
| `GET /api/graph` | B | 局部上下游图 |
| `GET /api/analysis` | D | 统计指标 |

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
