# DeepSeek Harness 借鉴 → Hermes 事件化插件层：完整工程报告

> **报告人**：Pioneer（云端）| 2026-08-16
> **协作**：Builder（Win11 本机）实现 + Pioneer（云端）验证，双 Agent 全流程
> **状态**：✅ 落地完成（云端 + Builder 双端部署验证通过）

---

## 一、项目设计

### 1.1 背景与目标

用户调研 `deepseek-ai/deepseek-harness`（DeepSeek 官方 Agent harness，npm 57+ 个 `@deepseek-ai/dsh-*` 包），认可其接口与插件化设计，方向确认：**借鉴其架构，改造我们现有 Hermes 系统**。本任务为评估 + 设计 + 落地三阶段。

核心问题：Hermes 是 Python、harness 是 TS/Node，**不能直接夺舍**。可移植的是三个语言无关设计模式：waterfall 事件钩子 / seam 抽象 / 事件溯源会话。

### 1.2 关键决策（P0 锁定）

| 决策 | 结论 | 理由 |
|:-----|:-----|:-----|
| 动本体 vs 外部插件层 | **外部桥接（零 patch）** | Hermes 升级频繁（0.16→0.19 连续动 plugins/compressor），本体 patch 是持续税；外部插件升级后照常工作 |
| 事件溯源会话 | **不做**（保留 SQLite） | 1.5GB state.db + FTS 检索 + active/compacted 压缩，迁移成本 >> 收益 |
| IoC 服务注入 | **暂不引入** | 无「插件 A 消费插件 B 服务」的真实需求；引入完整 DI 容器收益不大 |
| 工具注册表（Seam 落工具层） | **降级为可选** | 98 个工具全静态，直接收益有限 |
| 主循环拆分（5804 行） | **不做** | 收益（可读性）远小于风险（升级 patch 地狱） |

### 1.3 架构（外部桥接）

```
~/.hermes/plugins/hermes-event-bridge/        ← 零 patch 插件包
├── plugin.yaml          # manifest
├── protocol.py          # 事件名常量 + 返回契约 + ChainPlugin Protocol（纯模块，无宿主依赖）
├── bridge.py            # 宿主回调工厂（4 middleware + 3 hooks，每 seam 一个回调）
├── chain.py             # ChainRegistry：request 顺序覆盖 / execution async next_call 链 / observe 聚合
└── chains/              # 用户链插件（自动发现）
    ├── context_injector.py   # agent/pre-llm-call：多来源上下文合并注入
    ├── tool_guard.py         # agent/pre-tool-call：block 短路决策
    └── request_tuner.py      # agent/request：改 LLM 调用配置
```

**核心洞察**：Hermes 的 `middleware.py` **本身已是 waterfall 语义**（request 顺序覆盖 + execution next_call 链），协议层只做统一命名 + 薄桥接 + hooks 链式聚合。**借神为主、补神为辅、明确留白。**

### 1.4 事件协议 v1.1（8 事件 / 3 类）

| 类别 | 事件 | 宿主对接 | 语义 |
|:-----|:-----|:---------|:-----|
| request | `agent/request` / `agent/tool-request` | llm_request / tool_request middleware | waterfall 顺序覆盖（宿主原生） |
| execution | `agent/request-exec` / `agent/tool-exec` | llm_execution / tool_execution middleware | next_call 链（宿主原生） |
| observe | `agent/pre-llm-call` / `agent/pre-tool-call` / `agent/post-api-request` / `agent/turn-stopping` | pre_llm_call / pre_tool_call / post_api_request hooks | chain 聚合（bridge 实现） |

**契约修正（v1.1）**：pre-tool-call block 返回必须用 **`action`** key（宿主 `get_pre_tool_call_directive` plugins.py L2157 只认 `action ∈ {"block","approve"}`），`{"decision": "block"}` 会被静默跳过。云端实测发现，`protocol.block_decision()` 已改为同时返回 `{"action": "block", "decision": "block", "message": ...}` 兼容两端。

### 1.5 五条协议约束

1. 用户链插件**永不抛异常**（bridge 包住，异常只 log 不传播）
2. request 类只改 `request` key，不改其他字段
3. execution 类必须调 `next_call` **恰好一次**（宿主已强制单次保护）
4. observe 类永不阻塞（post_api_request 不做 I/O 等待）
5. **prompt cache 前缀保护**：context 注入走 user message，绝不碰 system prompt

---

## 二、内容指向

### 2.1 设计文档（~/Workplace/）

| 文档 | 内容 | 状态 |
|:-----|:-----|:-----|
| `DeepSeek-Harness-架构借鉴评估与设计方案.md` | v1 评估：6 核心包源码通读 + 三模式可行性 + 初步方案（516 行） | ✅ 存档 |
| `DeepSeek-Harness-架构借鉴-最终方案.md` | v2 定稿：外部桥接决策 + 范围/模块/对接点/风险/阶段（202 行） | ✅ P0 锁定 |
| `Hermes-事件协议-v1.md` | 事件协议 v1.1：8 事件表 + bridge 结构 + 验证矩阵 + 契约修正（195 行） | ✅ v1.1 锁定 |

### 2.2 实现代码（source 仓库）

| 位置 | 内容 | 归属 |
|:-----|:-----|:-----|
| `[builder]/hermes-event-bridge/` | 桥接插件完整实现（785 行 + README + test） | Builder（Pioneer 验证） |
| 云端部署副本 | `~/.hermes/plugins/hermes-event-bridge/`（含 v1.1 修复） | Pioneer |
| Builder 部署副本 | `~/AppData/Local/hermes/plugins/hermes-event-bridge/` | Builder |

### 2.3 情报笔记（hermes-notes）

| 笔记 | 小节 | 内容 |
|:-----|:-----|:-----|
| `情报与智库/情报-推理与Agent框架.md` | C6 | DeepSeek Harness 架构情报（四支柱/主循环/启示） |
| 同上 | C7 | Hermes vs Harness 架构对比（源码实测，5 维度） |

---

## 三、日志链接

| 日志 | 位置 | 内容 |
|:-----|:-----|:-----|
| 工作日志 2026-08-16 | `~/notes/工作日志/工作日志-2026-08-16.md` | DeepSeek Harness 拉取（Builder）、架构对比（Builder）、本报告落地全流程（Pioneer 补记） |
| 会话记录 | 本 session（2026-08-16） | 评估 → 设计 → 协议 → 验证全流程，session_search 可查 |
| GitHub | `xiyue-themoon/source` commit e723f87 + 本报告后续 | Builder 实现推送 + 根 README 登记 |

---

## 四、验证结果（双端一致）

| # | 验证项 | Builder（Win11 v0.19.0） | Pioneer（云端 v0.19.0） |
|:-:|:-------|:------------------------|:------------------------|
| 1 | 空链零回归 | ✅ PASS | ✅ PASS（真实对话 BRIDGE_OK 正常） |
| 2 | request 链生效 | ✅ PASS | ✅ PASS（max_tokens=32 真实截断） |
| 3 | 多链顺序覆盖 | ✅ PASS | ✅ PASS（单测 T2/T3） |
| 4 | tool block 短路 | ✅ PASS（单测层） | ✅ PASS（**宿主层，修复后** search_files 被拦截） |
| 5 | context 多源合并 | ✅ PASS | ✅ PASS（模型看到 `[event-bridge] PIONEER-CLOUD-VERIFY`） |
| 6 | execution wrap | ✅ PASS | ✅ PASS（单测 T6 terminal 恰好一次） |
| 7 | 升级兼容 | ✅ PASS | ✅ PASS（单测 T7 exploder 异常不传播） |

单测 14/14 双端一致 ✅

**发现并修复的问题**：
1. 🔴 **协议契约不匹配**（v1.1 修正）：block 返回 `decision` key vs 宿主认 `action` key → 云端实测发现 block 永不生效 → `protocol.block_decision()` 改双 key 兼容 → 宿主层验证通过
2. 🟡 **test 跨平台路径**：`test_event_bridge.py` L19/L28 硬编码 Windows 路径 → 云端无法直接运行 → 部署副本改 os.path.join（source 原版待 Builder 同步）

---

## 五、遗留事项

| 项 | 归属 | 说明 |
|:---|:-----|:-----|
| source 同步 v1.1 修复 | Builder | `protocol.py` block_decision 加 `action` key（云端已验，source 待同步） |
| source 同步 test 路径 | Builder | `test_event_bridge.py` 改 os.path.join 派生 |
| 真实链插件 | 双方按需 | 当前 3 个示例链（环境变量控制，默认关闭）；后续按需加记忆注入/请求调优 |
| P4 评估项 | 视需要 | 双轨制统一 / 工具注册表 / 事件日志，无需求驱动不做 |

---

## 六、结论

事件化插件层已双端落地。Hermes 的「形」被协议化（request/execution middleware 借神），「神」被补齐（observe 链式聚合 + block 契约修正），「留白」明确（IoC/事件溯源/工具注册等需求驱动再做）。零 patch 本体，升级无税。
