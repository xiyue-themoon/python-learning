"""Vision→3D 测量管线 — 算法分配 (Node 4)

按 role→algorithm 映射分配检测任务。
支持多 role 合并去重，同 function 保留高 accuracy。
"""

from ..types import GenericRegion, AlgorithmTask


# ═══════════════════════════════════════════════════════════
# Role → Algorithm 映射
# ═══════════════════════════════════════════════════════════

ROLE_ALGORITHM_MAP: dict[str, list[str]] = {
    'dominant':   ['contour_extract', 'shape_analysis'],
    'background': ['line_detect', 'texture_analysis'],
    'inclusion':  ['blob_detect', 'subpixel_fit'],
    'accent':     ['blob_detect', 'subpixel_fit'],
    'protrusion': ['curvature_analysis'],
    'uniform':    ['color_sampling'],
    'patterned':  ['texture_analysis'],
    'fragment':   ['position_only'],
    'adjunct':    ['contour_extract'],
}

# Roles that trigger ensemble (multi-algorithm voting) for key measurements
ENSEMBLE_ROLES = {'dominant'}


def allocate_algorithms(regions: list[GenericRegion]) -> list[AlgorithmTask]:
    """按 role→algorithm 映射分配检测任务

    多 role 合并去重，同 function 保留高 accuracy。
    dominant region 默认启用 ensemble (多算法投票)。

    Args:
        regions: 带角色的 GenericRegion 列表

    Returns:
        list[AlgorithmTask] 算法执行任务列表
    """
    tasks: list[AlgorithmTask] = []
    priority = 0

    for region in regions:
        if not region.roles:
            continue

        # Collect all algorithms for this region's roles
        alg_set: set[str] = set()
        for role in region.roles:
            algs = ROLE_ALGORITHM_MAP.get(role, [])
            alg_set.update(algs)

        if not alg_set:
            continue

        # Check if ensemble should be used
        use_ensemble = bool(region.roles & ENSEMBLE_ROLES)

        task = AlgorithmTask(
            target_region_id=region.id,
            algorithms=sorted(alg_set),
            ensemble=use_ensemble,
            priority=priority,
        )
        tasks.append(task)
        priority += 1

    return tasks
