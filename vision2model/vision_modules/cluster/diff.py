"""差分聚簇 (np.diff + 阈值分组)

注册为 cluster_diff:
  function=cluster, size=all, accuracy=3, robustness=3, speed=fast
"""

import numpy as np
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'cluster_diff',
    function='cluster',
    size='all',
    accuracy=3,
    robustness=3,
    speed='fast',
    gpu='none',
    deps=[],
)
def cluster_diff(values, *, threshold: float = 10.0):
    """Cluster 1D values by difference threshold.

    Groups consecutive values whose difference < threshold.

    Args:
        values: 1D numpy array of values to cluster.
        threshold: Maximum difference within a cluster.

    Returns:
        dict with keys:
          'clusters': list of list of values
          'n_clusters': int
          'means': list of cluster means
    """
    values = np.sort(values)
    if len(values) == 0:
        return {'clusters': [], 'n_clusters': 0, 'means': []}

    clusters = []
    current = [values[0]]
    for v in values[1:]:
        if v - current[-1] <= threshold:
            current.append(v)
        else:
            clusters.append(current)
            current = [v]
    clusters.append(current)

    means = [float(np.mean(c)) for c in clusters]
    return {
        'clusters': [[float(x) for x in c] for c in clusters],
        'n_clusters': len(clusters),
        'means': means,
    }


_validation_errors = validate_tags({'function': 'cluster', 'size': 'all', 'accuracy': 3})
if _validation_errors:
    raise RuntimeError(f'cluster_diff tag validation failed: {_validation_errors}')
