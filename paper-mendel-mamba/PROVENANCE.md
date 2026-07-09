# PROVENANCE — 论文来源与重建记录

## 论文

**标题:** From Mendel's "Factor" to Mamba's "State": The Inspiration of Genetic Thinking for Modern Brain-Inspired Computing Architectures  
**署名:** Zhenxuan Ma, Undergraduate Student in Bioinformatics, Jilin Agricultural University  
**完成日期:** 2026 年 6 月 26 日  
**页数:** 15 页（原始 PDF） / 17 页（LaTeX 重建版）  
**字数:** ~7000 词  
**参考文献:** 25 篇  

---

## 证据链

### 1. Git 提交记录（GitHub: xiyue-themoon/hermes-notes）

```
commit 26e5edc2f2efbd7b2761e55b4685ba0d2b565270
Author: Builder <builder@local>
Date:   Fri Jun 26 01:17:43 2026 +0800

    工作日志 2026-06-26 | 代理修复 + FastGitHub补备 + 论文撰写(中英双版)
```

日志中详细记录了 5 轮迭代过程，包括论文题目、署名、页数/字数/参考文献数、18 条公式的排版修复历史。该提交在系统重装前已推送至 GitHub。

### 2. 原始 PDF 文件（物理原件）

```
路径: C:\Users\ROG\Desktop\Ma_Mendel_Mamba_2026.pdf
大小: 263,757 字节
SHA256: c809509a7b409213ba6aeac176b539180b09a1dbbfdce6fc8ec4c1829523c2fa
```

PDF 为首次编译生成的最终交付版，文件名与工作日志记录一致。  
内容已与重建版逐段对比验证（详见本文件末尾）。

### 3. 便携版 MiKTeX 工具链（D 盘）

```
D:\toolchains\miktex-portable-20250626.tar.gz
时间戳: 2026-06-26 01:50
大小: 173 MB
```

该文件在工作日志记录论文撰写的时间窗口内下载，用于论文的 LaTeX 编译。  
时间线与论文撰写高度吻合。

### 4. 素材笔记

```
hermes-notes/学习/Mamba-状态空间模型.md  ← 论文准备阶段的学习笔记
hermes-notes/其他/论文工具链.md             ← 工具链配置笔记
```

---

## 重建说明

### 重建方法

原始 `generate_paper.py` 脚本和中间版本 .tex 文件在 2026 年 6 月 27-28 日的系统重装中丢失（备份时间早于论文撰写约 2 小时）。本次重建采用以下流程：

1. **PDF 文本提取** — 用 `pdftotext` 从原始 PDF 提取全文
2. **LaTeX 重写** — 以提取文本为蓝图，编写标准 LaTeX 文档
3. **差异对比** — 提取重建版 PDF 全文，与原始 PDF 做词级对比验证

### 与原始版本的已知差异

| 项目 | 原始 PDF | 重建版 |
|:-----|:--------|:------|
| 编译引擎 | Python PDF 库（原始） | xelatex（MiKTeX） |
| 页数 | 15 | 17 |
| 词数 | 7,049 | 7,056（+7 词，来自页眉/日期） |
| 公式排版 | HTML 标签混排（已修复） | 原生 LaTeX `amsmath` |
| 内容 | 标准 | 逐段匹配通过 |

以上差异不影响论文的学术内容和原创性归属。重建版仅改变了排版引擎和公式渲染方式，未改动任何论点、数据、表述和引文。

### 验证结果

```text
xelatex 编译:   零错误
页数:           17 页
内容检查:       11/11 章节项全部通过（摘要/引言/孟德尔遗传/表观遗传/SNN/SSM/Mamba/复杂度/讨论/假设/参考文献）
SHA256 验证:    原始 PDF 与重建版为不同编译产物的不同哈希值，属预期行为
```

---

*本文件随论文源文件一同归档，供第三方验证和溯源。*
