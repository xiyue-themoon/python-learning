# DeepSeek Harness 架构借鉴：最终方案 v2

> **委托**：Builder 补充委托 | 2026-08-16
> **基础**：v1 设计文档（/home/ubuntu/Workplace/DeepSeek-Harness-架构借鉴评估与设计方案.md）+ 本轮源码验证
> **阶段**：评估 + 设计定稿（不写实现代码）
> **状态**：✅ **P0 已锁定**（用户 2026-08-16 确认「借神+补神+留白」路径；IoC/事件溯源/工具注册暂不引入，等需求驱动）

---

## 一、Builder 对比结论验证（源码实测，非照单全收）

| # | Builder 结论 | 验证结果 | 源码证据 |
|:-:|:------------|:---------|:---------|
| 1 | invoke_hook() 是 emit 广播 | ✅ 属实 | `hermes_cli/plugins.py:1892-1927`——`callbacks = self._hooks.get(hook_name, [])` 顺序执行收集非 None 返回值，**无 next() 链**。`invoke_middleware`（L1937-1958）同为收集模式 |
| 2 | 无 IoC，插件间不能互相发现 | ✅ 属实 | `plugins.py:1253-1254`——`_hooks: Dict[str, List[Callable]]`、`_middleware: Dict[str, List[Callable]]`，纯回调注册，无服务注册表/发现机制 |
| 3 | SQLite 关系表 + active/compacted 标志位 | ✅ 属实 | `state.db` messages 表第 19/20 列即 `active INTEGER`、`compacted INTEGER`；压缩原地改写历史（`context_compressor.py` 大量 "COMPACTION — REFERENCE ONLY" 注入） |
| 4 | toolsets.py 静态 TOOLSETS dict | ✅ 属实 | `toolsets.py` 973 行，`TOOLSETS = {...}` at L96，纯静态 dict |
| 5 | conversation_loop.py 单文件巨函数 | ✅ 属实 | `agent/conversation_loop.py` 5804 行，`run_conversation` 一个函数驱动整轮 |

**Builder 对比结论全部属实**，无虚报。`invoke_hook` 甚至比 Builder 描述的还简单——`emit_collect` 语义（收集非 None），连 gateway/hooks.py 的 `emit_collect` 都还有 wildcard 匹配，plugins.py 的 invoke_hook 连这个都没有。

---

## 二、Builder 遗漏的关键事实（影响设计）

**F1：Hermes 已经在"模拟" waterfall——shell_hooks.py 的 block 决策**

`agent/shell_hooks.py:569-572` 明示：`pre_tool_call` 支持 Claude-Code-style 的 `{"decision": "block", ...}` 返回值，`get_pre_tool_call_block_message()` 读取。即：**Hermes 已经用"收集结果 + 调用点自行解释"模拟了短路决策**。

意义：这证明 waterfall 升级**不是理论空想，是有真实需求的**。但当前实现是脆弱的——多个插件都返回 block 时无优先级、无法替换请求、无法链式组合。这正是 harness waterfall 解决的。

**F2：双轨制——_hooks 与 _middleware 是两套平行系统**

`plugins.py` 同时维护 `_hooks`（invoke_hook）和 `_middleware`（invoke_middleware），二者注册/调用/语义完全平行但**互不感知**。升级时要统一，否则双轨制更乱。

**F3：pre_api_request 钩子已暴露请求体**

`conversation_loop.py:1356-1380` 的 `pre_api_request` 钩子传入了 `request=_request_payload`（完整请求体）。这是"改 LLM 调用配置"的天然挂点——harness 的 `agent/request` waterfall 对应物已存在，只是返回值未被调用点消费（收集后丢弃）。

**F4：主循环已有 4+ 个钩子点，不需要新增插入点**

现有：`pre_llm_call`（L882 附近）、`pre_api_request`（L1356）、`post` 类（L4485）、`pre_tool_call`/`post_tool_call`（shell_hooks）。**v1 设计里的"4 个插入点"大部分已存在**——升级语义即可，不必重写主循环。

---

## 三、借鉴优先级判断（对 Builder 3 点的回应）

### 3.1 🟢 Waterfall 事件语义 —— ✅ 认可，但建议**外部桥接**而非改本体

- **认可理由**：F1 证明需求真实存在；实现成本极低（~30-50 行）；收益立竿见影（pre_llm_call 链式注入、pre_tool_call 链式 block、pre_api_request 可改请求）。
- **修正**：Builder 说"改 pre_llm_call/pre_tool_call 为链式"——这暗示改 plugins.py 本体。**不必**。可以在外部写一个「协调插件」：它注册一个 Hermes 原生回调，内部再分发到我们的 EventBus.waterfall 链（详见 §五）。

### 3.2 🟡 Seam 抽象落工具层 —— ⚠️ 降级为"可选"，不是 Phase 2

- **认可价值**：TOOLSETS 静态 dict 确实落后，接口+注册表能支持动态扩展。
- **但**：Hermes 已有 `toolsets.py` 的 view 层（L596-609：`view only recognizes names literally present in TOOLSETS`），说明已有"动态 view"概念，静态 dict 是设计选择不是缺陷。
- **修正**：工具注册表改动的**直接收益有限**（我们现在没有动态注册工具的需求，98 个工具都是静态的）。它真正的价值是给未来（插件自定义工具）铺路。**降级为 P3 之后的备选项**。

### 3.3 🔴 事件溯源会话 —— ✅ 完全认可：不动

- 证据链完整：1.5GB SQLite + FTS 检索 + active/compacted 压缩 + 主循环直写。迁移成本极高，收益（审计/fork）当前无明确消费方。
- **唯一可做**：轻量审计日志（独立 JSONL，不碰 state.db），如果未来需要 fork/重放能力。**当前不需要，搁置**。

### 3.4 我补充的优先级项

| 项 | 优先级 | 理由 |
|:---|:-------|:-----|
| **决策点：动本体 vs 外部层** | 🔴 P0 | 影响后续所有改动的维护成本，必须先定 |
| **双轨制统一（_hooks/_middleware）** | 🟡 P2 | 不统一的话 waterfall 升级只覆盖一半 |
| 主循环拆分（5804 行） | ⚪ 不做 | 收益（可读性）远小于风险（升级 patch 地狱）；harness 的 phase 状态机价值在**设计**不在**行数** |

---

## 四、最终决策：动 Hermes 本体 vs 外部插件层

> 这是本轮最重要的决策点。Builder 明确指出：改 site-packages = 每次升级重打 patch。

### 4.1 三条路径对比

| 路径 | 做法 | 升级代价 | 能力上限 | 风险 |
|:-----|:-----|:---------|:---------|:-----|
| **A. 改本体** | 直接 patch plugins.py / conversation_loop.py | 每次升级重打 patch（已有先例：v0.19.0 打过 3 处） | 最高（可改调用点语义） | 高：patch 冲突、行为漂移 |
| **B. 外部桥接（推荐）** | 写一个 Hermes 原生插件，内部实现 EventBus.waterfall，作为唯一回调转发 | **零**（升级后插件照常工作） | 高（能覆盖 80% 场景） | 低：受限于宿主回调的传入参数 |
| **C. 混合** | 本体只做最小语义升级（如 invoke_hook 返回值消费），其余外部 | 低（1-2 处小 patch） | 最高 | 中 |

### 4.2 推荐：B 外部桥接（主）+ 极少量本体 patch（辅）

**为什么选 B**：
1. Hermes 升级频繁（0.16 → 0.19 一路在动 plugins/compressor/记忆），本体 patch 是持续税。**零 patch = 零升级税**，这是压倒性优势。
2. 宿主钩子点已足够多（F4：pre_llm_call/pre_api_request/pre_tool_call/post_tool_call），不需要改调用点。
3. 语义升级（收集 → 链式）是**转发层**的事，不需要动宿主。

**什么场景必须动本体**（C 的补充，暂不做，记录备选）：
- 如果未来需要「一个插件的返回值**真的替换请求体**」且调用点不消费返回值（如 pre_api_request 当前收集后丢弃）——这时才需要 1 处小 patch：让调用点消费 waterfall 链的最终值。

### 4.3 外部桥接架构

```
~/.hermes/plugins/hermes-event-bridge/
├── plugin.yaml            # manifest：provides_hooks: [pre_llm_call, pre_api_request, pre_tool_call, ...]
├── __init__.py            # register(ctx)：注册宿主回调 + 启动 EventBus
├── event_bus.py           # EventBus：emit/parallel/serial/bail/waterfall 五种模式（~120 行）
├── provider_registry.py   # ProviderRegistry：kind/scope/rank 注册表（~120 行，备选）
└── hooks/                 # 用户自定义链式插件（每个一个文件，注册到 EventBus）
    ├── context_injector.py   # pre_llm_call 链：注入记忆上下文（链式合并多个来源）
    ├── tool_guard.py         # pre_tool_call 链：block/allow 决策（可短路）
    └── request_tuner.py      # pre_api_request 链：改 maxTokens/provider 参数
```

**桥接原理**（关键，说明为什么零 patch）：

```python
# __init__.py —— 注册唯一的宿主回调，内部转发到 waterfall 链
def register(ctx):
    ctx.register_hook("pre_llm_call", bridge_pre_llm_call)
    ctx.register_hook("pre_api_request", bridge_pre_api_request)
    ctx.register_hook("pre_tool_call", bridge_pre_tool_call)
    # ... 每个 bridge_xxx 内部：
    #    results = await event_bus.waterfall(name, payload, next=default)
    #    return results   # 转发回 Hermes 宿主（保持原收集语义兼容）

async def bridge_pre_llm_call(**kwargs):
    payload = {"context_sources": [], "kwargs": kwargs}
    final = await event_bus.waterfall("agent/pre-llm-call", payload,
                                      lambda: {"context": ""})
    # 多个链节点各自 append context_sources，最终合并注入
    return {"context": "\n\n".join(final["context_sources"])}
```

**注意**：宿主 `invoke_hook` 的返回值是「收集所有回调的非 None 结果」——bridge 作为**唯一**回调返回一个聚合结果即可，与宿主语义天然兼容。链式发生在 bridge 内部，宿主无感知。

---

## 五、最终方案（范围/模块/对接点/风险/阶段）

### 5.1 范围

| 动作 | 范围 | 影响 |
|:-----|:-----|:-----|
| **新增** | `~/.hermes/plugins/hermes-event-bridge/` 插件包（~250-400 行） | 零风险，纯增量 |
| **新增** | 事件协议文档（事件名/参数/返回契约） | 双 Agent 对齐用 |
| **修改** | 零（推荐路径下不动 site-packages） | 升级无税 |
| **备选** | 1 处本体 patch（pre_api_request 消费链式结果），仅当需要真替换请求体时 | 记录待定 |

### 5.2 模块划分（外部插件包内）

| 模块 | 职责 | 参考 |
|:-----|:-----|:-----|
| `event_bus.py` | 五种 dispatch 模式 + 监听器注册/卸载/scope | cordis events.ts |
| `bridge.py` | 宿主钩子 → EventBus 转发层（每个宿主钩子一个 bridge 函数） | 自定义 |
| `hooks/context_injector.py` | pre_llm_call 链：多来源上下文合并注入 | dsh pre-step |
| `hooks/tool_guard.py` | pre_tool_call 链：block/allow 短路决策 | dsh pre-step |
| `hooks/request_tuner.py` | pre_api_request 链：改 LLM 调用配置 | dsh request |
| `provider_registry.py`（备选） | 工具/服务注册表 + scope 分层 | dsh-skill seam |

### 5.3 对接点（宿主钩子 → EventBus 事件映射）

| 宿主钩子 | 宿主位置 | EventBus 事件 | 语义升级 |
|:---------|:---------|:--------------|:---------|
| `pre_llm_call` | conversation_loop L882 附近 | `agent/pre-llm-call` | 广播收集 → 链式合并注入 |
| `pre_api_request` | conversation_loop L1356 | `agent/request` | 只读 → 可改配置（备选） |
| `pre_tool_call` | model_tools.py / shell_hooks | `agent/pre-tool-call` | 收集 block → 链式短路决策 |
| `post_tool_call` | model_tools.py / shell_hooks | `agent/post-tool-call` | 保留收集语义（只读通知） |
| `post_*`（L4485） | conversation_loop L4485 | `agent/turn-stopping` | 保留收集语义 |

### 5.4 迁移风险

| 风险 | 等级 | 缓解 |
|:-----|:-----|:-----|
| 宿主升级改变钩子签名/参数 | 🟡 中 | bridge 层做参数兼容适配（kwargs 透传，不依赖具体字段）；升级后跑一次钩子冒烟测试 |
| 宿主升级移除某钩子 | 🟢 低 | bridge 对缺失钩子容错（try/except 注册）；事件协议文档标注依赖钩子清单 |
| 双 Agent 两端行为不一致 | 🟡 中 | 事件协议文档先行；同一套 hooks/ 目录双端部署 |
| 链式插件死循环（A 调 B 调 A） | 🟢 低 | EventBus 加调用深度上限 + 循环检测 |
| bridge 异常拖垮主循环 | 🔴 高 | 继承宿主容错：bridge 内部 try/except 包住所有链调用，异常只 log 不抛出（与 invoke_hook L1920 同款） |

### 5.5 阶段划分（最终版）

| 阶段 | 内容 | 依赖 | 验收标准 |
|:-----|:-----|:-----|:---------|
| **P0 决策锁定** | 采用外部桥接路径；确认不动本体 | 无 | 本设计文档审过 |
| **P1 桥接骨架** | 插件包 + event_bus.py（5 模式）+ bridge.py（3 个宿主钩子转发） | P0 | 单测 5 模式；宿主原行为零回归（bridge 空链时透传默认值） |
| **P2 首个真实链** | hooks/context_injector.py（pre_llm_call 多来源上下文合并） | P1 | 两个来源同时注入，链式合并生效；单来源行为与现状一致 |
| **P3 决策链** | hooks/tool_guard.py（pre_tool_call 短路）+ request_tuner.py | P1 | block 短路生效；allow 时透传 |
| **P4 评估项** | 双轨制统一 / 工具注册表 / 事件日志 | 视需要 | 单独评估，不预设必做 |

> **P0+P1 是核心交付**（~300 行，零 patch，立即可用）。P2/P3 是演示价值（证明链式能力）。P4 全部可选。

### 5.6 验证方式

1. **单测**：event_bus 5 模式（waterfall 否决链、serial 短路、bail 同步短路）。
2. **宿主回归**：bridge 空链时跑一次真实对话，确认与未装插件时行为一致（关键：prompt cache 前缀不被破坏——注入的 context 仍走 user message，不碰 system prompt，遵循 plugins.py L1906 的约束）。
3. **链式验证**：注册 2 个 context_injector 源，确认合并注入；注册 tool_guard block，确认工具被拦截。
4. **升级测试**（关键卖点）：备份插件包 → 模拟宿主升级（改一个钩子签名）→ 确认 bridge 兼容或给出明确的失败日志。

---

## 六、对 Builder 的说明

1. **你的 5 条对比结论全部验证属实**，源码行号已附（§一），可直接引用。
2. **优先级判断**：Waterfall ✅ 做（但外部桥接）；Seam 落工具层 ⚠️ 降级为可选；事件溯源 ✅ 不动。新增 P0 决策点（动本体 vs 外部层）——**这是最重要的一条**。
3. **关键分歧点**：你在委托里说"改 pre_llm_call/pre_tool_call 为链式"（暗示改 plugins.py 本体），我建议**外部桥接零 patch**。理由：Hermes 升级频繁（0.16→0.19 连续动 plugins/compressor），本体 patch 是持续税；宿主钩子点已够多，语义升级可以在转发层完成。
4. **请重点审 §四（外部桥接）**：这是与 v1 最大的差异。如果你认同，锁定 P0，我出事件协议文档 v1（事件名/参数/返回契约），你再实现。
5. C6/C7 情报笔记仍未同步到云端（本地只见 C1-C5），建议 Builder 推送共享笔记库。
