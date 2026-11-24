"""全局常量：尺寸、配色、概率、动画时长与应用信息。

本模块只依赖标准库，不 import 任何业务模块（docs/02 §2 分层依赖规则）。
"""

APP_NAME = "2048"
APP_ID = "2048Desktop"
VERSION = "1.0.0"

GRID_SIZE = 4                 # 棋盘边长
SPAWN_4_PROB = 0.1            # 新方块为 4 的概率
WIN_VALUE = 2048              # 通关阈值

WINDOW_W, WINDOW_H = 560, 720
BOARD_PX = 480                # 棋盘边长（像素）
BOARD_X, BOARD_Y = 40, 140    # 棋盘左上角在窗口中的坐标
GRID_PADDING = 12             # 格子间距
CELL_PX = (BOARD_PX - GRID_PADDING * (GRID_SIZE + 1)) // GRID_SIZE   # = 105

FPS = 60
ANIM_MS = 140                 # 单次移动动画时长（毫秒）

# 颜色（经典 2048 主题）
BG_COLOR = (250, 248, 239)
BOARD_COLOR = (187, 173, 160)
EMPTY_COLOR = (205, 193, 180)
TEXT_DARK = (119, 110, 101)
TEXT_LIGHT = (249, 246, 242)
SCORE_BG = (187, 173, 160)

DEBUG = False                 # 发布前必须为 False（docs/04 §4.1）
