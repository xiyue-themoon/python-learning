# Vision→3D 测量管线 · 架构定稿

> 版本: v2.0 | 日期: 2026-07-07
> 设计目标: 泛化图像→3D 测量管线，支持不同图像尺寸/背景/物体的无标定适配

---

## 0. 全线架构图

```
输入图像
   │
   ├─[0] Dispatcher ── 图像分诊
   │   ├─ 尺寸分级: S(≤600px) / M(≤1920px) / L(>1920px)
   │   ├─ 对比度: high / medium / low (RMS contrast 阈值 30/60)
   │   ├─ 噪声: high / medium / low (Laplacian var 阈值 50/200)
   │   ├─ 背景: grid / solid / cluttered / unknown
   │   └─ 参照物: has_reference(bool)
   │         ↓ ImageProfile
   │
   ├─[1] Pipeline Selector
   │   ├─ size × bg_type 索引 → 预编排管线
   │   ├─ should_use_ensemble() 自动决定
   │   └─ fallback 保守管线兜底
   │         ↓ PipelineSelection
   │
   ├─[2] Segmentation
   │   ├─ Felzenszwalb (skimage) → 自适应区域分割
   │   ├─ HSV 直方图巴氏距离 → 相邻相似 region 合并
   │   ├─ 小特征保护: 面积比 > 10× 不合并
   │   ├─ 质量评估: region 数 / body_ratio / 小 region 数
   │   └─ 重试: 最多 3 组参数，全失败则降级
   │         ↓ LabelMap + Region List
   │
   ├─[3] Region Semantification
   │   ├─ 通用数学角色 (不假设语义)
   │   │   dominant / background / inclusion / adjunct
   │   │   protrusion / fragment / uniform / patterned
   │   │   accent / gradient
   │   ├─ 综合评分法判定 dominant
   │   ├─ 宽松对称检测 (垂直对齐容差 2×直径)
   │   └─ 被包围的零散 region → 合并到包围者
   │         ↓ GenericRegion[].roles
   │
   ├─[4] Algorithm Allocation
   │   ├─ role→algorithm 映射:
   │   │   dominant       → contour_extract + shape_analysis
   │   │   background     → line_detect + texture_analysis
   │   │   inclusion+accent → blob_detect + subpixel_fit
   │   │   protrusion     → curvature_analysis
   │   │   uniform        → color_sampling
   │   │   fragment       → position_only
   │   ├─ @register 装饰器 + tag 系统 → 算法发现
   │   ├─ 多 role 合并去重，同 function 保留高 accuracy
   │   └─ ensemble 仅用于关键测量 (dominant 尺寸/位置)
   │         ↓ AlgorithmTask[]
   │
   ├─[5] Measurement Execution
   │   ├─ 统一接口: fn(region_mask, source_image, **params) → MeasurementSet
   │   ├─ 显式传参，无隐藏状态
   │   ├─ 空结果返回空列表，不终止管线
   │   └─ 最低基线实现优先，跑通后逐个升级
   │         ↓ MeasurementSet[]
   │
   ├─[6] Fusion Engine
   │   ├─ 低置信度过滤 (< 0.3 剔除)
   │   ├─ IQR 去异常值
   │   ├─ 加权平均: value = Σ(w · v) / Σ(w), w = confidence
   │   ├─ 误差传播: σ² = Σ(w² · σ²ᵢ) / (Σw)²
   │   ├─ 一致性: CV < 5% high / < 15% medium / else low
   │   └─ 低一致标记不终止，突出显示
   │         ↓ FusionResult[]
   │
   ├─[7] Calibration & Mapping
   │   ├─ 级联校准:
   │   │   0: 无参照 → px 级输出
   │   │   1: 方格纸 → scale_grid (默认 5mm, 用户可改)
   │   │   2: 已知尺寸 → scale_body/scale_object
   │   │   3: 多参照交叉校验
   │   ├─ diff < 5% → ok, 加权平均
   │   │  diff 5-15% → warning, 取中位数
   │   │  diff > 15% → failed, 输出诊断
   │   ├─ 3D 映射: 自动检测旋转体/箱体/柱体
   │   └─ 特征 Z 坐标 = body_height × (1 − relative_y)
   │         ↓ CalibratedFeatures (mm 或 px)
   │
   └─[8] Output
       ├─ 结构化 JSON → Builder/FreeCAD
       │   regions / features / calibration / warnings / recommendations
       ├─ SVG 验证图 → 人工复核 (同目录 _validation.svg)
       ├─ 终端摘要 → 即时反馈
       └─ 历史存档 → ~/.hermes/measurements/<timestamp>/
```

---

## 1. Tag 系统设计

### 1.1 注册装饰器

```python
# vision_modules/registry.py

MODULE_REGISTRY = {}

def register(name, **tags):
    """注册检测算法模块"""
    def decorator(fn):
        MODULE_REGISTRY[name] = {'fn': fn, 'tags': tags}
        return fn
    return decorator

def find_modules(**filters):
    """按 tag 查询模块"""
    results = []
    for name, entry in MODULE_REGISTRY.items():
        tags = entry['tags']
        match = all(
            tags.get(k) == v or
            (k == 'size' and tags.get(k, '').count(v))
            for k, v in filters.items()
        )
        if match:
            results.append((name, entry))
    return results
```

### 1.2 Tag Schema

| 维度 | 类型 | 值域 | 描述 |
|:-----|:-----|:-----|:-----|
| `function` | str | preprocess / line_detect / blob_detect / contour / curvature / calibrate / fusion | 功能域 |
| `size` | str | S / M / L / S\|M / M\|L / all | 适用图像尺寸 |
| `accuracy` | int | 1-5 | 精度评级 |
| `robustness` | int | 1-5 | 抗噪评级 |
| `speed` | str | fast / medium / slow | 执行速度 |
| `gpu` | str | none / optional / required | GPU 需求 |
| `deps` | list | opencv / scipy / sklearn / skimage | 依赖项 |
| `beta` | bool | True/False | 实验性模块标记 |

### 1.3 查询示例

```python
# 找 S 级可用的线检测算法
find_modules(function='line_detect', size='S')
# → [('line_morphological', {...}), ('line_houghp', {...})]

# 找精度 ≥ 4 的特征检测
find_modules(function='blob_detect', accuracy=4)
```

---

## 2. 核心数据结构

### 2.1 ImageProfile（分流器输出）

```python
@dataclass
class ImageProfile:
    size: str            # 'S' | 'M' | 'L'
    contrast: str        # 'high' | 'medium' | 'low'
    noise: str           # 'high' | 'medium' | 'low'
    bg_type: str         # 'grid' | 'solid' | 'cluttered' | 'unknown'
    has_reference: bool  # True = 图中检测到已知尺寸参照物
```

### 2.2 PipelineSelection（管线选择输出）

```python
@dataclass
class PipelineSelection:
    name: str
    steps: list[str]           # 模块名序列
    use_ensemble: bool         # 是否启用投票融合
    params: dict               # 管线级参数覆盖
```

### 2.3 GenericRegion（通用数学区域）

```python
@dataclass
class GenericRegion:
    id: int
    mask: np.ndarray           # 布尔矩阵
    bbox: tuple                # (x, y, w, h)
    centroid: tuple            # (cx, cy)
    area: int                  # 像素数
    area_ratio: float          # 占图像总面积比
    roles: set[str]            # {'dominant', 'uniform', ...}
    properties: dict           # 统计量
    contour: np.ndarray        # N×2 边界点集
    convexity: float           # 凸包面积 / 实际面积
    aspect_ratio: float        # 宽高比
    color_mean: np.ndarray     # HSV 均值
    color_std: np.ndarray      # HSV 标准差
```

### 2.4 Measurement & MeasurementSet（测量结果）

```python
@dataclass
class Measurement:
    value: float | tuple       # 测量值 (单值或坐标)
    error: float               # 标准误差
    unit: str                  # 'px' | 'mm'
    confidence: float          # 0.0 - 1.0

@dataclass
class MeasurementSet:
    source: str                # 算法名
    measurements: list[Measurement]
    raw_data: dict             # 算法中间结果 (debug 用)
```

### 2.5 FusionResult（融合结果）

```python
@dataclass
class FusionResult:
    value: float | tuple
    error: float
    unit: str
    confidence: float
    n_sources: int
    consistency: str           # 'high' | 'medium' | 'low'
    details: list[dict]
    annotated: bool = False    # True = 已人工复核
```

### 2.6 AlgorithmTask（算法分配结果）

```python
@dataclass
class AlgorithmTask:
    target_region_id: int
    algorithms: list[str]      # ['blob_detect', 'subpixel_fit']
    ensemble: bool             # 是否多算法投票
    priority: int              # 执行优先级
```

### 2.7 CalibrationInput（用户输入的标定信息）

```python
@dataclass
class CalibrationInput:
    method: str                # 'grid' | 'body_height' | 'reference_object' | 'none'
    value_mm: float            # 真实尺寸
    description: str           # 描述 (用于报告)
    object_bbox: tuple | None = None  # 参照物在图像中的框
```

---

## 3. 管线表

当前已定义管线：

| 管线名 | 适用 profile | ensemble | 包含步骤 |
|:-------|:-------------|:--------:|:---------|
| `S_grid` | size=S, bg=grid | 否 | gaussian → clahe → otsu → houghp → diff → calibrate |
| `S_grid_ensemble` | size=S, bg=grid, contrast/噪点异常 | **是** | gaussian → clahe → otsu → [morphological+houghp+fld] → fusion → calibrate |
| `S_solid` | size=S, bg=solid | 否 | gaussian → otsu → contour → shape |
| `S_cluttered` | size=S, bg=cluttered | **是** | gaussian → clahe → felzenszwalb → ... |
| `M_grid` | size=M, bg=grid | 否 | gaussian → clahe → lsd → dbscan → calibrate |
| `M_grid_ensemble` | size=M, bg=grid, contrast/噪点异常 | **是** | gaussian → clahe → [lsd+fld] → fusion → calibrate |
| `fallback` | 其他 | 否 | gaussian → otsu → houghp → diff → 报告基础结果 |

---

## 4. Region 语义角色体系

### 4.1 通用数学角色（不假设物体类型）

| 角色 | 判定条件 | 对应算法 |
|:-----|:---------|:---------|
| `dominant` | 面积占比 > 15% + 质心靠近图像中心 | contour_extract, shape_analysis |
| `background` | 面积 > 10% + 位于图像外围 | line_detect, texture_analysis |
| `inclusion` | 被另一 region 完全包围 | 继承包围者的算法策略 |
| `accent` | 小面积 (<5%) + 高对比度 | blob_detect, subpixel_fit |
| `protrusion` | 相邻 dominant 且在轮廓外侧 | curvature_analysis |
| `uniform` | 颜色标准差低 | color_sampling |
| `patterned` | 边缘密度高 | texture_analysis |
| `fragment` | 零散、不与任何主区域相邻 | position_only |
| `adjunct` | 邻接 dominant 但不被包围 | contour_extract（合并到 dominant） |

### 4.2 对称性检测

```python
def find_symmetric_pairs(candidates, dominant_centroid, tolerance_y=0.05, tolerance_x=0.08):
    """
    宽松对称配对 — 用于成对特征识别
    
    tolerance_y: 允许的垂直偏差 (占 dominant 高度比)
    tolerance_x: 允许的水平偏差 (占 dominant 宽度比)
    """
    pairs = []
    used = set()
    for i, a in enumerate(candidates):
        if i in used:
            continue
        for j, b in enumerate(candidates):
            if j <= i or j in used:
                continue
            # 垂直对齐
            dy = abs(a.centroid[1] - b.centroid[1])
            if dy > dominant_centroid[3] * tolerance_y:  # bbox.h
                continue
            # 水平对称
            dx_a = abs(a.centroid[0] - dominant_centroid[0])
            dx_b = abs(b.centroid[0] - dominant_centroid[0])
            if abs(dx_a - dx_b) > dominant_centroid[2] * tolerance_x:  # bbox.w
                continue
            pairs.append((a, b))
            used.add(i); used.add(j)
    return pairs
```

---

## 5. 校准级联策略

| Level | 参照来源 | 条件 | 输出 |
|:-----:|:---------|:-----|:-----|
| 0 | 无参照 | fallback | px 级测量，无 3D 映射 |
| 1 | 方格纸 | background 检出规律网格 | scale_grid |
| 2 | 已知尺寸 | 用户输入 body_height_mm | scale_body |
| 3 | 参照物 | 用户标注 + 输入尺寸 | scale_object |
| 4 | 多参照校验 | ≥2 个参照可用 | 加权平均 ± 一致性报告 |

### 交叉校验规则

```python
def crosscheck(scales: dict[str, float]) -> dict:
    """
    scales = {'grid': 0.064, 'body': 0.217}
    返回校验结果
    """
    values = list(scales.values())
    if len(values) < 2:
        return {'status': 'single', 'scale': values[0], 'error': 0}
    
    median = np.median(values)
    errors = {}
    for name, v in scales.items():
        diff = abs(v - median) / median * 100
        errors[name] = diff
    
    max_diff = max(errors.values())
    if max_diff < 5:
        return {'status': 'ok', 'scale': median, 'error': np.std(values)}
    elif max_diff < 15:
        return {'status': 'warning', 'scale': median, 'error': np.std(values) * 1.5,
                'detail': errors}
    else:
        return {'status': 'failed', 'scale': None, 'error': float('inf'),
                'detail': errors, 'recommendation': '确认参照真实值/拍摄角度'}
```

---

## 6. 目录结构

```
python-learning/
├── vision2model/
│   ├── ARCHITECTURE.md          ← 本文档
│   ├── IMPLEMENTATION_PLAN.md   ← 工程落地方案
│   │
│   ├── vision_modules/
│   │   ├── __init__.py
│   │   ├── registry.py          ← MODULE_REGISTRY + register()
│   │   ├── tag_schema.py        ← Tag 定义 + find_modules()
│   │   ├── types.py             ← 所有 @dataclass 定义
│   │   │
│   │   ├── preprocessing/
│   │   │   ├── __init__.py
│   │   │   ├── gaussian.py
│   │   │   ├── clahe.py
│   │   │   ├── otsu.py
│   │   │   ├── morphological.py
│   │   │   ├── superres.py
│   │   │   └── perspective.py
│   │   │
│   │   ├── line_detection/
│   │   │   ├── __init__.py
│   │   │   ├── morphological.py
│   │   │   ├── houghp.py
│   │   │   ├── fld.py
│   │   │   └── lsd.py
│   │   │
│   │   ├── cluster/
│   │   │   ├── __init__.py
│   │   │   ├── diff.py
│   │   │   └── dbscan.py
│   │   │
│   │   ├── calibrate/
│   │   │   ├── __init__.py
│   │   │   ├── grid.py
│   │   │   └── crosscheck.py
│   │   │
│   │   ├── fusion/
│   │   │   ├── __init__.py
│   │   │   └── engine.py
│   │   │
│   │   └── region/
│   │       ├── __init__.py
│   │       ├── segmenter.py        ← Felzenszwalb 分割 + 合并 + 质量评估
│   │       ├── semantifier.py      ← 角色分配 + 对称检测
│   │       └── allocator.py        ← 算法分配映射
│   │
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── S_grid.py
│   │   ├── S_grid_ensemble.py
│   │   ├── S_solid.py
│   │   ├── M_grid.py
│   │   ├── M_grid_ensemble.py
│   │   └── fallback.py
│   │
│   ├── dispatcher.py              ← 图像分诊 + 管线选择
│   ├── image2model.py             ← 主入口
│   │
│   ├── output/
│   │   ├── __init__.py
│   │   ├── json_exporter.py
│   │   ├── svg_renderer.py
│   │   └── summary_printer.py
│   │
│   ├── tests/
│   │   ├── test_segmenter.py
│   │   ├── test_semantifier.py
│   │   ├── test_fusion.py
│   │   └── test_pipelines.py
│   │
│   └── refs/
│       ├── sample_image.png        ← 启仔参考图 (sample)
│       └── test_grid.png           ← 测试网格图
```

---

## 7. 设计哲学

1. **数学优先** — 测量管线全在可量化的数学模型上运行，不依赖 LLM 生成的文字作为中间输入。
2. **泛化优先** — Region 角色用通用数学描述（dominant/inclusion/accent），不假设物体类型。
3. **降级不崩溃** — 无参照输出 px、分割差降级、低一致标记不终止。管线永远产出结果，只是置信度不同。
4. **模块化** — 每个算法独立注册、独立测试、独立升级。管线只是模块的编排组合。
5. **置信度传播** — 每步产出的值自带误差和置信度，最终用户看到的不只是数值，而是数值的可信程度。
