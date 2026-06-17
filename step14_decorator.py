"""
============================================
Step 14 — 装饰器：在不改原函数的前提下加功能
============================================
概念清单:
  1. Python 里"函数也是对象"——可以传来传去
  2. 装饰器是什么：包在函数外面的函数
  3. 基础装饰器写法
  4. @ 语法糖
  5. 带参数的装饰器
  6. 实际用途（日志/计时/权限）
============================================
"""


# ========== 0. 前置：函数也是对象 ==========
print("=" * 60)
print("0. 先理解：函数可以当变量传来传去")
print("=" * 60)


def greet(name):
    return f"你好, {name}"


# 函数可以赋值给变量
f = greet
print(f"直接调用 greet: {greet('小明')}")
print(f"通过变量调用 f:  {f('小明')}")

# 函数可以作为参数传给另一个函数
def run_twice(func, arg):
    print(func(arg))
    print(func(arg))

print("\n把 greet 函数作为参数:")
run_twice(greet, "小红")
print("  → 函数就像变量一样，可以被传递 ✅")


# ========== 1. 装饰器是什么 ==========
print("\n" + "=" * 60)
print("1. 装饰器 — 不改原函数，给原函数加功能")
print("=" * 60)

# 想计算某个函数的执行时间，但不改函数内部代码
import time


def timer_decorator(func):
    """装饰器：给函数加计时功能"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)  # 执行原函数
        elapsed = time.time() - start
        print(f"  ⏱ {func.__name__} 耗时: {elapsed:.4f}秒")
        return result
    return wrapper


# 手动应用装饰器
def slow_add(a, b):
    time.sleep(0.1)
    return a + b

slow_add = timer_decorator(slow_add)  # 用装饰器替换原函数
result = slow_add(3, 5)
print(f"  slow_add(3, 5) = {result}")


# ========== 2. @ 语法糖 ==========
print("\n" + "=" * 60)
print("2. @ 语法糖 — 不用手动赋值")
print("=" * 60)


@timer_decorator  # ← 等价于 slow_multiply = timer_decorator(slow_multiply)
def slow_multiply(a, b):
    time.sleep(0.05)
    return a * b


result = slow_multiply(4, 7)
print(f"  slow_multiply(4, 7) = {result}")
print("  @timer_decorator 就是简写 ✅")


# ========== 3. 实战：日志装饰器 ==========
print("\n" + "=" * 60)
print("3. 实战：日志装饰器（d2l 里也有类似用法）")
print("=" * 60)


def log_call(func):
    """记录函数被调用了"""
    def wrapper(*args, **kwargs):
        print(f"  → 调用 {func.__name__}(args={args}, kwargs={kwargs})")
        result = func(*args, **kwargs)
        print(f"  ← 返回 {result}")
        return result
    return wrapper


@log_call
def train_epoch(data_size, lr=0.01):
    """模拟一个训练轮次"""
    return f"trained {data_size} samples with lr={lr}"


train_epoch(100)
train_epoch(200, lr=0.001)


# ========== 4. 多个装饰器叠加 ==========
print("\n" + "=" * 60)
print("4. 装饰器可以叠加")
print("=" * 60)


@timer_decorator
@log_call
def heavy_compute(n):
    """计时 + 日志 双重装饰"""
    total = sum(i**2 for i in range(n))
    return total


result = heavy_compute(10000)
print(f"  heavy_compute(10000) = {result}")
print("  装饰器从下往上应用：先 log_call，再 timer_decorator")


# ========== 5. d2l 里你会看到的装饰器 ==========
print("\n" + "=" * 60)
print("5. d2l / PyTorch 里你会遇到的装饰器")
print("=" * 60)

print("""
  @torch.no_grad()           ← 推理时不需要计算梯度
  @torch.jit.script           ← 把函数优化成 TorchScript
  @nn.Module.register_buffer  ← 注册非参数张量

  你现在不需要深究它们怎么实现，
  只需要知道：@ 符号 = 给函数加了一层功能。
""")

print("""
✅ 装饰器总结：
  装饰器 = "我不想改你的代码，但我想给你的功能加点料"
  @xxx   = 简写方式，等价于 func = xxx(func)
  你写 d2l 时至少会用到 @torch.no_grad()
""")
