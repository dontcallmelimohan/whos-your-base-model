# 证据交接与判定约定（任务 3 → 任务 4）

> 2026-11-23 · 对应分工 v5。改动这里要同步：
> `backend/modules/evidence/retrieval/`、`verification/`、
> `frontend/src/modules/evidence/fields.ts` 与 `docs/CONTRACTS.md`。

任务 3 产出**候选和证据**，任务 4 产出**判定、核验记录和入图状态**。
两边只通过下面这些字段交接，不直接改对方的代码。

## 1. 任务 3 交出的东西

### 1.1 候选关系

| 字段 | 含义 | 来源 |
|---|---|---|
| `snapshot_id` | 数据快照 | 任务 1 |
| `parent_id` | 候选上游（`org/name`） | 规则命中 |
| `child_id` | 下游模型 | 模型卡所属模型 |
| `relation_type` | `finetune / adapter / quantized / merge / unknown` | 规则到类型的映射 |
| `rule_id` | 命中的规则，如 `r_finetuned_from` | 规则表 |
| `origin` | 固定 `candidate` | 模块写入 |

### 1.2 证据

| 字段 | 含义 |
|---|---|
| `id` | 由 `snapshot + relation + rule + path + locator` 派生，重复运行不变 |
| `source_type` | `model_field / model_card_text / model_card_yaml / config` |
| `source_path` | 文件路径或 URL，如 `README.md` |
| `locator` | 行号 `L42`，字段名如 `base_model`，配置项如 `config.json:base_model` |
| `quote` | 原文或配置值原样截取（≤ 400 字符），不改写 |
| `revision` | commit SHA 或快照标识；没有就空，页面显示「仅有数据快照」 |

### 1.3 检索记录（来源范围与失败）

任务 3 还要交出「查过哪些来源、哪些打不开」，字段与前端
`fields.ts` 的 `RetrievalRecord` 对齐：

```json
{
  "snapshot_id": "modelbiome-2026-11",
  "model_id": "stabilityai/stable-video-diffusion-img2vid-xt",
  "rule_version": "rules-v2",
  "checked": ["README.md", "config.json"],
  "failures": [
    { "model_id": "stabilityai/stable-video-diffusion-img2vid-xt",
      "path": "config.json", "reason": "not_found" }
  ],
  "created_candidates": 1,
  "created_evidence": 1
}
```

失败原因只用这几个值：`not_found` / `access_denied` / `timeout` / `unsupported`。
**不能把「没查」写成「没证据」。**

## 2. 版本对齐

- 证据的 `revision` 与快照一致 → 计入同快照差分；
- revision 不同或缺失 → 单独展示，页面上标「未对齐版本」；
- 不能为了凑数把线上最新 README 的证据算到旧快照上。

## 3. 任务 4 的判定结果

```json
{
  "relation_id": "rel_…",
  "verdict": "support",
  "insufficient_reason": null,
  "evidence_ids": ["ev_…"],
  "reason": "README 明确写 finetuned from stabilityai/stable-video-diffusion-img2vid",
  "rule_id": "r_finetuned_from",
  "rule_version": "rules-v2",
  "version_aligned": true
}
```

| `verdict` | 判定条件 | 入图 |
|---|---|---|
| `support` | 原文/配置明确支持两端、方向、类型 | 是 |
| `refute` | 原文明确指向别的上游，或明确否认 | 否 |
| `conflict` | 已检查来源互相矛盾，或与已有声明冲突 | 否 |
| `insufficient` | 定位不到足够的直接证据 | 否 |

`insufficient` 必须带 `insufficient_reason`：

| 值 | 含义 |
|---|---|
| `not_found` | 查过来源，没有提到这条关系 |
| `ambiguous` | 提到了名字，但看不出方向、类型或确切模型 ID |
| `unreachable` | 来源不可访问（与检索失败原因对应） |

## 4. 入图门槛（全部满足才自动发布）

1. 结论为 `support`；
2. 已检查来源之间没有 `conflict`；
3. 原文或配置明确支持**两端、方向、类型**——共同祖先、链接、家族名不算；
4. `version_aligned = true`；
5. 关系唯一键 `(snapshot_id, parent_id, child_id, relation_type)` 去重，重复运行不加边。

已有声明关系的异议只写核验记录，**基线图继续用原始声明**。
自动入图不经过人工审批；页面保留人工复核作为兜底。

## 5. 固定样例（第 1 天定稿，测试直接引用）

### S1 支持 · 答辩主案例

> 前提：本地已有保存 `modelCard` 正文的 Model Biome 快照。
> 目前 `fixtures/model_cards.json` 是合成样例，导入真实快照后要替换成真实原文。

- 下游：`stabilityai/stable-video-diffusion-img2vid-xt`
- 快照里五个父模型字段为空；
- README 原文（示意，实际以快照正文为准）：

  > This model is finetuned from stabilityai/stable-video-diffusion-img2vid.

- 期望：`support`，`relation_type = finetune`，证据 `source_path = README.md`，
  `locator = L<n>`，`version_aligned = true`。

### S2 反驳 · 同一句话指向别的上游

- 正文写 `fine-tuned from` 另一个模型，或写明「本模型没有微调自 X」；
- 期望：`refute`，不得入图，原始声明关系不受影响。

### S3 来源冲突

- README 说 `finetuned from A`，`config.json` 的 `base_model` 写 `B`；
- 期望：`conflict`，列出两条证据 ID，不入图，页面提示「来源冲突」。

### S4 证据不足

- README 只写「built on the SD ecosystem」「based on SD」这类家族/共同祖先说法；
- 期望：`insufficient` + `ambiguous`（或正文缺失时 `unreachable`），
  不把家族名当直接上游。

## 6. 代码落点

| 内容 | 位置 |
|---|---|
| 来源读取、失败原因 | `backend/modules/evidence/retrieval/sources.py` |
| 规则提取、证据落库 | `backend/modules/evidence/retrieval/extract.py` |
| 判定词汇与入口 | `backend/modules/evidence/verification/judge.py` |
| 候选查询、复核记录 | `backend/modules/evidence/verification/service.py` |
| 批处理入口 | `backend/modules/evidence/verification/batch.py` |
| 前端字段与文案 | `frontend/src/modules/evidence/fields.ts` |
| 接口契约 | `docs/CONTRACTS.md` 第 7、8 节 |

## 7. 待定（需四人同意后改冻结层）

v5 要求「单模型 / 单条边核验入口」和「核验结论查询」，目前接口只有
`POST /api/extractions` 与人工复核。拟新增：

- `POST /api/verifications`（body：`snapshot_id` + `model_id` 或 `relation_id`）→ 结论列表；
- `GET /api/verifications?relation_id=` → 历史结论。

落地前先在群里过一遍，补进 `shared/contracts.py`、`shared/types.ts` 和
`docs/CONTRACTS.md` 再写实现。
