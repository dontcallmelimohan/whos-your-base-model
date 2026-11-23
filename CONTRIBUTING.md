# 贡献指南

## 一句话规则

**每人只改自己的目录，只 import `shared/`。需要别人的东西就改契约，不要改别人的代码。**

分工版本：v5（2026-11-23），见 [docs/平台搭建两周任务分工.md](docs/平台搭建两周任务分工.md)。

## 领地划分

| 任务 | 后端 | 前端 | 测试 |
|---|---|---|---|
| 1 目录、数据与分析 | `backend/modules/catalog/`、`backend/modules/analysis/` | `src/modules/catalog/`、`src/modules/data/`、`src/modules/analysis/` | `tests/catalog/`、`tests/analysis/` |
| 2 谱系与可视化 | `backend/modules/lineage/`、`backend/shared/graph_read.py` | `src/modules/lineage/` | `tests/lineage/` |
| 3 检索与提取 | `backend/modules/evidence/retrieval/` | `src/modules/evidence/fields.ts`（证据字段与样例响应） | `tests/evidence/retrieval/` |
| 4 核验与补全 | `backend/modules/evidence/verification/`、证据相关迁移 | `src/modules/evidence/`（页面与接口调用） | `tests/evidence/verification/` |

`backend/modules/galaxy/` 与 `src/modules/galaxy/` 是扩展占位，不在 v5 验收范围，认领前先说明。

## 公共文件

这些文件**只允许加一行**，不允许重构别人的部分：

- `backend/app.py` 的 include 列表；
- `frontend/src/app/router.ts` 的路由表；
- `backend/modules/evidence/router.py` 的两个子路由聚合。

## 契约冻结点

以下改动必须先在群里说，并同步改代码与文档：

- `backend/shared/contracts.py`
- `frontend/src/shared/types.ts`
- `fixtures/`
- `docs/CONTRACTS.md`（改契约必改这一份）
- `backend/shared/migrations/`（只加文件，不改已有文件）

证据有关的字段、四类结论、入图门槛另有约定：
[docs/EVIDENCE_HANDOFF.md](docs/EVIDENCE_HANDOFF.md)。任务 3 与 4 各自实现前先对这份文档。

## 证据模块的边界

```text
modules/evidence/
  retrieval/       任务 3：读来源、提候选、存证据；不写结论
  verification/    任务 4：判定、核验记录、入图状态、批处理；不改候选规则
```

- 任务 3 的产出是「线索 + 原文」，不是「结论」；
- 任务 4 只有拿到明确支持、且来源无冲突、版本对齐时才自动入图；
- 两边都不许绕过对方直接改关系状态或证据表。

## 分支与提交

```bash
git checkout -b feat/catalog-search      # feat/ | fix/ | docs/ + 你的模块名
git commit -m "feat(catalog): 按名称搜索与分页"
```

提交信息用 Conventional Commits：`feat(catalog): ...`、`fix(lineage): ...`、`docs: ...`。

合并前：

```bash
make test                              # 仓库根
cd frontend && npm run build
```

## 接入自己的模块（四步）

1. **后端**：在 `backend/modules/<你的模块>/` 建 `router.py`，写
   `router = APIRouter(prefix="/api", tags=["<模块>"])`；
   在 `backend/app.py` 的 include 区加一行。证据模块写在
   `retrieval/router.py` 或 `verification/router.py`，不要动聚合层。
2. **前端**：在 `src/modules/<你的模块>/` 写页面与 `api.ts`；
   在 `src/app/router.ts` 把对应的 `PlaceholderPage` 换成你的组件，
   `meta.owner` 填任务号。
3. **测试**：在仓库根 `tests/<你的模块>/` 写用例，用 `tests/conftest.py` 的 `client` 夹具。
4. **说明**：在你目录的 `README.md` 更新“已完成 / 未完成 / 已知问题”。

## 数据库迁移

编号按 v5 归属，只加自己的文件：

```text
001_init.sql              公共骨架（已占用）
002_evidence.sql          任务 4 证据表（已占用）
003_verification_*.sql    任务 4 新的判定 / 核验记录表
010_catalog_*.sql         任务 1 目录与数据
020_lineage_*.sql          任务 2 谱系（若需要）
030_analysis_*.sql        任务 1 分析
```

只给自己的表加字段，不改别人的表；`ALTER TABLE` 不是幂等的，靠
`schema_migrations` 记账，所以文件名一旦应用就不要再改。

## 代码风格

- Python：`ruff` 默认规则，行宽 100，类型注解尽量写全。
- TypeScript：`strict: true`，不要用 `any` 逃逸；请求统一走 `src/shared/api.ts`。
- 不许引入新的前端依赖而不说明理由（尤其不要为了一个图表引入整套 UI 库）。

## 禁止事项

1. 把 `models.parquet`、`platform.db`、`node_modules`、`dist` 提交进 Git。
2. 从 `open-model-evolution` 复制任何代码（该仓库未声明许可证）。
3. 在前端写死后端地址（用 `/api` 相对路径）。
4. 跨模块 `import`。
