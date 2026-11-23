# 第三方代码与数据声明

本仓库包含或改编了以下第三方作品。分发本项目时请一并保留本文件。

## 1. model-family-tree

- 来源：<https://github.com/h9-tec/model-family-tree>
- 许可：MIT License，Copyright (c) 2026 Hesham Haroon
- 使用范围：
  - 关系类型与统计口径（`finetune` / `adapter` / `quantized` / `merge` / `unknown`，`direct` 与 `total` 后代数，family、ghost 概念）；
  - 后续大图模块（`backend/modules/galaxy/`）将改编其 `site/galaxy.js` 与 `modeltree/galaxy.py` 的布局逻辑。
- MIT 全文：

```text
MIT License

Copyright (c) 2026 Hesham Haroon

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 2. hub-stats（数据）

- 来源：<https://huggingface.co/datasets/cfahlgren1/hub-stats>
- 许可：Apache-2.0
- 使用范围：模型元数据与 `baseModels` 标签，作为平台的基础数据。
- 数据文件本身不进入 Git，使用时请注明快照日期。

## 3. Lineage Explorer（仅参考交互）

- 来源：<https://huggingface.co/spaces/EQTYLab/lineage-explorer>
- 许可：Apache-2.0（Space README 声明）
- 使用范围：**只参考界面组织方式**（分栏、点击展开、边详情面板）。
- 若后续复制其代码，需保留其版权与 NOTICE，并在本节补充具体文件清单。
- 注意：其数据来自模型仓库内的 `.eqtylab/` manifest，与本项目使用的 `base_model` 标签不是同一来源。

## 4. Open Model Evolution（仅参考版式，未使用代码）

- 来源：<https://huggingface.co/spaces/economies-open-ai/open-model-evolution>
- 许可：**未声明**（默认保留所有权利）
- 使用范围：只参考页面版式与指标定义思路，**未复制任何代码或样式**。
- 相关论文：arXiv:2512.03073

## 5. 前端依赖

- Vue 3（MIT）、Vue Router（MIT）、Vite（MIT）、TypeScript（Apache-2.0）。
- 字体使用系统字体栈，不引入外部 CDN，保证断网可演示。
