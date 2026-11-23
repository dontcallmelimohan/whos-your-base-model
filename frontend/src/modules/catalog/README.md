# 模型目录（任务 1）

`/catalog` 的衍生排行可以按全部后代、近 90 天、直接下游和衍生类型排序。排行按选定快照的声明关系计算，全部后代跨层去重。切换到「全部模型」后，可以按名称搜索、分页、隐藏占位上游和切换快照。详情展示模型属性、声明的直接上游、模型卡中的数据集与许可证字段，并提供 Hugging Face 仓库链接。

`GET /api/models` 和 `GET /api/model` 支持 `snapshot_id`。详情接口的 `declared_parents` 包含上游 ID、关系类型和来源字段，`license_declaration` 保存有记录的模型卡许可证字段。证据检索可使用模型 ID 和快照定位原仓库。

后端代码位于 `backend/modules/catalog/`，测试位于 `tests/catalog/`。
