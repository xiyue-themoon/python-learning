"""DBSCAN 空间聚簇

注册为 cluster_dbscan:
  function=cluster, size=all, accuracy=4, robustness=3, speed=slow
"""

import numpy as np
from sklearn.cluster import DBSCAN as SklearnDBSCAN
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'cluster_dbscan',
    function='cluster',
    size='all',
    accuracy=4,
    robustness=3,
    speed='slow',
    gpu='none',
    deps=['scikit-learn'],
)
def cluster_dbscan(points, *, eps: float = 10.0, min_samples: int = 2):
    """Cluster 2D points using DBSCAN.

    Args:
        points: Nx2 numpy array of (x, y) coordinates.
        eps: Maximum distance between two samples for one neighborhood.
        min_samples: Min points to form a dense region.

    Returns:
        dict with keys:
          'labels': cluster labels (-1 = noise)
          'n_clusters': number of clusters found (excluding noise)
          'n_noise': number of noise points
          'clusters': dict of cluster_id -> list of points
          'centroids': dict of cluster_id -> (cx, cy) centroid
    """
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim == 1:
        pts = pts.reshape(-1, 1)
    if len(pts) < min_samples:
        return {
            'labels': np.array([-1] * len(pts)),
            'n_clusters': 0,
            'n_noise': len(pts),
            'clusters': {},
            'centroids': {},
        }

    clustering = SklearnDBSCAN(eps=eps, min_samples=min_samples).fit(pts)
    labels = clustering.labels_

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = int((labels == -1).sum())

    clusters = {}
    centroids = {}
    for label in set(labels):
        if label == -1:
            continue
        mask = labels == label
        cluster_pts = pts[mask]
        clusters[int(label)] = cluster_pts.tolist()
        centroids[int(label)] = cluster_pts.mean(axis=0).tolist()

    return {
        'labels': labels.tolist(),
        'n_clusters': n_clusters,
        'n_noise': n_noise,
        'clusters': clusters,
        'centroids': centroids,
    }


_validation_errors = validate_tags({'function': 'cluster', 'size': 'all', 'accuracy': 4})
if _validation_errors:
    raise RuntimeError(f'cluster_dbscan validation: {_validation_errors}')
