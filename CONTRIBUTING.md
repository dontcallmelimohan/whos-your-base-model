# 贡献指南

## 一句话规则

**每人只改自己的目录，只 import `shared/`。需要别人的东西就改契约，不要改别人的代码。**

## 领地划分

| 工作包 | 后端 | 前端 | 测试 |
|---|---|---|---|
| A 数据与框架 | `backend/shared/`、`backend/modules/data/`、`app.py`、`scripts/` | `src/app/`、`src/shared/`、`src/modules/data/` | `backend/tests/data/` |
| B 目录 + 小图 | `backend/modules/catalog/`、`backend/modules/lineage/` | `src/modules/catalog/`、`src/modules/lineage/` | `backend/tests/catalog/`、`backend/tests/lineage/` |
| C 大图 | `backend/modules/galaxy/` | `src/modules/galaxy/` | `backend/tests/galaxy/` |
| D 分析 | `backend/modules/analysis/` | `src/modules/analysis/` | `backend/tests/analysis/` |

公共文件（`app.py`、`router.ts`、`app.py` 的 include 列表）**只允许加一行**，不允许重构别人的部分。

## 分支与提交

```bash
git checkout -b feat/catalog-search      # feat/ | fix/ | docs/ + 你的模块名
git commit -m "feat(catalog): 按名称搜索与分页"
```

提交信息用 Conventional Commits：`feat(catalog): ...`、`fix(lineage): ...`、`docs: ...`。

合并前：

```bash
cd backend && python -m pytest tests -q
cd ../frontend && npm run build
```

## 接入自己的模块（四步）

1. **后端**：在 `backend/modules/<你的模块>/` 建 `router.py`，写 `router = APIRouter(prefix="/api", tags=["<模块>"])`；
   在 `backend/app.py` 的 include 区加一行 `app.include_router(your_router)`，并在 `# TODO(C)` 处保留注释风格。
2. **前端**：在 `src/modules/<你的模块>/` 写页面与 `api.ts`；
   在 `src/app/router.ts` 把对应的 `PlaceholderPage` 换成你的组件。
3. **测试**：在 `backend/tests/<你的模块>/` 写用例，用 `tests/conftest.py` 里的 `client` 夹具。
4. **说明**：在你目录的 `README.md` 里更新“已完成/未完成/已知问题”。

## 契约冻结点

以下文件是四人共用的，**改动必须先在群里说，并同步更新 `docs/CONTRACTS.md`**：

- `backend/shared/contracts.py`
- `frontend/src/shared/types.ts`
- `backend/shared/migrations/`（只加，不改已有文件）

## 数据库迁移

每人一个号段，只加自己的文件：

```text
001_init.sql          A（已占用）
010_catalog_*.sql     B
020_galaxy_*.sql      C
030_analysis_*.sql    D
```

只给自己的表加字段，不改别人的表。

## 代码风格

- Python：`ruff` 默认规则，行宽 100，类型注解尽量写全。
- TypeScript：`strict: true`，不要用 `any` 逃逸；请求统一走 `src/shared/api.ts`。
- 不许引入新的前端依赖而不说明理由（尤其不要为了一个图表引入整套 UI 库）。

## 禁止事项

1. 把 `models.parquet`、`platform.db`、`node_modules`、`dist` 提交进 Git。
2. 从 `open-model-evolution` 复制任何代码（该仓库未声明许可证）。
3. 在前端写死后端地址（用 `/api` 相对路径）。
4. 跨模块 `import`。
