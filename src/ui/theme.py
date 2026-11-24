"""主题：数值→配色、位数→字号、格子与按钮的布局坐标。

表现层，只提供常量与纯函数，不接触模型状态。
"""

from __future__ import annotations

from ..config import BOARD_X, BOARD_Y, CELL_PX, EMPTY_COLOR, GRID_PADDING, TEXT_DARK, TEXT_LIGHT

TILE_COLORS: dict[int, tuple[int, int, int]] = {
    0: EMPTY_COLOR,
    2: (238, 228, 218),
    4: (237, 224, 200),
    8: (242, 177, 121),
    16: (245, 149, 99),
    32: (246, 124, 95),
    64: (246, 94, 59),
    128: (237, 207, 114),
    256: (237, 204, 97),
    512: (237, 200, 80),
    1024: (237, 197, 63),
    2048: (237, 194, 46),
}
DARK_TILE = (60, 58, 50)            # >2048 统一深色
BUTTON_COLOR = (143, 122, 102)      # 「新游戏」与浮层按钮底色
CONFIRM_OK_COLOR = (245, 149, 99)   # 确认弹窗主按钮底色
EMPTY_ACCENT = (226, 218, 207)      # 排行榜分隔线

# 布局矩形 (x, y, w, h)：绘制与点击检测共用同一份常量，避免视觉与热区错位
SCORE_BOX = (300, 32, 110, 64)
BEST_BOX = (426, 32, 110, 64)
NEW_GAME_BTN = (40, 645, 132, 44)
OVERLAY_CARD = (80, 220, 400, 280)
OVERLAY_BTN_LEFT = (118, 400, 150, 48)
OVERLAY_BTN_RIGHT = (292, 400, 150, 48)
OVERLAY_BTN_SINGLE = (205, 400, 150, 48)
CONFIRM_CARD = (110, 300, 340, 200)
CONFIRM_CANCEL_BTN = (152, 428, 120, 46)
CONFIRM_OK_BTN = (288, 428, 120, 46)

# 主菜单
MENU_BTN_START = (190, 300, 180, 56)
MENU_BTN_SETTINGS = (190, 372, 180, 56)
MENU_BTN_RANKING = (190, 444, 180, 56)
MENU_BTN_EXIT = (190, 516, 180, 56)

# 设置页
SET_WINDOW_BTN = (150, 320, 260, 56)
SET_FULLSCREEN_BTN = (150, 392, 260, 56)
BACK_BTN = (40, 645, 110, 44)

# 排行榜与昵称输入
RANK_CARD = (70, 180, 420, 420)
NAME_INPUT_BOX = (130, 350, 300, 56)


def tile_color(value: int) -> tuple[int, int, int]:
    return TILE_COLORS.get(value, DARK_TILE)


def text_color(value: int) -> tuple[int, int, int]:
    return TEXT_DARK if value in (0, 2, 4) else TEXT_LIGHT


def font_size(value: int) -> int:
    """按位数下调字号，保证大数字不溢出格子。"""
    digits = len(str(value)) if value else 1
    return {1: 46, 2: 46, 3: 38, 4: 30, 5: 24}.get(digits, 20)


def cell_rect(r: int, c: int) -> tuple[int, int, int, int]:
    """第 (r, c) 格在窗口中的矩形；绘制与点击检测都调它。"""
    step = CELL_PX + GRID_PADDING
    return (
        BOARD_X + GRID_PADDING + c * step,
        BOARD_Y + GRID_PADDING + r * step,
        CELL_PX,
        CELL_PX,
    )
