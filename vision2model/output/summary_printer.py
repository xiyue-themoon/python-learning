"""Terminal summary printer — 即时反馈
"""

def print_summary(result: dict):
    """Print a human-readable summary of pipeline results to stdout."""
    pipeline = result.get('pipeline', 'unknown')
    seg = result.get('segmentation', {})
    grid = result.get('grid', {})
    calib = result.get('calibration', {})
    measurements = result.get('measurements', [])

    print('=' * 50)
    print(f'Vision→3D Pipeline: [{pipeline}]')
    print('=' * 50)
    print(f'  Image: {result.get("image_shape", "?")}')
    print(f'  Segmentation: {seg.get("n_regions", 0)} regions ({seg.get("quality", "?")})')
    print(f'  Grid lines: H={grid.get("n_horizontal", 0)} V={grid.get("n_vertical", 0)}')
    print(f'  Grid cell: {grid.get("grid_cell_estimate_px", 0):.1f} px')

    if calib.get('method') == 'grid':
        print(f'  Calibration: {calib["px_per_mm"]:.2f} px/mm ({calib["grid_mm"]}mm grid)')
    else:
        print(f'  Calibration: none (px only)')

    print(f'  Regions: {len(measurements)}')
    for m in measurements[:5]:
        roles = ','.join(m.get('roles', []))
        print(f'    R{m.get("id", 0)}: {m.get("area_ratio", 0):.3f} [{roles}]')
    if len(measurements) > 5:
        print(f'    ... ({len(measurements) - 5} more)')

    warnings = result.get('outputs', {}).get('warning', '')
    if warnings:
        print(f'  ⚠ {warnings}')
    print('=' * 50)
