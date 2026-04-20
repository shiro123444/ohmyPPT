# ohmyPPT

`ohmyPPT` 是一个研究型整合仓库，用来并排保存两套能力，并沉淀后续产品化方向：

- `landppt/`
  - 来自 `sligter/LandPPT`
  - 偏向 AI 驱动的 HTML 幻灯片生成、在线编辑、流式逐页生成、双路导出
- `minimax-skills/`
  - 来自 `MiniMax-AI/skills`
  - 其中 `pptx-generator` skill 提供了更偏工程化、专业化的 PPTX 生产协议

本仓库的目标不是简单拼接两个项目，而是研究一种新的路线：

- 保留 `LandPPT` 已有的细粒度控制流
- 吸收 `MiniMax pptx-generator` 的专业 PPT 编排方法
- 形成一个更简化、但更专业、更稳定的 `ohmyPPT`

## 目录

- `landppt/`: LandPPT 源码副本
- `minimax-skills/`: MiniMax skills 源码副本
- `README.md`: 当前研究结论与整合建议

## LandPPT 当前是怎么做 PPT 的

### 1. 它的核心产物其实是 HTML 幻灯片

LandPPT 不是先生成 `.pptx`，而是先逐页生成 HTML。

关键链路：

- 逐页流式生成入口：
  - `landppt/src/landppt/services/slide/slide_streaming_service.py`
- 单页生成与图片上下文注入：
  - `landppt/src/landppt/services/slide/slide_media_service.py`
- 最终把逐页结果合并成 `slides_html`：
  - `landppt/src/landppt/services/slide/slide_generation_service.py`

实际流程大致是：

1. 先有 outline
2. 再逐页生成 slide HTML
3. 每页结果单独存库
4. 全部完成后拼成完整 `slides_html`

这意味着它天然支持：

- 单页流式生成
- 单页重试
- 单页持久化
- 断线重连
- HTML 级在线编辑

### 2. PPTX 导出有两条路

#### 标准 PPTX 导出

路径：

- `HTML -> PDF -> PPTX`

关键实现：

- `landppt/src/landppt/web/route_modules/export_routes.py`

说明：

- 先用 Playwright 渲染 PDF
- 再通过 Apryse 把 PDF 转 PPTX
- 还可以把讲稿写入 PPT 备注

#### 图片型 PPTX 导出

路径：

- `HTML -> PNG 截图 -> PPTX`

关键实现：

- `landppt/src/landppt/web/route_modules/export_routes.py`

说明：

- 逐页把 HTML 渲染成截图
- 用 `python-pptx` 把整页图贴进 PPTX
- 对复杂 HTML/CSS 样式保真度更高

### 3. 图片不是固定某一家 AI 生成

LandPPT 有自己的图片服务抽象层。

已支持的生成 provider 包括：

- `dalle`
- `stable_diffusion`
- `siliconflow`
- `gemini`
- `openai_image`
- `pollinations`

搜图 provider 包括：

- `unsplash`
- `pixabay`
- `searxng`

关键实现：

- `landppt/src/landppt/services/image/image_service.py`
- `landppt/src/landppt/services/ppt_image_processor.py`

其中比较重要的一点是：

- 是否配图
- 配几张图
- 用本地图、网络图还是 AI 生图

这些不是写死的，而是由 `PPTImageProcessor` 在配置和内容分析基础上动态决定。

### 4. LandPPT 已经有“专业化”雏形

虽然当前最终输出还是 HTML，但它内部已经不只是“让 AI 随便写一页页面”。

它其实在做多层设计控制：

- 全局视觉规则
- 页面类型级指导
- 项目级设计指导
- 单页生成

关键实现：

- `landppt/src/landppt/services/prompts/design_prompts.py`

这很重要，因为它说明 `LandPPT` 并不缺“控制力”，缺的是：

- 更稳定的结构化中间层
- 更收敛的页型系统
- 更专业的最终编译协议

## MiniMax `pptx-generator` skill 的核心价值

MiniMax 的 `pptx-generator` skill 不是一个简单“帮你做 PPT”的 prompt，它更像一份专业 PPT 工程规范。

来源：

- `minimax-skills/skills/pptx-generator/SKILL.md`

它的核心特点有：

### 1. 从一开始就面向 PPTX，而不是 HTML

它直接围绕 `PptxGenJS` 组织生成工作流，目标文件是 `.pptx`。

### 2. 它强制页型化

默认把整套演示文稿压缩进有限页型：

- Cover
- TOC
- Section Divider
- Content
- Summary

这会显著降低“每页都重新发明一次版式”的不稳定性。

### 3. 它有明确设计系统约束

skill 中要求主题对象必须使用固定键：

- `primary`
- `secondary`
- `accent`
- `light`
- `bg`

而不是让每次生成都重新发明配色字段名。

### 4. 它是模块化编译

生成策略不是“一次性吐完整 deck”，而是：

1. 先规划大纲和页型
2. 每页一个独立 JS 模块
3. 最后 `compile.js` 合并

这个模式特别适合：

- 并行生成
- 单页替换
- QA 校验
- 编译失败时的局部修复

### 5. 它的“专业感”来自约束，而不是模型更聪明

真正让它显得专业的，不是某个神奇模型，而是它把以下东西定死了：

- 页面尺寸
- 主题 contract
- 页型集合
- 文件结构
- 编译入口
- QA 流程

## 两者的本质差异

### LandPPT 的强项

- Web 化完整
- 流式逐页生成成熟
- 单页编辑能力强
- HTML 渲染自由度高
- 在线协作和导出路径完整

### MiniMax `pptx-generator` 的强项

- PPTX 原生思维
- 页型体系清晰
- 设计系统收敛
- 编译式产出更稳定
- 更适合做“专业模板化”输出

### LandPPT 当前的主要问题

- 最终生成自由度较高，稳定性依赖 prompt
- 页面表达能力很强，但专业 deck 的一致性有时不够稳定
- HTML 很强，PPTX 原生表达相对弱
- 缺少一个统一的中间结构把“内容、版式、资源、导出”绑在一起

### MiniMax 方案直接搬进 LandPPT 的问题

- Skill 是给 agent 的工作说明，不是给 FastAPI 直接调用的运行时协议
- 直接输出 `PptxGenJS` 模块体系，和 LandPPT 当前 `slides_html` 存储模型不一致
- 强行塞进去会形成双状态机、双渲染协议、双维护成本

## 研究结论

不建议把 `MiniMax skill` 原样塞进 `LandPPT`。

更合适的方向是：

- 借用 `MiniMax pptx-generator` 的方法论
- 用 `LandPPT` 的控制流、用户态能力、编辑能力去承载
- 做一个新的上层产品方向：`ohmyPPT`

一句话概括：

> 借流程，不硬塞 skill；借约束，不放弃 LandPPT 的颗粒级控制。

## 我建议的 ohmyPPT 路线

### 总体目标

做一个“双引擎”的演示文稿系统：

- `Creative Mode`
  - 继承 LandPPT 的自由 HTML 生成能力
- `Professional Mode`
  - 吸收 MiniMax 的页型化、设计系统化、模块化编译方式

### 核心中间层：Presentation Spec

真正需要补的不是更多 prompt，而是一个统一的中间结构。

建议新增：

- `presentation_spec`

建议字段：

- `deck_meta`
- `theme_spec`
- `outline_spec`
- `slide_specs`
- `asset_plan`
- `speaker_notes`
- `render_target`

每页 `slide_spec` 建议至少包含：

- `slide_id`
- `slide_type`
- `content_blocks`
- `layout_constraints`
- `visual_priority`
- `image_policy`
- `chart_policy`
- `notes`

这样就能把当前生成链路改成：

1. 输入主题与要求
2. 生成 outline
3. 把每页强制归类成有限页型
4. 先生成统一设计系统
5. 每页先出 `slide_spec`
6. 再交给不同 renderer 输出

## 建议保留的 LandPPT 颗粒控制能力

这些能力是后续产品差异化的重要部分，不应因为追求“专业化”而丢掉：

- 单页重生成
- 单页锁定
- 单页图片策略
- 单页设计 brief
- 页面级与全局级分层指导
- 流式逐页状态追踪
- 在线编辑
- 分享、讲稿、导出链路

## 建议简化的地方

“简化但专业化”不等于砍功能，而是减少无边界自由度。

建议收敛：

- 页型数量
- 每种页型的布局家族
- 主题变量数量
- 图片用途分类
- 图表组件集合
- 页面构图自由度

也就是说：

- 让 AI 先生成 `spec`
- 再让 renderer 负责“怎么画”

而不是让 AI 每次直接写最终整页 HTML。

## 推荐架构

### 渲染双通路

同一份 `presentation_spec`，可以走两种 renderer：

- `HTML Renderer`
  - 复用 LandPPT 现有在线预览与编辑体系
- `PPTX Renderer`
  - 新增基于 `PptxGenJS` 的原生 PPTX 编译

### 产品形态

建议的最终结构是：

- `Outline Engine`
- `Theme Engine`
- `Slide Spec Engine`
- `Asset Engine`
- `HTML Renderer`
- `PPTX Renderer`
- `QA / Validation Layer`

## 分阶段落地建议

### Phase 1

目标：

- 先不碰最终导出协议
- 只把 `slide_type`、`theme_spec`、`slide_spec` 引入 LandPPT 现有 HTML 生成链路

收益：

- 稳定性立刻提升
- 可观察性提升
- 不会一下子重构过大

### Phase 1 当前已落地部分

目前仓库里已经做了第一轮工程化落地，不再只是停留在 README 方案层：

- 已新增 `presentation_spec` 的 Phase 1 schema 与 builder
  - 位置：`landppt/src/landppt/services/presentation/presentation_spec_service.py`
- 已在保存/更新项目时自动派生并刷新 `presentation_spec`
  - 当前先存放在 `project_metadata.presentation_spec`
  - 接入点：
    - `landppt/src/landppt/database/service.py`
    - `landppt/src/landppt/services/db_project_manager.py`
- 已在 `PPTProject` 响应模型上直接暴露 `presentation_spec`
  - 位置：`landppt/src/landppt/api/models.py`
- 已让 HTML 单页生成 prompt 开始消费 `slide_spec`
  - 通过 `Phase 1 Presentation Spec` 约束块，把：
    - `layout_family`
    - `visual_priority`
    - `density`
    - `image_policy`
    - `chart_policy`
    注入当前页生成提示词
  - 当前已覆盖：
    - 默认单页 prompt 路径
    - 选中全局母版后的模板生成路径
  - 接入点：
    - `landppt/src/landppt/services/slide/slide_media_service.py`
    - `landppt/src/landppt/services/slide/creative_design_service.py`
    - `landppt/src/landppt/services/prompts/design_prompts.py`
- 已让 `theme_spec.design_tokens` 同时保留：
  - `outline.theme_config`
  - `outline.metadata.theme_config`
  这样上层主题 token 不会在构建 `presentation_spec` 时被静默丢失
  - 位置：`landppt/src/landppt/services/presentation/presentation_spec_service.py`
- 已新增 `slide_spec -> render_hints` 解释层
  - 用于把中间层约束统一解释成更接近 renderer 的信号
  - 当前已覆盖：
    - `toc-grid`
    - `data-spotlight`
    - `dense-two-column`
    - `spacious-bullets`
- 已让 fallback HTML renderer 开始消费 `render_hints`
  - 位置：`landppt/src/landppt/services/slide/slide_document_service.py`

换句话说，当前状态已经从：

- “只有 README 里的目标架构”

推进到：

- “有中间层 schema”
- “有项目内自动派生与刷新”
- “有 prompt 侧消费”
- “有 fallback renderer 侧消费”

但还没有到：

- 正式 HTML renderer 全面按 `render_hints` / `content_blocks` 做确定性选择
- 原生 `PptxGenJS` renderer
- 图表/讲稿/备注/QA 全量挂到 `presentation_spec`

### Phase 2

目标：

- 新增 `PptxGenJS` 渲染器
- 让 `Professional Mode` 直接生成原生 PPTX

收益：

- 真正吸收 MiniMax `pptx-generator` 的专业化工作方式
- 避免 HTML 转 PPTX 带来的信息损耗

### Phase 3

目标：

- 把图表、图片、讲稿、备注、页级 QA 全都挂到 `presentation_spec`

收益：

- Deck 可编排、可验证、可复用
- 真正完成从“提示词生成页面”到“可控文稿系统”的升级

## 模型与 API 选择建议

### 文本模型

如果以“结构化输出 + 页型控制 + 低成本批量生成”为主，建议优先选择：

- 海外链路稳定时：
  - `gpt-5-mini`
- 国内落地优先时：
  - OpenAI 兼容接口上的 `qwen-plus`
  - 辅助角色可用 `qwen-flash`

原因：

- 这类任务更偏结构化内容生成和执行稳定性
- 不一定需要最重的推理模型
- 更重要的是 JSON/spec 服从性、成本、延迟

### 图片模型

建议分场景：

- 海外链路稳定时：
  - `gpt-image-1.5`
- 国内优先时：
  - `siliconflow`

LandPPT 当前已有图片 provider 抽象，后续最适合的是继续沿用抽象层，而不是把图片服务写死在某一家模型上。

## 为什么这是 `ohmyPPT` 而不是简单 fork

因为目标已经不只是“再套一层皮”。

新的方向实际上是在做：

- 一个更受约束的专业 deck 系统
- 一个同时支持 HTML 与 PPTX 的统一内容协议
- 一个保留页级控制的 AI 文稿编排引擎

如果这个方向继续推进，后续更合适的项目定位会是：

- `LandPPT` 偏创意化、全能化
- `ohmyPPT` 偏专业化、规范化、编译化

## 源仓库

- LandPPT:
  - https://github.com/sligter/LandPPT
- MiniMax Skills:
  - https://github.com/MiniMax-AI/skills

## 当前状态

本仓库当前是研究打包版本，包含：

- `LandPPT` 源码副本
- `MiniMax Skills` 源码副本
- 当前整合思路与架构建议

同时，`landppt/` 内已经开始承载第一阶段的实际实现，不再只是“旁边放一个建议文档”。

更准确地说，当前仓库状态是：

- 上层仍然是研究型整合仓库
- `landppt/` 内已经有一版正在生效的 `presentation_spec` Phase 1 实现
- 当前实现重点是：
  - 统一中间层
  - 自动刷新
  - prompt 消费
  - fallback renderer 消费
- 当前尚未完成的是：
  - 完整 HTML renderer 的强约束化
  - 原生 PPTX renderer
  - 端到端 Professional Mode

后续如果继续推进，建议下一步优先做：

1. 让正式 HTML 生成器不只“读 prompt 约束”，而是按 `render_hints` / `content_blocks` 做更确定性的 renderer 选择
2. 把 `agenda/content/conclusion` 的 fallback 变体继续扩成可复用布局族，而不是只覆盖最小示例
3. 继续把图表、图片、讲稿、备注挂进 `presentation_spec`
4. 在此基础上补 `PptxGenJS` renderer
