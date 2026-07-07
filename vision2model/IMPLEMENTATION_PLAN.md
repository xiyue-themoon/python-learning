# Vision→3D · 工程落地方案

> 目标: 按阶段拆解为 Builder 可执行的原子任务
> 周期: Phase 1-3 逐步推进，每阶段完成后回归测试

---

## 总体阶段

```
Phase 0 — 骨架搭建（~2 天）
  模块目录 + @register 注册表 + 所有 @dataclass + 空函数体

Phase 1 — 核心管线跑通（~3 天）
  segmenter + semantifier + allocator + 3 条基础管线
  从 S_grid 开始，输出 JSON + SVG

Phase 2 — 多算法融合（~2 天）
  fusion engine + ensemble 管线
  
Phase 3 — 校准与映射（~2 天）
  级联校准 + 3D 映射 + 输出完善

Phase 4 — 质量加固（~2 天）
  测试 + 边界情况 + 性能优化
```

---

## Phase 0：骨架搭建

### 任务 0.1 — 目录结构 & 空文件

```
创立 vision2model/ 目录树（见 ARCHITECTURE.md §6）
每个 .py 文件写入 import 头 + 空函数体 + pass
```

验收标准: `python3 -c "from vision2model import *"` 不报 import 错

### 任务 0.2 — registry.py + tag_schema.py

```python
registry.py:
  MODULE_REGISTRY = {}
  register(name, **tags) → 装饰器
  find_modules(**filters) → list[(name, entry)]

tag_schema.py:
  TAG_SCHEMA 常量定义（function/size/accuracy/...）
  validate_tags(tags) → 检查必填字段
```

验收标准: 单测 `test_registry.py` 通过

### 任务 0.3 — types.py（所有 @dataclass）

定义以下结构体（详见 ARCHITECTURE.md §2）：

```
ImageProfile
PipelineSelection
GenericRegion
Measurement
MeasurementSet
FusionResult
AlgorithmTask
CalibrationInput
```

验收标准: 所有 dataclass 可 import + 实例化

### 任务 0.4 — 所有模块空文件 + 注册装饰

```
为 preprocessing/*.py、line_detection/*.py、
cluster/*.py、calibrate/*.py、fusion/*.py、
region/*.py、output/*.py 的每个函数体打上 @register 装饰器
```

验收标准: `find_modules()` 能遍历所有已注册模块

---

## Phase 1：核心管线跑通

### 任务 1.1 — Dispatcher（图像分诊）

**文件**: `dispatcher.py`

```python
def analyze_image(image_path) -> ImageProfile:
    """提取图像特征画像"""
    - 尺寸分级 S/M/L
    - RMS 对比度判定
    - 拉普拉斯方差估计噪声
    - 背景类型猜测
    - 参照物检测

def select_pipeline(profile: ImageProfile) -> PipelineSelection:
    """按 profile 查管线表，fallback 兜底"""
```

验收标准: 对启仔参考图输出正确的 profile (`S, medium, medium, grid`)

### 任务 1.2 — Segmenter（Felzenszwalb 分割 + 合并 + 质量评估）

**文件**: `region/segmenter.py`

```python
def segment_image(image) -> tuple[np.ndarray, str]:
    """
    Felzenszwalb 自适应分割
    + HSV 巴氏距离合并相邻相似 region
    + 质量评估 (region 数 / body_ratio / 小 region 数)
    + 最多 3 次重试
    返回: (segments_label_map, quality)
    """
```

验收标准: 单测 `test_segmenter.py` — 同一张图两次运行返回相同结果

### 任务 1.3 — Semantifier（角色分配）

**文件**: `region/semantifier.py`

```python
def assign_roles(segments, image) -> list[GenericRegion]:
    """给每个 region 分配通用数学角色"""

def find_symmetric_pairs(candidates, dominant) -> list[tuple]:
    """宽松对称配对"""
```

验收标准: 对启仔参考图，能分出 dominant + background + 若干 inclusion+accent

### 任务 1.4 — Allocator（算法分配）

**文件**: `region/allocator.py`

```python
def allocate_algorithms(regions: list[GenericRegion]) -> list[AlgorithmTask]:
    """按 role→algorithm 映射分配检测任务"""
```

验收标准: dominant → contour_extract + shape_analysis

### 任务 1.5 — 基础算法实现（最低基线）

实现以下基础算法，每个独立测试：

| 算法 | 文件 | 最低基线 |
|:-----|:-----|:---------|
| `preproc_gaussian` | preprocessing/gaussian.py | cv2.GaussianBlur |
| `preproc_clahe` | preprocessing/clahe.py | cv2.createCLAHE |
| `preproc_otsu` | preprocessing/otsu.py | cv2.threshold(OTSU) |
| `line_houghp` | line_detection/houghp.py | cv2.HoughLinesP |
| `blob_detect` | line_detection/blob.py（新增） | skimage.feature.blob_log |
| `contour_extract` | line_detection/contour.py（新增） | cv2.findContours |
| `shape_analysis` | line_detection/shape.py（新增） | minAreaRect + fitEllipse |
| `cluster_diff` | cluster/diff.py | np.diff + 阈值分组 |

验收标准: 每个算法独立可测试，输入已知数据输出预期结果

### 任务 1.6 — 管线 S_grid

**文件**: `pipelines/S_grid.py`

```python
def run_S_grid(image, calib: CalibrationInput) -> dict:
    """S_grid 完整执行"""
    steps:
      1. dispatcher → profile（验证 profile == S_grid 匹配）
      2. segmenter → regions
      3. semantifier → labeled regions
      4. allocator → tasks
      5. 按 tasks 执行对应算法
      6. calibrate
      7. output JSON + SVG
```

验收标准: 对启仔参考图输出完整 JSON（所有字段非空）

### 任务 1.7 — SVG + JSON 输出

**文件**: `output/json_exporter.py`, `output/svg_renderer.py`, `output/summary_printer.py`

验收标准: SVG 在浏览器中打开可见原图 + region 边界 + 特征标注

---

## Phase 2：多算法融合

### 任务 2.1 — Fusion Engine

**文件**: `fusion/engine.py`

```python
def fuse_measurements(sets: list[MeasurementSet]) -> FusionResult:
    """
    低置信过滤 → IQR 去异常 → 加权平均 → 一致性检验
    """
```

验收标准: 对自洽的虚拟数据输出一致的高置信结果

### 任务 2.2 — 追加检测算法

| 算法 | 文件 | 说明 |
|:-----|:-----|:-----|
| `line_morphological` | line_detection/morphological.py | 骨架提取→交叉点检测 |
| `line_fld` | line_detection/fld.py | OpenCV FLD |
| `subpixel_fit` | line_detection/subpixel.py（新增） | 2D 高斯拟合 |
| `curvature_analysis` | line_detection/curvature.py（新增） | contour 曲率突变 |

### 任务 2.3 — 管线 S_grid_ensemble

**文件**: `pipelines/S_grid_ensemble.py`

```python
def run_S_grid_ensemble(image, calib) -> dict:
    """S_grid_ensemble 完整执行，开启融合"""
```

验收标准: 对同一张图，S_grid 和 S_grid_ensemble 的输出数值应在误差范围内一致，且 ensemble 的置信度更高

### 任务 2.4 — Pipeline Selector 整合

**文件**: `dispatcher.py` 内 `select_pipeline()` 补全

```
profile: S, grid, low_contrast → S_grid_ensemble
profile: S, grid, high_contrast → S_grid
profile: S, solid → S_solid
profile: M, grid → M_grid
profile: M, grid, low_contrast → M_grid_ensemble
else → fallback
```

---

## Phase 3：校准与映射

### 任务 3.1 — 方格纸校准

**文件**: `calibrate/grid.py`

```python
def calibrate_grid(lines, known_grid_mm=5.0) -> MeasurementSet:
    """
    从检测到的格线 → 格距 px → 比例尺 mm/px
    支持用户预设格距（默认 5mm）
    """
```

### 任务 3.2 — 多参照交叉校验

**文件**: `calibrate/crosscheck.py`

```python
def crosscheck_scales(scales: dict[str, Measurement]) -> dict:
    """校验逻辑，输出 ok/warning/failed"""
```

### 任务 3.3 — 2D→3D 映射

**文件**: `image2model.py` 内新增

```python
def map_to_3d(features, dominant_region, scale, mapping_mode='auto'):
    """
    auto 检测模式:
      宽高比 ≈ 1 + 轮廓近似椭圆 → revolve
      宽高比 ≈ 1 + 轮廓近似矩形 → box
      宽高比 >> 1 → cylinder
    """
```

### 任务 3.4 — CalibrationInput 接受

在 `image2model.py` 主入口支持传入 `CalibrationInput`：

```bash
python3 image2model.py input.png --body-height 84
python3 image2model.py input.png --grid-mm 5
python3 image2model.py input.png  # 无参照 → px 输出
```

---

## Phase 4：质量加固

### 任务 4.1 — 测试用例

```
test_segmenter.py  — 同一图两次结果一致
test_fusion.py     — 自洽虚拟数据
test_pipelines.py  — 启仔参考图跑通全管线
test_calibration.py — 尺寸偏差 3%/10%/20% 的校验结果正确
```

### 任务 4.2 — 边界情况

```
- 空图像（全白/全黑）
- 极低分辨率 (100×100)
- 无特征图像（纯色块）
- 多物体图像
```

### 任务 4.3 — 性能基准

```
S 图管线执行时间应 < 5s（不含 I/O）
M 图 < 15s
L 图 < 60s
```

---

## 验收驱动的开发

每阶段完成后运行全量测试：

```bash
cd vision2model
python3 -m pytest tests/ -v
```

所有测试通过后才标记阶段完成，进入下一阶段。
