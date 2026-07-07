"""Vision→3D 测量管线 — 主入口

用法:
    python3 vision2model/image2model.py <image_path> [options]

选项:
    --body-height N    已知身体高度 (mm)
    --grid-mm N        方格纸格距 (mm, 默认 5.0)
    --output-dir DIR   输出目录 (默认与输入同目录)
"""

import sys
import argparse
import os


def main():
    parser = argparse.ArgumentParser(description='图像→3D 测量管线')
    parser.add_argument('image_path', help='输入图像路径')
    parser.add_argument('--body-height', type=float, help='已知身体高度 (mm)')
    parser.add_argument('--grid-mm', type=float, default=5.0, help='方格纸格距 (mm)')
    parser.add_argument('--output-dir', help='输出目录 (默认与输入同目录)')
    args = parser.parse_args()
    
    if not os.path.exists(args.image_path):
        print(f"❌ 图像不存在: {args.image_path}")
        sys.exit(1)
    
    # TODO: 施工阶段 — 执行完整管线
    print(f"📸 Vision→3D 测量管线")
    print(f"   输入: {args.image_path}")
    print(f"   管线就绪，等待 Builder 施工")


if __name__ == '__main__':
    main()
