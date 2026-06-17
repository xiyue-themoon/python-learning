"""
========================================
my_utils.py — 一个自己写的模块（供 step9 调用）
========================================
知识点: 模块就是一个 .py 文件，可以被别的文件 import
========================================
"""

# 这个变量在模块顶层，等同于模块的"全局设置"
VERSION = "1.0"

def greet(name):
    """打招呼函数"""
    return f"你好，{name}！"

def add(a, b):
    """加法"""
    return a + b

def celsius_to_fahrenheit(c):
    """摄氏度转华氏度"""
    return c * 9 / 5 + 32

# 这个类也可以被外部导入
class Calculator:
    def __init__(self, name="默认计算器"):
        self.name = name
        self.history = []

    def add(self, a, b):
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def show_history(self):
        return self.history

# ===== 关键概念：__name__ =====
# 当直接运行 python my_utils.py 时，__name__ 是 "__main__"
# 当被其他文件 import 时，__name__ 是 "my_utils"
print(f"  [my_utils] __name__ = {__name__!r}")

if __name__ == "__main__":
    # 这里的代码只有在"直接运行"这个文件时才会执行
    # 被 import 时不会执行
    print("  [my_utils] 我是被直接运行的！做自测...")
    print(f"  [my_utils] greet('世界') → {greet('世界')}")
    print(f"  [my_utils] 30°C = {celsius_to_fahrenheit(30)}°F")
