# Hermes 事件协议 v1（Event Protocol v1）

> **产出**：Pioneer → Builder | 2026-08-16
> **状态**：✅ **协议已锁定**（用户 2026-08-16 确认 P0；待 Builder 实现桥接插件）
> **基础**：最终方案 v2（/home/ubuntu/Workplace/DeepSeek-Harness-架构借鉴-最终方案.md）+ Builder 二轮审查确认 + middleware.py 源码实测

---

## 〇、协议摘要

Hermes 宿主已有**完整的 waterfall 能力**（middleware），协议层做的是：**统一命名 + 薄桥接 + 链内协调**。不重写宿主，不自己实现事件循环。

一句话：**协议 = 一张事件表 + 一个 bridge 插件 + 用户链插件约定。**

---

## 一、关键事实（为什么协议可以很薄）

源码实测（hermes_cli/middleware.py）：

| 事实 | 位置 | 含义 |
|:-----|:-----|:-----|
| `VALID_MIDDLEWARE` 4 种 | L29-34 | tool_request / tool_execution / llm_request / llm_execution |
| `apply_llm_request_middleware` | L77-117 | 每个回调返回 `{"request": {...}}` **顺序覆盖**前一个 → 链式改请求 |
| `apply_tool_request_middleware` | L120-162 | 每个回调返回 `{"args": {...}}` 顺序覆盖 → 链式改工具参数 |
| `run_llm_execution_middleware` | L173-189 | next_call 链式包裹 provider 调用 |
| `run_tool_execution_middleware` | L192-210 | next_call 链式包裹工具执行 |
| `_run_execution_chain` | L240-302 | 正宗 waterfall：next_call 单次保护 + 短路 + 异常恢复 |
| `register_middleware(kind, cb)` | plugins.py L1177 | 公开 API，外部插件可注册 |
| `register_hook(name, cb)` | plugins.py L1158 | 公开 API，观察型钩子 |

**推论**：
- **request middleware 已是 waterfall**（顺序覆盖），无需自研。
- **execution middleware 已是完整 next() 链**，无需自研。
- hooks（pre_llm_call 等）是 emit 收集——**唯一需要 bridge 聚合的**是这类多来源上下文合并。
- 所以 bridge 插件核心逻辑只有两块：① request/execution middleware 的**协议转发**（薄）；② hooks 的**链式聚合**（把 emit 收集变成有序合并）。

---

## 二、事件表（双 Agent 共用的契约）

命名空间：`agent/*`（对齐 harness 语义）。每个事件标注：宿主对接点、参数、返回契约、语义。

### 2.1 request 类（waterfall，宿主原生）

| 事件 | 宿主 | 参数 | 返回契约 | 语义 |
|:-----|:-----|:-----|:---------|:-----|
| `agent/request` | `llm_request` middleware | `request`（当前完整 kwargs）、`original_request`、`model`、`provider`、`base_url` | `{"request": {...}}` 替换；`None` 跳过 | waterfall：顺序覆盖，末位生效 |
| `agent/tool-request` | `tool_request` middleware | `tool_name`、`args`（当前）、`original_args` | `{"args": {...}}` 替换；`None` 跳过 | waterfall：顺序覆盖，末位生效 |

### 2.2 execution 类（waterfall，宿主原生）

| 事件 | 宿主 | 参数 | 返回契约 | 语义 |
|:-----|:-----|:-----|:---------|:-----|
| `agent/request-exec` | `llm_execution` middleware | `request`、`next_call`、`original_request` | 调 `next_call(payload)` 或短路 | waterfall：可包裹/重试/超时 |
| `agent/tool-exec` | `tool_execution` middleware | `tool_name`、`args`、`next_call`、`original_args` | 调 `next_call(payload)` 或短路 | waterfall：可包裹/拦截 |

### 2.3 observe 类（emit，宿主原生，bridge 聚合）

| 事件 | 宿主 | 参数 | 返回契约 | 语义 |
|:-----|:-----|:-----|:---------|:-----|
| `agent/pre-llm-call` | `pre_llm_call` hook | `messages`、`session_id`、`model`、`provider`、`turn_id` | `{"context": str}` 合并注入 user message；`None` 跳过 | **chain（bridge 聚合）**：多个来源有序合并 |
| `agent/pre-tool-call` | `pre_tool_call` hook | `tool_name`、`args`、`session_id` | **`{"action": "block", "message": str}`** 或 `None` | chain：首个 block 短路 |

> ⚠️ **契约修正（v1.1）**：block 返回必须用 `action` key，不是 `decision`。宿主 `get_pre_tool_call_directive`（plugins.py L2157-2173）只认 `action ∈ {"block","approve"}`，`{"decision": "block"}` 会被静默跳过导致 block 永不生效（2026-08-16 云端实测发现并验证）。`protocol.block_decision()` 已改为同时返回 `{"action": "block", "decision": "block", "message": ...}` 兼容两端。
| `agent/post-api-request` | `post_api_request` hook | `response` 摘要、`session_id`、`turn_id` | `None`（只读通知） | emit：广播 |
| `agent/turn-stopping` | `post_api_request` + 状态累积 | `turn_id`、`accumulated`（桥接层维护） | `None`（近似实现） | emit：turn 级干预（近似） |

### 2.4 语义对照（harness ↔ 协议）

| harness 事件 | 协议事件 | 等价程度 |
|:-------------|:---------|:---------|
| `agent/pre-step`（决定进不进 + 注入 context） | `agent/pre-llm-call`（注入）+ `agent/request`（返回空/拒绝） | 🟡 组合近似 |
| `agent/request`（改 LLM 配置） | `agent/request` | ✅ 完全等价（宿主原生） |
| `agent/request-error`（重试决策） | `agent/request-exec`（wrap 内重试） | 🟡 组合近似 |
| `agent/turn-stopping`（turn 结束前干预） | `agent/turn-stopping`（状态累积近似） | 🟡 近似 |

---

## 三、bridge 插件结构（Builder 按此实现）

```
~/.hermes/plugins/hermes-event-bridge/
├── plugin.yaml          # manifest：name/description
├── __init__.py          # register(ctx)：注册 4 个 middleware + 3 个 hook
├── protocol.py          # 事件名常量 + 参数契约校验（~60 行）
├── bridge.py            # 宿主对接层：middleware/hook → 用户链插件分发（~120 行）
├── chain.py             # hooks 链式聚合器（emit 收集 → 有序合并，~50 行）
└── chains/              # 用户链插件（每个文件一个）
    ├── context_injector.py   # agent/pre-llm-call：多来源上下文合并
    ├── tool_guard.py         # agent/pre-tool-call：block 短路
    └── request_tuner.py      # agent/request：改 maxTokens/provider
```

### 3.1 用户链插件接口（chains/*.py 的契约）

```python
# 每个链插件实现这个 Protocol（chains/__init__.py 定义）
class ChainPlugin(Protocol):
    name: str                      # 插件名（日志/追踪用）
    events: list[str]              # 订阅的事件（agent/request 等）

    async def handle(self, ctx: dict, next_call: Callable) -> Any:
        """处理一个事件。ctx 是事件 payload。

        - request 类：返回 {"request": {...}} 或 None
        - execution 类：调用 next_call(payload) 继续，或返回结果短路
        - observe 类：
            - pre-llm-call: 返回 {"context": str} 或 None
            - pre-tool-call: 返回 {"action": "block", "message": str} 或 None  ⚠️ action 不是 decision
        """
```

### 3.2 bridge.py 核心逻辑（示意，非最终实现）

```python
# 宿主 middleware 回调 → 分发给订阅该事件的用户链插件（按注册顺序）
def make_llm_request_bridge(protocol, chains):
    def handler(request, original_request, **ctx):
        current = request
        for chain in chains.subscribed("agent/request"):
            result = chain.handle({"request": current, "original_request": original_request, **ctx})
            if isinstance(result, dict) and "request" in result:
                current = result["request"]          # 顺序覆盖（宿主语义）
        return {"request": current}
    return handler

# 宿主 execution 回调 → 用户链插件 next_call 链（宿主 _run_execution_chain 已保证单次调用）
def make_llm_exec_bridge(protocol, chains):
    def handler(request, next_call, **ctx):
        def chained(payload=None):
            # 逐个执行用户链插件，最后调宿主 next_call
            ...
        return chained(request)
    return handler

# 宿主 hook 回调 → chain.py 聚合（emit 收集 → 有序合并）
def make_pre_llm_call_bridge(protocol, chains):
    def handler(**kwargs):
        merged = chain.merge("agent/pre-llm-call", kwargs, default={"context": ""})
        return merged   # {"context": "src1\n\nsrc2"} 或 None
    return handler
```

### 3.3 注册清单（__init__.py 必须做的）

```python
def register(ctx):
    ctx.register_middleware("llm_request",     make_llm_request_bridge(...))
    ctx.register_middleware("tool_request",    make_tool_request_bridge(...))
    ctx.register_middleware("llm_execution",   make_llm_exec_bridge(...))
    ctx.register_middleware("tool_execution",  make_tool_exec_bridge(...))
    ctx.register_hook("pre_llm_call",   make_pre_llm_call_bridge(...))
    ctx.register_hook("pre_tool_call",  make_pre_tool_call_bridge(...))
    ctx.register_hook("post_api_request", make_post_api_request_bridge(...))
```

**关键约束**（协议级，两端一致）：
1. **用户链插件永不抛异常**——bridge 包住所有 `chain.handle()` 调用，异常只 log 不传播（对齐宿主 invoke_hook L1920 容错）。
2. **request 类只改 `request` key**，不改其他字段（`original_request` 只读）。
3. **execution 类必须调 `next_call` 恰好一次**（宿主已强制单次保护 L268-273）。
4. **observe 类永不阻塞**——`post_api_request` 回调不做 I/O 等待。
5. **prompt cache 前缀保护**——`agent/pre-llm-call` 注入的 context 走 user message，**绝不碰 system prompt**（对齐 plugins.py L1906 约束）。

---

## 四、验证矩阵（双 Agent 共用）

| # | 验证项 | 方法 | 通过标准 |
|:-:|:-------|:-----|:---------|
| 1 | 空链零回归 | 安装 bridge（无 chains/ 插件）跑真实对话 | 行为与未装插件时一致；无 traceback |
| 2 | request 链生效 | 注册 request_tuner 改 max_tokens=32 | API 调用日志出现 max_tokens=32 |
| 3 | 多链顺序覆盖 | 注册 2 个 request 链（A 改 max_tokens，B 改 temperature） | 末位 B 生效且 A 的改动保留（若 A 后无 B 覆盖该 key） |
| 4 | tool block 短路 | 注册 tool_guard block `web_search` | 工具被拦截，模型收到 block 消息 |
| 5 | context 多源合并 | 注册 2 个 context_injector | user message 尾部含两个来源拼接文本 |
| 6 | execution wrap | 注册 request-exec 打印耗时 | 日志出现耗时记录，LLM 调用正常返回 |
| 7 | 升级兼容 | 改宿主 middleware 签名（模拟升级） | bridge 给出明确失败日志而非静默错 |

---

## 五、双 Agent 部署

| 项 | Builder（Win11） | Pioneer（云端） |
|:---|:-----------------|:----------------|
| 版本 | Hermes v0.16.0（本地） | Hermes v0.19.0 |
| 宿主钩子 | pre_llm_call/pre_tool_call/post_api_request 需确认存在 | 已验证存在（conversation_loop L882/L1356/L4485） |
| middleware | llm_request/tool_request/llm_execution/tool_execution 需确认 | 已验证存在（middleware.py L29-34） |
| 实现 | 按协议实现 bridge 插件 | 同协议实现（或复用 Builder 版本） |
| 验证 | 跑验证矩阵 1-7 | 跑验证矩阵 1-7 |

> ⚠️ Builder 侧 v0.16.0 需先确认：`hermes_cli/middleware.py` 是否存在、`VALID_MIDDLEWARE` 是否 4 种。若 v0.16.0 没有 middleware 链（只有 hooks），则 v0.16 先只做 observe 类（hooks 聚合），request 类等升级到 0.19 后启用。**协议本身两端一致，实现按版本裁剪。**

---

## 六、变更记录

| 版本 | 日期 | 变更 |
|:-----|:-----|:-----|
| v1 | 2026-08-16 | 初版：事件表 + bridge 结构 + 验证矩阵 |
| v1.1 | 2026-08-16 | **契约修正**：pre-tool-call block 返回改用 `action` key（宿主解析 plugins.py L2157 只认 action）；云端实测发现 `{"decision": "block"}` 被宿主静默跳过 |
