"""Vision→3D 测量管线 — 模块注册表"""

MODULE_REGISTRY = {}


def register(name, **tags):
    """注册检测算法模块
    
    Args:
        name: 模块唯一标识名
        **tags: 标签键值对 (function/size/accuracy/robustness/speed/gpu/deps/beta)
    
    Returns:
        装饰器，将函数注册到 MODULE_REGISTRY
    """
    def decorator(fn):
        MODULE_REGISTRY[name] = {'fn': fn, 'tags': tags}
        return fn
    return decorator


def find_modules(**filters):
    """按标签条件查询已注册模块
    
    Args:
        **filters: 筛选条件，如 function='blob_detect', size='S'
    
    Returns:
        list[(name, entry)] 匹配的模块列表，按 accuracy 降序
    """
    results = []
    for name, entry in MODULE_REGISTRY.items():
        tags = entry['tags']
        match = True
        for k, v in filters.items():
            tag_val = tags.get(k)
            if k == 'size':
                # size='all' 匹配任何尺寸
                if tag_val == 'all':
                    continue
                # size 支持 'S|M' 格式
                if isinstance(v, str) and v not in str(tag_val).split('|'):
                    match = False
                    break
            elif k == 'accuracy' and isinstance(v, int):
                if tag_val is None or tag_val < v:
                    match = False
                    break
            elif k == 'robustness' and isinstance(v, int):
                if tag_val is None or tag_val < v:
                    match = False
                    break
            else:
                if tag_val != v:
                    match = False
                    break
        if match:
            results.append((name, entry))
    
    # 按 accuracy 降序
    results.sort(key=lambda x: x[1]['tags'].get('accuracy', 0), reverse=True)
    return results


def list_all_modules():
    """列出所有已注册模块"""
    for name, entry in MODULE_REGISTRY.items():
        tags = entry['tags']
        print(f"  [{name}]  func={tags.get('function','?')}  "
              f"size={tags.get('size','?')}  acc={tags.get('accuracy','?')}  "
              f"robust={tags.get('robustness','?')}")
