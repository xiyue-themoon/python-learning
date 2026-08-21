# DeepSeek Harness 架构借鉴：评估与设计方案

> **委托**：Builder → Pioneer | 2026-08-16
> **阶段**：评估 + 设计（不写实现代码）
> **源码**：npm 拉取 deepseek-ai/dsh-* 6 核心包，解包通读于 /tmp/dsh-npm/
> **对应 Hermes**：0.19.0（Python，本机 venv 源码）

---

## 〇、结论速览（TL;DR）

1. **三个设计模式都能移植**，成本排序：Waterfall 事件钩子（低）< Seam 抽象（中）< 事件溯源会话（高）。
2. **Waterfall 是白送的**——核心逻辑只有 10 行闭包链，Python 的 asyncio + 闭包天然支持，且 Hermes 已有 `gateway/hooks.py` 的 HookRegistry 雏形，只需补 `waterfall`/`serial`/`bail` 三种 dispatch 模式。
3. **Seam 抽象（接口包+实现包分离）**对应 Python 的 `typing.Protocol`/ABC，Hermes 已有 LLM provider/adapter 概念，缺的是**统一注册表 + 分层 scope**（dsh-skill 的 `registerProvider + rank + scope` 正是 Hermes skill 系统缺的）。
4. **事件溯源会话是最重的**：Hermes 的 `state.db`（SQLite messages 表 + FTS）是「写后读」模型，与 append-only log 理念冲突。**不建议替换存储层**，建议增量引入「session 事件日志」作为审计/派生辅助层。
5. **推荐策略：不整体夺舍，把三模式作为「事件化插件层」增量引入 Hermes**，保留全部现有基建（skills/cron/gateway/记忆/工具集），分 4 阶段演进。

---

## 一、deepseek-harness 源码通读

### 1.1 包结构

| 包 | 版本 | 行数(核心) | 职责 |
|:---|:-----|:----------|:-----|
| @deepseek-ai/cordis | 4.0.1 | src 2693 | IoC 容器：Context/Service/事件总线/Fiber |
| @deepseek-ai/dsh-agent | 0.1.0-rc.6 | 794 | Agent 注册表 + 工厂 + initiator 溯源 |
| @deepseek-ai/dsh-agent-loop | 0.1.0-rc.6 | 1295 | ReactLoopAgent 主循环（turn/step 双循环） |
| @deepseek-ai/dsh-session | 0.0.1-rc.1 | 1841 | 事件溯源会话（append-only log + surface 投影） |
| @deepseek-ai/dsh-llm | 0.0.1-rc.1 | 1391 | LLM 适配层：adapter 注册 + 重试策略 |
| @deepseek-ai/dsh-skill | 0.0.1-rc.1 | 565 | Skill 能力缝（Service Definition + provider 注册） |

### 1.2 cordis：IoC 容器（最底层）

**Context = Proxy**。属性读取走 `ReflectService.handler` 的服务解析器；`extend()`/`isolate()`/`intercept()` 创建子上下文实现作用域隔离（原型链继承 + 符号键 shadow）。核心机制：

```ts
// context.ts L42-84
class Context {
  constructor() {
    const self = new Proxy<this>(this, ReflectService.handler)  // 属性读取动态解析服务
    this.fiber = new Fiber(self, {}, Object.create(null), null, () => [])
    this.reflect = new ReflectService(self)
    this.registry = new RegistryService(self)
    this.events = new EventsService(self)
    this.logger = new LoggerService(self)
    return self
  }
  extend(meta = {})      // 子上下文（原型继承）
  isolate(name, label?)  // 独立服务 scope
  intercept(name, config) // 服务配置拦截
}
```

**事件总线五种 dispatch 模式**（events.ts L32）：

| 模式 | 语义 | 用途 |
|:-----|:-----|:-----|
| `emit` | 同步触发，忽略返回值 | 通知（agent/error 等） |
| `parallel` | 并发 await 全部 | 广播 |
| `serial` | 顺序 await，遇 bail 值停止 | 决策链（agent/turn-stopping） |
| `bail` | 同步顺序，首个非空停止 | 短路判定 |
| `waterfall` | 洋葱链式包裹 next() | 请求改造 / 拦截（agent/request） |

**waterfall 实现全貌**（events.ts L234-243）——这是本评估的核心，全文只有 10 行：

```ts
waterfall(...args: any[]) {
  const cbs = this.dispatch('waterfall', args)
  const inner = args.pop()                    // 最后一个参数是内置行为
  const next = () => {
    const cb = cbs.shift() ?? inner           // 逐个取出监听器，耗尽则执行内置
    return cb(...args)
  }
  args.push(next)
  return next()                               // 最外层监听器先跑，不调 next 即否决
}
```

**Service 基类**（service.ts）：`constructor(ctx, name)` 里调 `ctx.reflect.provide(name, self)` 完成注册，随 fiber 卸载自动清理。这是「声明合并注入」的运行时底座——TS 的 `declare module` 只提供编译期类型安全，运行时就是 service 注册表。

**关键洞察**：cordis 的事件/服务/作用域三层都是**运行时注册表 + 原型链隔离**，没有任何魔法。Python 用 dict + 类注册 + contextvar 可以等价实现，且不需要 Proxy（Python 有 `__getattr__`）。

### 1.3 dsh-agent + dsh-agent-loop：主循环

**Agent 公开接口仅 6 方法**（agent.d.ts L12-60）：

```
send(message, target, wakeup)  // 入队
followup(input)                // 追加
steer(input)                   // 转向
inject(input)                  // 注入
cancel(cause, options)         // 取消
whenIdle()                     // 等待空闲
```

**主循环**（agent-loop index.js L477-605）：

```js
async kick() {
  while (await this.turn());          // 一个 driver 循环跑到无 pending
}

async turn() {
  phase.turn++
  while (true) {
    const decision = await this.preStep(target, {turn, step})
    if (decision.kind === 'reject') return false    // pre-step 钩子否决
    this.session.append('step/start', {...})
    for (const msg of decision.messages) this.session.append('user/message', msg)
    const stepEnd = await this.step(decision.assembly)   // LLM 调用
    this.session.append('step/end', {...})
    if (turnEnds && inbox.nextStep.empty) {
      await this.dispatch.serial('agent/turn-stopping', {turn, signal})  // turn 结束前干预
      break
    }
  }
}
```

**四个关键事件钩子**（就是插件化的根源）：

| 钩子 | dispatch 模式 | 位置 | 能干什么 |
|:-----|:-------------|:-----|:---------|
| `agent/pre-step` | waterfall | preStep L501 | 决定 step 进不进；改 messages（注入 context）；否决（reject） |
| `agent/request` | waterfall | buildRequest L685 | 改 LLM 调用配置（provider/model/maxTokens/任意参数） |
| `agent/request-error` | waterfall | step L630 | 重试决策（返回 `{kind:'retry'}` 则重来） |
| `agent/turn-stopping` | serial | turn L565 | turn 结束前干预（清理/记录/追加任务） |

**step 内部**（L606-664）：buildRequest（经 waterfall 改造配置）→ `llm.stream()` → 每个 chunk append 到 session log → BlockAssembler 聚合 → error/aborted 时走 `agent/request-error` waterfall → 完成则 append `assistant/message` → 提取 tool-call → executeToolCalls → 工具结果经 `acceptContext` 塞回 next-step inbox。

**关键洞察**：整个主循环**没有任何业务逻辑内嵌**，全部通过 4 个钩子点暴露。换插件 = 换行为，主循环代码不动。这就是插件化优秀的根源。

### 1.4 dsh-session：事件溯源会话

**核心模型**（index.js L1258-1509）：

```
Session
├── log: SessionEvent[]          # append-only，seq = log.length 连续
├── surfaceManager: SurfaceManager  # 增量投影：哪些事件进 LLM 可见面
└── header                      # 存储元数据（cwd/lineage/seedLength），不进 log

append(type, data, opts) -> event   # 校验 JSON 可序列化 + surface 契约，deep-freeze 后入 log
deriveMessages() -> Message[]       # 增量折叠 surface 节点 → LLM 消息历史
```

**事件类型**：`turn/start`、`step/start`、`user/message`（surfaceOp: append）、`assistant/chunk`、`assistant/message`（surfaceOp: append, sourceEventSeqs: [chunk seqs]）、`step/end`、`turn/end`、`request/header`、`request/context` 等。

**surface 投影**（surface.ts）：每个 message-producing 事件声明 `surfaceOp: append|replace` + `sourceEventSeqs`。`foldSurface()` 重放全 log 得到当前可见面；`SurfaceManager` 增量维护，`replaceGeneration` 单调递增。**替换语义**（replace）允许「改写历史可见面」而不破坏 append-only log——这是 compaction/fork 的基础。

**deriveMessages 增量缓存**（L1494-1509）：只处理 `nodes.slice(derivedNodes)` 的新节点，generation 变了才重建，性能接近零开销。

**持久化是插件**（L1532-1534 注释明确）：store 不实现持久化，**持久化插件订阅 `session/event` 异步 flush**。这跟 Hermes 的 SQLite 直写模型完全相反。

**fork/恢复**：`Session.create(id, seed, header)` 用 seed 事件数组重建；`fromRestore()` 校验格式/连续性后接管。子会话 fork 父 log 的平衡前缀。

**关键洞察**：事件溯源的价值 = **LLM 消息历史是派生值不是存储值**。改一个事件（replace）就能让所有后续请求看到新历史，且 log 永远可审计。代价 = 所有写入要走事件契约校验 + 投影器。

### 1.5 dsh-skill：Seam 抽象范例

**Service Definition 角色**（index.d.ts）：`SkillService` 只做三件事——合并 provider 目录、按名字解析赢家、暴露 summary/definition。**它不知道 skill 从哪来**。

**Provider 接口**（L168-188）只有两个方法：
```ts
interface SkillProvider {
  readonly list: (options) => Promise<SkillCandidate[] | Observation>  // 列出候选
  readonly get: (candidate, options) => Promise<SkillDefinition | undefined>  // 加载正文
}
```

**注册与分层**：`registerProvider()` 注册进**调用上下文所在 scope 的 layer**；读时按 `scope chain` 合并——最近层胜出，同层内按 rank 决胜。`@deepseek-ai/dsh-skill-local`（本地目录）、windows-acl（沙盒实现）都是这个接口的实现包，**换实现 = 换安全边界**。

**关键洞察**：seam 的本质 = 「接口包定义契约，实现包可替换」。Python 里就是 `Protocol` + 注册表，Hermes 的 LLM adapters（anthropic_adapter.py / bedrock_adapter.py 等）已经是这个思想，缺的是**统一注册 + 分层覆盖**。

### 1.6 dsh-llm：adapter + 重试

- `prepareCall(config, signal)`：绑定 adapter 路由，解析 exact-model 默认（reasoningEffort/contextWindow 等），返回 `{config, adapterDefaults, context}`。
- `retry-policy`：provider 自持重试策略（normal: 限次限码 / always: 无限重试），bounded 指数退避 + 对称 jitter。
- `agent/request-error` waterfall 执行重试决策，策略是 provider 配置不是全局。

**关键洞察**：重试策略**归属 provider**（配置在 provider route 上），决策点挂在 waterfall 钩子上——不污染主循环。

---

## 二、可行性评估：三模式移植到 Hermes（Python）

> 核心问题：Hermes 是 Python、harness 是 TS/Node，不直接"夺舍"。下面逐一评估三个语言无关设计模式。

### 2.1 Waterfall 事件钩子 —— ✅ 直接可行，成本最低

**本质**：洋葱中间件链（middleware chain）。10 行闭包逻辑，**语言无关**。

**Python 实现对照**：

| TS 元素 | Python 等价物 |
|:--------|:-------------|
| 闭包 + shift() | `list.pop(0)` / `itertools` 消费 |
| async 链 | `asyncio` 原生支持 |
| `next()` 不调即否决 | 不调 `await next()` 即否决 |
| 类型安全（declare module） | `typing.Protocol` + 事件名常量 |

**Hermes 现状**（已确认）：`gateway/hooks.py` 已有 `HookRegistry`：
- `discover_and_load()`：扫 `~/.hermes/hooks/*/HOOK.yaml + handler.py`
- `emit(event, ctx)`：fire-and-forget，丢返回值
- `emit_collect(event, ctx)`：收集非 None 返回值（已用于 `command:*` 决策钩子）
- 事件：`gateway:startup` / `session:start|end|reset` / `agent:start|step|end` / `command:*`

**缺口**：没有 `waterfall` / `serial` / `bail` 三种模式。`emit_collect` 只收集结果，**不能改造请求、不能链式否决**。

**结论**：在 `HookRegistry` 上加一个 `waterfall(event, ctx, next)` 方法即可获得 90% 的 dsh 钩子能力。改动 ~30 行，不破坏现有 `emit`/`emit_collect` 调用方。**这是三模式里性价比最高的。**

### 2.2 Seam 抽象（接口包 + 实现包分离）—— ✅ 可行，成本中

**本质**：接口定义契约 + 实现可替换。**语言无关**。

**Python 实现对照**：

| TS 元素 | Python 等价物 |
|:--------|:-------------|
| `interface SkillProvider` | `typing.Protocol`（结构子类型，无需继承） |
| 分层 scope（isolate/layer） | contextvar 或显式 scope key |
| rank 决胜 | 注册表内排序 |
| 换实现 = 换安全边界 | 同 Protocol 不同实现类，入口注入 |

**Hermes 现状**（已确认）：
- LLM 侧已有 adapter 模式：`agent/anthropic_adapter.py`、`agent/bedrock_adapter.py`、`agent/codex_responses_adapter.py` 等 → **已经是 seam，只是没有统一注册表**
- skill 系统：`~/.hermes/skills/` 目录 + `skill_manage`，但**没有 provider 概念**——只有本地目录一个来源，没有分层覆盖（不能"这个 scope 用这套 skill"）

**结论**：seam 模式在 Hermes 里**局部已存在**（LLM adapters），缺的是：
1. 统一的 provider 注册表（list/get 两方法接口）
2. scope 分层（skill 按 agent/目录/项目分层覆盖）
3. skill 来源可插拔（本地目录 / 远程 / 内嵌）

**风险**：skill 系统改动影响面大（50+ skill、Builder 双端同步），必须保持向后兼容。

### 2.3 事件溯源会话 —— 🟡 可行但成本高，需分阶段

**本质**：LLM 消息历史是**派生值**（从 append-only 事件日志投影），不是存储值。**语言无关但存储模型冲突**。

**Hermes 现状**（已确认）：`state.db`（SQLite 1.5GB）：
- `sessions` / `messages` 表 + `messages_fts` 全文索引（session_search 用）
- 模型：**写后读**——消息直接 INSERT，读时 SELECT
- 主循环 `conversation_loop.py`（5804 行）直接读写 messages

**冲突点**：

| 维度 | Hermes 现状 | 事件溯源 |
|:-----|:-----------|:---------|
| 存储 | SQLite messages 表 | append-only 事件 log |
| 读历史 | SELECT 查询 | foldSurface 投影 |
| 改写 | UPDATE 消息 | surfaceOp: replace 事件 |
| 持久化 | 直写 DB | 订阅事件异步 flush |
| 检索 | FTS 全文索引 | 无原生检索（需另建索引） |

**为什么不能直接替换**：
1. session_search 依赖 FTS 索引——事件溯源 log 里没有全文索引，检索性能会崩
2. 1.5GB 存量数据迁移成本高，风险大
3. conversation_loop 直接读写 messages，改造点散布在 5804 行主循环里

**可行路径（增量）**：
- **不替换存储层**。保留 SQLite 作为权威存储。
- **增量引入「session 事件日志」**：在关键生命周期点（turn/start、step/start、user/message、assistant/message、step/end、turn/end、request/header、tool/call）同时 append 一条轻量事件记录（JSON Lines 文件或独立表）。
- 用途：**审计 + fork/重放**（子会话从事件日志派生初始历史）+ 未来 compaction 实验。
- 双写成本：每次 append 多一条写入，可以异步批量。

**结论**：完整事件溯源**不建议**在 Hermes 落地（检索模型冲突、迁移成本高）；**轻量事件日志**值得做（审计 + fork 能力），作为独立辅助层，不与现有存储耦合。

### 2.4 三模式可行性汇总

| 模式 | 可行性 | 成本 | 收益 | 建议 |
|:-----|:-------|:-----|:-----|:-----|
| Waterfall 钩子 | ✅ 高 | 低（~30 行） | 高（插件化根基） | **Phase 1 做** |
| Seam 抽象 | ✅ 中 | 中（注册表 + 分层） | 中高（skill/工具可插拔） | **Phase 2 做** |
| 事件溯源会话 | 🟡 部分 | 高 | 中（审计/fork） | **Phase 3 做轻量版** |

---

## 三、设计方案：Hermes 事件化插件层

### 3.0 设计原则

1. **不放弃现有基建**：skills/cron/gateway/记忆系统/工具集全部保留，事件化是**增量**不是**替换**。
2. **主循环最小侵入**：conversation_loop.py 只在 4 个关键点插 hook 调用，不重写。
3. **向后兼容**：现有 `emit`/`emit_collect` 调用方不动，新增模式是超集。
4. **双 Agent 对齐**：设计对 Builder（Win11）和 Pioneer（云端）同构，两端共用同一套事件协议。
5. **成本纪律**：事件层零依赖（标准库 asyncio），不引第三方框架。

### 3.1 目标架构

```
┌─────────────────────────────────────────────────────────┐
│                     Hermes 事件化插件层                     │
│                                                         │
│  ┌─────────────┐   ┌────────────────────────────────┐   │
│  │  事件总线    │   │        插件注册表 (seam)         │   │
│  │ EventBus    │   │  ProviderRegistry              │   │
│  │  emit       │   │  register(name, impl)          │   │
│  │  parallel   │   │  scope 分层                     │   │
│  │  serial     │   │  rank 决胜                     │   │
│  │  bail       │   │                                │   │
│  │  waterfall  │   │  skill-provider               │   │
│  └─────┬───────┘   │  tool-provider                │   │
│        │           │  llm-provider (已有 adapter)   │   │
│        │           └────────────────────────────────┘   │
│        │                                                 │
│        ▼                                                 │
│  ┌────────────────────────────────────────────────┐   │
│  │           Agent 主循环钩子点 (4 处)              │   │
│  │                                                │   │
│  │  agent/pre-step  (waterfall) ← 进不进 step     │   │
│  │  agent/request   (waterfall) ← 改 LLM 配置     │   │
│  │  agent/request-error (waterfall) ← 重试决策    │   │
│  │  agent/turn-stopping (serial)  ← turn 结束前   │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │         Session 事件日志 (轻量审计层)             │   │
│  │  append(type, data) → JSONL / 独立表            │   │
│  │  fork(seed) → 子会话派生初始历史                  │   │
│  └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘

        ↕ 兼容层：现有基建照常工作
┌─────────────────────────────────────────────────────────┐
│  skills (skill_manage)  │  cron  │  gateway/hooks.py     │
│  记忆系统 (MEMORY/USER)  │  tools (98 个)  │  state.db    │
└─────────────────────────────────────────────────────────┘
```

### 3.2 模块划分（新增 4 个模块，~800-1200 行）

| 模块 | 路径建议 | 职责 | 参考 |
|:-----|:---------|:-----|:-----|
| event_bus | `agent/event_bus.py` | 五种 dispatch 模式 + 监听器注册/卸载 | cordis events.ts |
| provider_registry | `agent/provider_registry.py` | 通用 Provider 注册表 + scope 分层 + rank | dsh-skill SkillService |
| agent_hooks | `agent/agent_hooks.py` | 4 个主循环钩子点的常量 + 调用封装 | dsh-agent-loop |
| session_event_log | `agent/session_event_log.py` | 轻量事件日志（append/fork/投影） | dsh-session |

### 3.3 核心接口设计

**① EventBus（对应 Waterfall 模式）**

```python
class EventBus:
    """基于 asyncio 的事件总线，五种 dispatch 模式。"""

    def on(self, name: str, listener: Callable, *, prepend: bool = False,
           scope: str | None = None) -> Callable[[], None]:
        """注册监听器，返回卸载函数。scope 用于隔离。"""

    def emit(self, name: str, **ctx) -> None:
        """同步触发，忽略返回值（fire-and-forget）。"""

    async def parallel(self, name: str, **ctx) -> None:
        """并发触发全部监听器。"""

    async def serial(self, name: str, **ctx) -> Any:
        """顺序触发，首个 bail 值（非 None/False）停止并返回。"""

    def bail(self, name: str, **ctx) -> Any:
        """同步顺序，首个非空停止。"""

    async def waterfall(self, name: str, ctx: dict, next: Callable) -> Any:
        """洋葱链：每个监听器包住 next()，不调即否决。"""
```

waterfall 的 Python 实现（等价 10 行 TS）：

```python
async def waterfall(self, name: str, ctx: dict, next: Callable) -> Any:
    listeners = self._listeners(name)          # 按注册顺序取
    async def chain(i: int) -> Any:
        if i < len(listeners):
            return await listeners[i](ctx, lambda: chain(i + 1))
        return await next()
    return await chain(0)
```

**② ProviderRegistry（对应 Seam 抽象）**

```python
class ProviderRegistry:
    """统一 provider 注册表：接口包 + 实现包分离。"""

    def register(self, kind: str, name: str, impl: Any, *,
                 rank: int = 500, scope: str | None = None) -> None:
        """kind='skill'|'tool'|'llm'|'fs'|'sandbox'，impl 实现对应 Protocol。"""

    def resolve(self, kind: str, name: str, *, scope: str | None = None) -> Any:
        """按 scope 链 + rank 决胜，返回赢家实现。"""

    def list(self, kind: str) -> list[ProviderSummary]:
        """列出某 kind 的全部 provider 摘要。"""

# 契约定义（接口包）
class SkillProvider(Protocol):
    def list(self, options: SkillLookupOptions) -> list[SkillCandidate]: ...
    def get(self, candidate: SkillCandidate, options: SkillLookupOptions) -> SkillDefinition | None: ...
```

**③ Agent 钩子（对应 dsh-agent-loop 4 钩子）**

```python
# agent_hooks.py — 事件名常量 + 调用点封装
PRE_STEP        = "agent/pre-step"          # waterfall: 决定 step 进不进
REQUEST         = "agent/request"           # waterfall: 改 LLM 调用配置
REQUEST_ERROR   = "agent/request-error"     # waterfall: 重试决策
TURN_STOPPING   = "agent/turn-stopping"     # serial: turn 结束前干预
```

conversation_loop.py 插入点（4 处，各 2-4 行）：

```python
# ① preStep 前（约 L748 附近 step_callback 之后）
decision = await bus.waterfall(PRE_STEP, {"turn": turn, "step": step, "messages": messages},
                               lambda: {"kind": "enter", "messages": messages})
if decision["kind"] == "reject":
    break

# ② buildRequest 后、llm.stream 前（改配置）
config = await bus.waterfall(REQUEST, {"turn": turn, "step": step},
                             lambda: default_config)

# ③ LLM 调用异常时（重试决策）
action = await bus.waterfall(REQUEST_ERROR, {"failure": exc, "retry_count": n},
                             lambda: None)
if action and action.get("kind") == "retry":
    continue

# ④ turn 结束前
await bus.serial(TURN_STOPPING, {"turn": turn})
```

**④ Session 事件日志（轻量版）**

```python
class SessionEventLog:
    """append-only 事件日志，独立于 state.db，用于审计 + fork。"""

    def append(self, session_id: str, type: str, data: dict) -> int:
        """追加事件，返回 seq。异步批量落盘。"""

    def replay(self, session_id: str, *, upto: int | None = None) -> list[Event]:
        """重放事件序列。"""

    def fork(self, session_id: str, *, upto: int | None = None) -> list[Event]:
        """取平衡前缀作为子会话 seed。"""
```

### 3.4 对接点（与现有基建）

| 现有基建 | 对接方式 | 改动量 |
|:---------|:---------|:-------|
| gateway/hooks.py | EventBus 复用其 HOOK.yaml 发现机制，**新增 waterfall/serial/bail 模式** | ~30 行 |
| skills 系统 | skill_manage 保留为默认 provider；ProviderRegistry 加 skill-provider 接缝，允许 scope 覆盖 | 中 |
| LLM adapters | 已有 adapter 模式，注册进 ProviderRegistry（llm kind），不重写 | 小 |
| cron | cron tick → `bus.emit("cron:tick", job_id=...)`，可选 | 小 |
| 记忆系统 | 不接管。MEMORY/USER 文本注入保持原样 | 零 |
| 工具集（98 个） | 工具注册进 ProviderRegistry（tool kind），调用点包一层 pre-call 钩子 | 中 |
| state.db | 不动。session_event_log 是独立辅助层 | 零 |
| 双 Agent 同步 | 事件协议文档化（事件名/参数/返回契约），两端各自实现同一协议 | 文档 |

### 3.5 重写范围 vs 保留范围

**新增**（~800-1200 行）：
- `agent/event_bus.py`（~150 行）
- `agent/provider_registry.py`（~150 行）
- `agent/agent_hooks.py`（~80 行）
- `agent/session_event_log.py`（~200 行）
- 测试 + 事件协议文档

**修改**（~60 行）：
- `gateway/hooks.py`：+waterfall/serial/bail 模式（~30 行）
- `agent/conversation_loop.py`：4 处钩子插入点（~20 行）
- 可选：cron 触发点（~10 行）

**不动**：
- state.db 存储层、现有 98 个工具、现有 skills、记忆系统、现有 hooks 调用方

### 3.6 迁移风险

| 风险 | 等级 | 缓解 |
|:-----|:-----|:-----|
| conversation_loop.py 是 5804 行巨函数，插错点影响主循环 | 🔴 高 | 4 个插入点全部**无默认行为**（没有监听器时零开销短路），先加日志后加逻辑；改动前 git 快照 |
| 双 Agent 两端事件协议不一致 | 🟡 中 | 协议文档先行；Builder 端实现前先对齐文档 |
| skill provider 化后现有 skill_manage 行为漂移 | 🟡 中 | Phase 2 默认 provider 保持原行为，scope 覆盖是纯增量 |
| 事件日志双写性能 | 🟢 低 | 异步批量落盘；审计层可开关 |
| 上游升级冲突（v0.19.0 后官方改动） | 🟡 中 | 遵循既有上游升级决策原则：官方有利则接受，冲突则以用户为主恢复定制 |

### 3.7 阶段划分

| 阶段 | 内容 | 依赖 | 验收标准 |
|:-----|:-----|:-----|:---------|
| **P1 事件总线** | event_bus.py + hooks.py 升级（waterfall/serial/bail） | 无 | 单测覆盖 5 模式；现有 hooks 调用方零回归 |
| **P2 主循环钩子** | conversation_loop 插 4 点 + agent_hooks.py | P1 | 空钩子零开销；注入测试插件验证 4 点都触发 |
| **P3 Seam 抽象** | provider_registry.py + skill-provider 接缝 + LLM adapters 注册 | P1 | skill 默认 provider 行为与现状一致；scope 覆盖生效 |
| **P4 事件日志** | session_event_log.py + 关键点 append + fork 演示 | P1 | 审计可查；子会话能从事件日志派生初始历史 |

> P1/P2 是必做（插件化根基）；P3 视需要（skill 分层有价值但影响面大）；P4 是可选项（审计收益明确，fork 场景待定）。

### 3.8 验证方式

1. **单测**：event_bus 5 模式各一个测试（含 waterfall 否决链）。
2. **回归**：现有 gateway hooks 场景（agent:start/step/end）跑一遍，确认 emit/emit_collect 行为不变。
3. **端到端**：注入一个测试插件（pre-step 注入 context + request 改 maxTokens），跑一次真实对话确认生效。
4. **双 Agent**：Builder 侧跑同一套单测，两端事件协议对齐。

---

## 四、对 Builder 的说明与建议

1. **本评估基于 npm 拉取的 6 核心包源码通读**（/tmp/dsh-npm/，版本 rc.6/rc.1），与 Win11 侧 unpacked/ 版本一致（同为 npm pack）。
2. **C6 情报笔记**（hermes-notes/情报-推理与Agent框架.md）本地尚未同步——C6 小节只有 Builder 侧有。建议你同步到共享笔记库，我这边看到的是 C1-C5。
3. **建议下一步**：你审这份设计文档（反向审查模式），重点看 3.5 重写范围是否可接受、P2 主循环 4 个插入点是否与 Win11 侧 Hermes 版本（v0.16.0）源码匹配。对齐后锁定版本，再进实现阶段。
4. **实现分工建议**：P1 事件总线 + P2 主循环钩子（核心，双端各实现），P3 skill 分层（影响面大，需单独评估），P4 事件日志（可延后）。
