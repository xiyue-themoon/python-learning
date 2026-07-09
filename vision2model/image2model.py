"""Vision→3D 测量管线 — 主入口

用法:
    python3 vision2model/image2model.py <image_path> [options]
"""

import sys
import argparse
import os
import cv2

from .dispatcher import dispatcher, select_pipeline
from .pipelines.S_grid import run_S_grid
from .pipelines.S_grid_ensemble import run_S_grid_ensemble
from .output.json_exporter import export_json
from .output.svg_renderer import render_svg
from .output.summary_printer import print_summary
from .vision_modules.types import CalibrationInput
from .vision_modules.registry import MODULE_REGISTRY, list_all_modules


PIPELINE_REGISTRY = {
    'S_grid': run_S_grid,
    'S_grid_ensemble': run_S_grid_ensemble,
    'S_solid': run_S_grid,
    'fallback': run_S_grid,
}


def main():
    parser = argparse.ArgumentParser(description='Vision→3D 测量管线')
    parser.add_argument('image_path', help='输入图像路径')
    parser.add_argument('--body-height', type=float, help='已知身体高度 (mm)')
    parser.add_argument('--grid-mm', type=float, default=5.0, help='方格纸格距 (mm, 默认 5.0)')
    parser.add_argument('--output-dir', help='输出目录 (默认与输入同目录)')
    parser.add_argument('--list-modules', action='store_true', help='列出所有已注册模块')
    args = parser.parse_args()

    if args.list_modules:
        print(f'Registered modules ({len(MODULE_REGISTRY)}):')
        list_all_modules()
        return

    if not os.path.exists(args.image_path):
        print(f'Image not found: {args.image_path}')
        sys.exit(1)

    # Read image
    image = cv2.imread(args.image_path)
    if image is None:
        print(f'Failed to read image: {args.image_path}')
        sys.exit(1)

    # Step 1: Dispatch (profile + pipeline selection)
    profile, pipeline = dispatcher(args.image_path)
    print(f'Profile: {profile}')
    print(f'Pipeline: {pipeline.name} (ensemble={pipeline.use_ensemble})')

    # Step 2: Run the selected pipeline
    runner = PIPELINE_REGISTRY.get(pipeline.name)
    if runner is None:
        print(f'Pipeline {pipeline.name} not yet implemented')
        sys.exit(1)

    # Build calibration input
    calib = None
    if args.grid_mm > 0 and profile.bg_type == 'grid':
        calib = CalibrationInput(method='grid', value_mm=args.grid_mm, description='方格纸')
    elif args.body_height:
        calib = CalibrationInput(method='body_height', value_mm=args.body_height)

    result = runner(image, calib=calib)

    # Step 3: Output
    output_dir = args.output_dir or os.path.dirname(args.image_path) or '.'
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(args.image_path))[0]

    json_path = os.path.join(output_dir, f'{base_name}_result.json')
    export_json(result, json_path)
    print(f'JSON: {json_path}')

    svg_path = os.path.join(output_dir, f'{base_name}_validation.svg')
    render_svg(image, result, svg_path, args.image_path)
    print(f'SVG: {svg_path}')

    print_summary(result)
    print('Done.')


if __name__ == '__main__':
    main()
