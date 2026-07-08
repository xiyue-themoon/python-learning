"""JSON exporter — 管线结果序列化
"""

import json
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def export_json(result: dict, output_path: str) -> str:
    """Export pipeline result to JSON file.

    Args:
        result: Pipeline result dict from run_S_grid or similar.
        output_path: Path to write JSON file.

    Returns:
        The output path.
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, cls=NumpyEncoder, ensure_ascii=False)
    return output_path
