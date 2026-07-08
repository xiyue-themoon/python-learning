"""Vision→3D 模块标签系统"""

TAG_SCHEMA = {
    'function':     str,    # 功能域
    'size':         str,    # S | M | L | S|M | M|L | all
    'accuracy':     int,    # 1-5
    'robustness':   int,    # 1-5
    'speed':        str,    # fast | medium | slow
    'gpu':          str,    # none | optional | required
    'deps':         list,   # ['opencv', 'scipy', ...]
    'beta':         bool,   # True = 实验性
}

REQUIRED_TAGS = ['function', 'size', 'accuracy']

VALID_SIZES = {'S', 'M', 'L', 'S|M', 'M|L', 'all'}


def validate_tags(tags: dict) -> list[str]:
    """验证标签是否满足 schema 要求
    
    Returns:
        list[str] 错误信息列表，空列表表示验证通过
    """
    errors = []
    for required in REQUIRED_TAGS:
        if required not in tags:
            errors.append(f"缺少必填标签: {required}")
    
    for key, value in tags.items():
        if key not in TAG_SCHEMA:
            errors.append(f"未知标签: {key}")
            continue
        
        expected_type = TAG_SCHEMA[key]
        if not isinstance(value, expected_type):
            errors.append(f"标签 '{key}' 应为 {expected_type.__name__}, 实际为 {type(value).__name__}")
    
    # accuracy 和 robustness 范围校验
    if 'accuracy' in tags and not (1 <= tags['accuracy'] <= 5):
        errors.append(f"accuracy 应为 1-5, 实际为 {tags['accuracy']}")
    if 'robustness' in tags and not (1 <= tags['robustness'] <= 5):
        errors.append(f"robustness 应为 1-5, 实际为 {tags['robustness']}")
    if 'size' in tags and tags['size'] not in VALID_SIZES:
        errors.append(f"size 应为 {VALID_SIZES}, 实际为 {tags['size']}")
    
    return errors
