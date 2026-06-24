"""
================================================================
d2l §4.3: 多层感知机简洁实现 —— MLP Concise
================================================================
和 4.2 手搓版做同一件事（Fashion-MNIST 分类），
但用 PyTorch 高级 API，代码量从 270 行 → 20 行。

对比 4.2 手搓版，看看「简洁」到底简洁在哪：

  4.2 手搓                   →  4.3 简洁
  ─────────────────────────────────────────────
  手动定义参数 W1,b1,W2,b2    →  nn.Linear(784, 256) 自动管参数
  手动写 relu(X)              →  nn.ReLU() 直接当层用
  手动写 cross_entropy        →  nn.CrossEntropyLoss()
  手动 SGD 循环 param -= lr*g →  torch.optim.SGD(net.parameters(), lr)
  手动 for 训练循环            →  d2l.train_ch3() 一行训练

运行方式: python d2l_43_mlp_concise.py
依赖: d2l 环境（pip install d2l）
"""

import torch
from torch import nn
from d2l import torch as d2l

# ======================== 1. 加载数据 ========================
# 同一份 Fashion-MNIST，d2l 封装好了下载 + DataLoader
batch_size = 256
train_iter, test_iter = d2l.load_data_fashion_mnist(batch_size)


# ======================== 2. 模型 ========================
#
# nn.Sequential：把层按顺序串起来，输入依次流过每层
#
# 输入:  (batch, 1, 28, 28)     ← 原始图片（通道1，高28，宽28）
#   │
#   ▼
# nn.Flatten()
#   │  拉平: (batch, 1, 28, 28) → (batch, 784)
#   ▼
# nn.Linear(784, 256)
#   │  全连接: (batch, 784) → (batch, 256)
#   │  = 相当于 4.2 的 X @ W1 + b1
#   ▼
# nn.ReLU()
#   │  激活: max(0, x)，砍掉负数
#   ▼
# nn.Linear(256, 10)
#   │  全连接: (batch, 256) → (batch, 10)
#   │  = 相当于 4.2 的 h @ W2 + b2
#   ▼
# 输出: (batch, 10)              ← 10 个类别的 logits

net = nn.Sequential(
    nn.Flatten(),          # ① 拉平图片 → 一维向量
    nn.Linear(784, 256),   # ② 隐藏层：784维 → 256维
    nn.ReLU(),             # ③ 激活函数（引入非线性）
    nn.Linear(256, 10)     # ④ 输出层：256维 → 10个类别
)


# ======================== 3. 初始化权重 ========================
#
# nn.Linear 默认用 Kaiming 初始化（对 ReLU 友好的方法），
# 但 d2l 为了和 4.2 公平对比，手动改成 N(0, 0.01) 初始化。
#
# net.apply(fn)：对 net 里的每一层执行 fn
# type(m) == nn.Linear：只对 Linear 层初始化（跳过 Flatten 和 ReLU）

def init_weights(m):
    """如果 m 是 Linear 层，用正态分布 N(0, 0.01) 初始化权重"""
    if type(m) == nn.Linear:
        nn.init.normal_(m.weight, std=0.01)

net.apply(init_weights)


# ======================== 4. 训练 ========================
#
# 对比 4.2 手搓版，这里 3 行搞定训练配置：
#   - 损失函数：交叉熵（内部自动做 softmax）
#   - 优化器：SGD（自动遍历 net.parameters()）
#   - 训练循环：d2l.train_ch3 封装好了

loss = nn.CrossEntropyLoss(reduction='none')   # 交叉熵损失
trainer = torch.optim.SGD(net.parameters(), lr=0.1)  # SGD 优化器

num_epochs = 10
d2l.train_ch3(net, train_iter, test_iter, loss, num_epochs, trainer)


# ======================== 对比总结 ========================
"""
┌──────────────────────┬──────────────────────┬──────────────────┐
│       环节            │   4.2 手搓版          │   4.3 简洁版      │
├──────────────────────┼──────────────────────┼──────────────────┤
│ 模型定义              │ init_mlp_params()    │ nn.Sequential()  │
│ 前向传播              │ mlp_forward()        │ net(X) 自动执行   │
│ 激活函数              │ def relu(): ...      │ nn.ReLU()        │
│ 损失函数              │ def cross_entropy()  │ nn.CrossEntropyLoss│
│ 参数更新              │ for p in params:     │ optimizer.step() │
│                      │   p -= lr * p.grad   │                  │
│ 训练循环              │ 手写双层 for 循环     │ d2l.train_ch3()  │
│ 代码行数              │ ~270 行              │ ~20 行           │
└──────────────────────┴──────────────────────┴──────────────────┘

核心思想：
  高级 API 把「做什么」和「怎么做」分离了。
  - 你只管说：网络长什么样（Sequential）
  - 框架管：参数怎么初始化、梯度怎么算、权重怎么更新

下一节 4.4 开始讲：模型选错了会怎样？（过拟合/欠拟合）
"""
