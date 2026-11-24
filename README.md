# 2048 桌面版

一个基于 **Python 3 + pygame** 实现的 2048 数字合并小游戏，支持 Windows 单文件 **exe 打包分发**，无需目标机器安装 Python 环境。

---

## 一、项目速览

| 项目 | 说明 |
| --- | --- |
| 产品名称 | 2048 桌面版（2048 Desktop） |
| 运行形态 | Windows 桌面窗口程序（python 脚本 ／ exe 可执行文件） |
| 技术栈 | Python 3.12（conda `game` 环境）/ pygame 2.5+ / PyInstaller 6.x |
| 核心玩法 | 4×4 棋盘，方向键操作，相同数字合并，达到 2048 通关 |
| 代码规模 | 约 1700 行（含注释与测试） |
| 交付物 | 源码工程、文档集、单个 `2048.exe` |

## 二、文档索引

建议按序号阅读；只想快速跑起来，看第 6、7 篇即可。

| 序号 | 文档 | 内容 | 主要读者 |
| --- | --- | --- | --- |
| 01 | [需求规格说明书](docs/01-需求规格说明书.md) | 功能需求、非功能需求、验收标准、需求边界 | 产品／讲师／开发 |
| 02 | [概要设计说明书](docs/02-概要设计说明书.md) | 总体架构、分层设计、模块划分、目录结构、数据流 | 开发 |
| 03 | [详细设计说明书](docs/03-详细设计说明书.md) | 核心算法、数据结构、类与函数签名、关键流程、渲染实现 | 开发 |
| 04 | [开发规范与环境搭建](docs/04-开发规范与环境搭建.md) | 环境准备、依赖管理、编码规范、协作约定 | 开发 |
| 05 | [测试计划与测试用例](docs/05-测试计划与测试用例.md) | 测试策略、单元测试用例、UI 手工用例、缺陷等级 | 开发／测试 |
| 06 | [打包发布指南](docs/06-打包发布指南.md) | PyInstaller 打包 exe 全流程、资源路径、常见坑与排查 | 开发／发布 |
| 07 | [用户操作手册](docs/07-用户操作手册.md) | 安装、操作、计分规则、常见问题 | 最终用户 |

## 三、工程目录结构

工程结构如下（源码已落地，可直接 `python main.py` 运行）：

```
2048/
├── main.py                 # 程序入口：窗口/全屏、主菜单与游戏主循环
├── requirements.txt        # 依赖清单
├── pytest.ini              # pytest 路径配置
├── 2048.spec               # PyInstaller 打包配置
├── version_info.txt        # exe 版本信息（已启用）
├── assets/
│   ├── icon.ico            # exe / 任务栏图标（含 16~256 多尺寸）
│   ├── icon.png            # 窗口图标（64×64，pygame 加载）
│   └── fonts/msyh.ttc      # 随包字体，保证中文显示
├── src/
│   ├── config.py           # 尺寸、颜色、概率、动画与昵称长度等常量
│   ├── board.py            # 棋盘核心逻辑（纯模型，可单测）
│   ├── game.py             # 游戏状态机（运行/胜利/结束、计分、撤销）
│   ├── storage.py          # 数据持久化（最高分/设置/排行榜）
│   ├── resource.py         # 资源路径解析（兼容 exe 运行）
│   └── ui/
│       ├── theme.py        # 配色、字号与各界面布局常量
│       ├── renderer.py     # 棋盘/菜单/设置/排行榜/昵称/弹窗绘制
│       └── animator.py     # 滑动/合并/新块弹出动画
├── tests/
│   ├── test_board.py       # 棋盘规则单元测试
│   ├── test_game.py        # 状态机单元测试
│   └── test_storage.py     # 排行榜与存档单元测试
└── docs/                   # 本文档集
```

## 四、快速开始

```bash
# 1. 安装依赖
python -m pip install -r requirements.txt

# 2. 运行
python main.py

# 3. 跑单元测试（可选）
pytest -q

# 4. 打包成单文件 exe
pyinstaller 2048.spec --clean --noconfirm
# 产物：dist/2048.exe
```

## 五、游戏图片

<p align="center">
  <img src="screenshots/start.png" alt="2048 开始界面" width="564">
</p>

<p align="center">
  <img src="screenshots/play.png" alt="2048 游戏界面" width="564">
</p>

<p align="center">
  <img src="screenshots/order.png" alt="2048 排行界面" width="564">
</p>