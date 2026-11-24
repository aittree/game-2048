"""渲染器：每帧绘制背景、标题区、棋盘、方块、操作区与浮层。

棋盘方块支持滑动／合并／新块弹出动画；逻辑在按键瞬间已结算，动画只做视觉插值。
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from ..config import (
    APP_NAME,
    BG_COLOR,
    BOARD_COLOR,
    BOARD_PX,
    BOARD_X,
    BOARD_Y,
    GRID_SIZE,
    MAX_NAME_LEN,
    SCORE_BG,
    TEXT_DARK,
    TEXT_LIGHT,
    WINDOW_H,
    WINDOW_W,
)
from ..game import Action, GameSnapshot, GameState
from . import theme
from .animator import (
    MERGE_PULSE,
    NEW_TILE_APPEAR_RATIO,
    NEW_TILE_START_SCALE,
    SLIDE_RATIO,
    ease_out_cubic,
    lerp,
)

if TYPE_CHECKING:
    from ..storage import Record
    from .animator import Animator

_MERGE_SHRINK_RATIO = 0.35   # 合并源块在落定阶段前 35% 内收缩消失


class Renderer:
    def __init__(self, font_path: str) -> None:
        self.font_path = font_path
        self._fonts: dict[int, pygame.font.Font] = {}

    # —— 字体（带缓存与降级） ——
    def _font(self, size: int) -> pygame.font.Font:
        font = self._fonts.get(size)
        if font is None:
            try:
                font = pygame.font.Font(self.font_path, size)
            except (FileNotFoundError, pygame.error):
                font = pygame.font.SysFont("microsoftyahei", size)   # 随包字体缺失时降级
            self._fonts[size] = font
        return font

    # —— 每帧入口 ——
    def draw(
        self,
        screen: pygame.Surface,
        snapshot: GameSnapshot,
        animator: "Animator | None" = None,
        can_record: bool = False,
    ) -> None:
        screen.fill(BG_COLOR)
        self._draw_header(screen, snapshot)
        self._draw_board(screen, snapshot, animator)
        self._draw_footer(screen)
        # 浮层等本手动画播完再出现，避免通关/结束的最后一手被遮住
        if snapshot.state is not GameState.RUNNING and (animator is None or not animator.active):
            self._draw_overlay(screen, snapshot, can_record)

    # —— 标题区：标题 + 分数 + 最高分 ——
    def _draw_header(self, screen: pygame.Surface, snapshot: GameSnapshot) -> None:
        title = self._font(64).render(APP_NAME, True, TEXT_DARK)
        screen.blit(title, (40, 30))
        self._draw_stat(screen, theme.SCORE_BOX, "分数", snapshot.score)
        self._draw_stat(screen, theme.BEST_BOX, "最高分", snapshot.best)

    def _draw_stat(
        self, screen: pygame.Surface, rect_xywh: tuple[int, int, int, int], label: str, value: int
    ) -> None:
        x, y, w, h = rect_xywh
        pygame.draw.rect(screen, SCORE_BG, pygame.Rect(x, y, w, h), border_radius=8)
        label_surf = self._font(16).render(label, True, (238, 228, 218))
        screen.blit(label_surf, label_surf.get_rect(center=(x + w / 2, y + 20)))
        size = 26 if value < 100000 else 20
        value_surf = self._font(size).render(str(value), True, TEXT_LIGHT)
        screen.blit(value_surf, value_surf.get_rect(center=(x + w / 2, y + h - 20)))

    # —— 棋盘：底板 + 16 格 + 静态方块 + 动画方块 ——
    def _draw_board(
        self, screen: pygame.Surface, snapshot: GameSnapshot, animator: "Animator | None"
    ) -> None:
        pygame.draw.rect(
            screen, BOARD_COLOR, pygame.Rect(BOARD_X, BOARD_Y, BOARD_PX, BOARD_PX), border_radius=12
        )
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                pygame.draw.rect(
                    screen, theme.tile_color(0), pygame.Rect(theme.cell_rect(r, c)), border_radius=8
                )

        anim = animator if animator is not None and animator.active else None
        result = anim.result if anim is not None else None

        # 动画接管的目标格与新生格：静态层跳过，避免同一数字绘制两次
        involved: set[tuple[int, int]] = set()
        if anim is not None and result is not None:
            involved = {dst for _v, _src, dst in result.slides}
            if anim.new_pos is not None:
                involved.add(anim.new_pos)

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                value = snapshot.grid[r][c]
                if value and (r, c) not in involved:
                    self._draw_tile(screen, pygame.Rect(theme.cell_rect(r, c)), value)

        if anim is None or result is None:
            return

        p = anim.progress
        if p < SLIDE_RATIO:
            self._draw_slides(screen, result, ease_out_cubic(p / SLIDE_RATIO))
        else:
            self._draw_settled(screen, result, (p - SLIDE_RATIO) / (1 - SLIDE_RATIO))
        self._draw_new_tile(screen, snapshot, anim, p)

    def _draw_new_tile(self, screen: pygame.Surface, snapshot: GameSnapshot, anim, p: float) -> None:
        """新块从滑动后半程开始弹出，避免「等动画完才出现」的延迟感。"""
        if anim.new_pos is None or p < NEW_TILE_APPEAR_RATIO:
            return
        t = min(1.0, (p - NEW_TILE_APPEAR_RATIO) / (1 - NEW_TILE_APPEAR_RATIO))
        r, c = anim.new_pos
        self._draw_tile(
            screen,
            pygame.Rect(theme.cell_rect(r, c)),
            snapshot.grid[r][c],
            lerp(NEW_TILE_START_SCALE, 1.0, t),
        )

    def _draw_slides(self, screen: pygame.Surface, result, t: float) -> None:
        """滑动阶段：按 slide 记录的起终点插值，速度前快后慢。"""
        for value, src, dst in result.slides:
            start = pygame.Rect(theme.cell_rect(*src))
            end = pygame.Rect(theme.cell_rect(*dst))
            rect = pygame.Rect(
                int(lerp(start.x, end.x, t)),
                int(lerp(start.y, end.y, t)),
                start.w,
                start.h,
            )
            self._draw_tile(screen, rect, value)

    def _draw_settled(self, screen: pygame.Surface, result, q: float) -> None:
        """合并阶段：未合并的块停在终点，合并源收缩，合并目标回弹放大。"""
        merge_targets = {(r, c) for r, c, _v in result.merges}
        for value, _src, dst in result.slides:
            if dst not in merge_targets:
                self._draw_tile(screen, pygame.Rect(theme.cell_rect(*dst)), value)

        # 落定初期让合并源块收缩消失，避免 0.7 处的硬切
        if q < _MERGE_SHRINK_RATIO:
            shrink = 1.0 - 0.3 * (q / _MERGE_SHRINK_RATIO)
            drawn: set[tuple[int, int]] = set()
            for value, _src, dst in result.slides:
                if dst in merge_targets and dst not in drawn:
                    drawn.add(dst)
                    self._draw_tile(screen, pygame.Rect(theme.cell_rect(*dst)), value, shrink)

        scale = 1.0 + MERGE_PULSE * math.sin(math.pi * q)
        for r, c, value in result.merges:
            self._draw_tile(screen, pygame.Rect(theme.cell_rect(r, c)), value, scale)

    def _draw_tile(self, screen: pygame.Surface, rect: pygame.Rect, value: int, scale: float = 1.0) -> None:
        center = rect.center
        if scale != 1.0:
            rect = pygame.Rect(0, 0, max(1, int(rect.w * scale)), max(1, int(rect.h * scale)))
            rect.center = center
        pygame.draw.rect(screen, theme.tile_color(value), rect, border_radius=8)
        if value == 0:
            return
        font = self._font(max(8, int(theme.font_size(value) * scale)))
        text = font.render(str(value), True, theme.text_color(value))
        screen.blit(text, text.get_rect(center=rect.center))

    # —— 操作区：新游戏按钮 + 操作提示 ——
    def _draw_footer(self, screen: pygame.Surface) -> None:
        self._draw_button(screen, theme.NEW_GAME_BTN, "新游戏")
        hint = self._font(18).render("方向键 / WASD 操作", True, TEXT_DARK)
        screen.blit(hint, hint.get_rect(center=(380, 667)))

    # —— 通关 / 结束浮层 ——
    def _draw_overlay(self, screen: pygame.Surface, snapshot: GameSnapshot, can_record: bool) -> None:
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill((250, 248, 239, 200))
        screen.blit(overlay, (0, 0))

        card = pygame.Rect(theme.OVERLAY_CARD)
        pygame.draw.rect(screen, (255, 255, 255), card, border_radius=16)

        if snapshot.state is GameState.WIN:
            title_text, title_size = "恭喜达成 2048", 32
        else:
            title_text, title_size = "游戏结束", 36
        title = self._font(title_size).render(title_text, True, TEXT_DARK)
        screen.blit(title, title.get_rect(center=(card.centerx, card.y + 55)))

        detail = self._font(20).render(
            f"本局分数 {snapshot.score}    最高 {snapshot.best}", True, TEXT_DARK
        )
        screen.blit(detail, detail.get_rect(center=(card.centerx, card.y + 110)))

        if snapshot.state is GameState.WIN:
            self._draw_button(screen, theme.OVERLAY_BTN_LEFT, "继续挑战")
            self._draw_button(screen, theme.OVERLAY_BTN_RIGHT, "重新开始")
        elif can_record:
            self._draw_button(screen, theme.OVERLAY_BTN_LEFT, "登记成绩", theme.CONFIRM_OK_COLOR)
            self._draw_button(screen, theme.OVERLAY_BTN_RIGHT, "再来一局")
        else:
            self._draw_button(screen, theme.OVERLAY_BTN_SINGLE, "再来一局")
            tip = self._font(16).render("按 R 可直接重开", True, TEXT_DARK)
            screen.blit(tip, tip.get_rect(center=(card.centerx, card.y + 260)))

    def _draw_button(
        self,
        screen: pygame.Surface,
        rect_xywh: tuple[int, int, int, int],
        label: str,
        color: tuple[int, int, int] = theme.BUTTON_COLOR,
    ) -> None:
        rect = pygame.Rect(rect_xywh)
        pygame.draw.rect(screen, color, rect, border_radius=8)
        text = self._font(22).render(label, True, TEXT_LIGHT)
        screen.blit(text, text.get_rect(center=rect.center))

    # —— 确认弹窗（重新开始 / 退出共用同一套布局） ——
    def draw_dialog(self, screen: pygame.Surface, dialog: str) -> None:
        if dialog == "restart":
            self._draw_dialog(
                screen, "重新开始？", "当前进度会丢失，确定要重开吗？", "重新开始"
            )
        elif dialog == "exit":
            self._draw_dialog(screen, "退出游戏？", "当前进度会丢失，最高分会保留", "退出游戏")

    def _draw_dialog(
        self,
        screen: pygame.Surface,
        title_text: str,
        detail_text: str,
        ok_label: str,
    ) -> None:
        veil = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        veil.fill((250, 248, 239, 180))
        screen.blit(veil, (0, 0))

        card = pygame.Rect(theme.CONFIRM_CARD)
        pygame.draw.rect(screen, (255, 255, 255), card, border_radius=16)

        title = self._font(28).render(title_text, True, TEXT_DARK)
        screen.blit(title, title.get_rect(center=(card.centerx, card.y + 50)))
        detail = self._font(18).render(detail_text, True, TEXT_DARK)
        screen.blit(detail, detail.get_rect(center=(card.centerx, card.y + 94)))

        self._draw_button(screen, theme.CONFIRM_CANCEL_BTN, "取消")
        self._draw_button(screen, theme.CONFIRM_OK_BTN, ok_label, theme.CONFIRM_OK_COLOR)

    # —— 主菜单 ——
    def draw_menu(self, screen: pygame.Surface, best: int) -> None:
        screen.fill(BG_COLOR)
        title = self._font(96).render(APP_NAME, True, TEXT_DARK)
        screen.blit(title, title.get_rect(center=(WINDOW_W // 2, 170)))
        sub = self._font(20).render("合并方块，挑战 2048", True, TEXT_DARK)
        screen.blit(sub, sub.get_rect(center=(WINDOW_W // 2, 248)))

        self._draw_button(screen, theme.MENU_BTN_START, "开始游戏", theme.CONFIRM_OK_COLOR)
        self._draw_button(screen, theme.MENU_BTN_SETTINGS, "设置")
        self._draw_button(screen, theme.MENU_BTN_RANKING, "排行榜")
        self._draw_button(screen, theme.MENU_BTN_EXIT, "退出")

        best_text = self._font(18).render(f"最高分 {best}", True, TEXT_DARK)
        screen.blit(best_text, best_text.get_rect(center=(WINDOW_W // 2, 620)))
        hint = self._font(16).render("ESC 退出    F11 切换全屏", True, TEXT_DARK)
        screen.blit(hint, hint.get_rect(center=(WINDOW_W // 2, 690)))

    @staticmethod
    def hit_menu(pos: tuple[int, int]) -> str | None:
        for rect, key in (
            (theme.MENU_BTN_START, "start"),
            (theme.MENU_BTN_SETTINGS, "settings"),
            (theme.MENU_BTN_RANKING, "leaderboard"),
            (theme.MENU_BTN_EXIT, "exit"),
        ):
            if pygame.Rect(rect).collidepoint(pos):
                return key
        return None

    # —— 设置 ——
    def draw_settings(self, screen: pygame.Surface, fullscreen: bool) -> None:
        screen.fill(BG_COLOR)
        title = self._font(44).render("设置", True, TEXT_DARK)
        screen.blit(title, title.get_rect(center=(WINDOW_W // 2, 120)))
        label = self._font(22).render("显示模式", True, TEXT_DARK)
        screen.blit(label, label.get_rect(center=(WINDOW_W // 2, 250)))

        for rect, text, active in (
            (theme.SET_WINDOW_BTN, "窗口", not fullscreen),
            (theme.SET_FULLSCREEN_BTN, "全屏", fullscreen),
        ):
            box = pygame.Rect(rect)
            color = theme.CONFIRM_OK_COLOR if active else theme.BUTTON_COLOR
            pygame.draw.rect(screen, color, box, border_radius=8)
            text_surf = self._font(24).render(text, True, TEXT_LIGHT)
            screen.blit(text_surf, text_surf.get_rect(center=box.center))
            if active:
                pygame.draw.circle(screen, TEXT_LIGHT, (box.x + 26, box.centery), 6)

        tip = self._font(16).render("设置会自动保存，下次启动沿用", True, TEXT_DARK)
        screen.blit(tip, tip.get_rect(center=(WINDOW_W // 2, 500)))
        self._draw_button(screen, theme.BACK_BTN, "返回")
        hint = self._font(16).render("F11 可随时切换全屏", True, TEXT_DARK)
        screen.blit(hint, hint.get_rect(center=(380, 667)))

    @staticmethod
    def hit_settings(pos: tuple[int, int]) -> str | None:
        if pygame.Rect(theme.SET_WINDOW_BTN).collidepoint(pos):
            return "window"
        if pygame.Rect(theme.SET_FULLSCREEN_BTN).collidepoint(pos):
            return "fullscreen"
        if pygame.Rect(theme.BACK_BTN).collidepoint(pos):
            return "back"
        return None

    # —— 排行榜 ——
    def draw_leaderboard(self, screen: pygame.Surface, records: "list[Record]") -> None:
        screen.fill(BG_COLOR)
        title = self._font(44).render("排行榜", True, TEXT_DARK)
        screen.blit(title, title.get_rect(center=(WINDOW_W // 2, 92)))
        sub = self._font(16).render("历史最高分前 10 名", True, TEXT_DARK)
        screen.blit(sub, sub.get_rect(center=(WINDOW_W // 2, 136)))

        card = pygame.Rect(theme.RANK_CARD)
        pygame.draw.rect(screen, (255, 255, 255), card, border_radius=12)

        if not records:
            empty = self._font(20).render("暂无记录，快去挑战吧", True, TEXT_DARK)
            screen.blit(empty, empty.get_rect(center=card.center))
        else:
            head = self._font(15)
            screen.blit(head.render("名次", True, TEXT_DARK), (card.x + 34, card.y + 20))
            screen.blit(head.render("昵称", True, TEXT_DARK), (card.x + 96, card.y + 20))
            score_head = head.render("分数", True, TEXT_DARK)
            screen.blit(score_head, score_head.get_rect(topright=(card.right - 30, card.y + 20)))
            pygame.draw.line(
                screen, theme.EMPTY_ACCENT,
                (card.x + 24, card.y + 48), (card.right - 24, card.y + 48), 1,
            )
            for index, record in enumerate(records[:10], start=1):
                y = card.y + 74 + (index - 1) * 33
                rank = self._font(17).render(str(index), True, TEXT_DARK)
                screen.blit(rank, rank.get_rect(midleft=(card.x + 40, y)))
                name = self._font(16).render(record.name, True, TEXT_DARK)
                screen.blit(name, name.get_rect(midleft=(card.x + 96, y)))
                score = self._font(17).render(str(record.score), True, TEXT_DARK)
                screen.blit(score, score.get_rect(midright=(card.right - 30, y)))

        self._draw_button(screen, theme.BACK_BTN, "返回")

    @staticmethod
    def hit_back(pos: tuple[int, int]) -> bool:
        return pygame.Rect(theme.BACK_BTN).collidepoint(pos)

    @staticmethod
    def hit_record(pos: tuple[int, int]) -> bool:
        """结束浮层左侧「登记成绩」按钮。"""
        return pygame.Rect(theme.OVERLAY_BTN_LEFT).collidepoint(pos)

    # —— 昵称输入 ——
    def draw_name_entry(self, screen: pygame.Surface, score: int, name: str) -> None:
        screen.fill(BG_COLOR)
        title = self._font(44).render("新纪录！", True, TEXT_DARK)
        screen.blit(title, title.get_rect(center=(WINDOW_W // 2, 150)))
        sub = self._font(20).render(f"本局得分 {score}，可以进入前 10 名", True, TEXT_DARK)
        screen.blit(sub, sub.get_rect(center=(WINDOW_W // 2, 220)))

        label = self._font(18).render("昵称", True, TEXT_DARK)
        screen.blit(label, label.get_rect(midleft=(130, 330)))

        box = pygame.Rect(theme.NAME_INPUT_BOX)
        pygame.draw.rect(screen, (255, 255, 255), box, border_radius=8)
        pygame.draw.rect(screen, theme.BUTTON_COLOR, box, width=2, border_radius=8)
        shown = name if name else "输入昵称"
        color = TEXT_DARK if name else (176, 166, 156)
        text_surf = self._font(22).render(shown, True, color)
        screen.blit(text_surf, text_surf.get_rect(midleft=(box.x + 14, box.centery)))

        hint = self._font(16).render("Enter 保存    ESC 跳过", True, TEXT_DARK)
        screen.blit(hint, hint.get_rect(center=(WINDOW_W // 2, 446)))
        tip = self._font(14).render(f"支持中英文与数字，最多 {MAX_NAME_LEN} 个字符", True, TEXT_DARK)
        screen.blit(tip, tip.get_rect(center=(WINDOW_W // 2, 476)))

    # —— 点击检测 ——
    @staticmethod
    def hit_dialog(pos: tuple[int, int]) -> str | None:
        """确认弹窗热点：'confirm' / 'cancel'；点空白返回 None（等同取消）。"""
        if pygame.Rect(theme.CONFIRM_OK_BTN).collidepoint(pos):
            return "confirm"
        if pygame.Rect(theme.CONFIRM_CANCEL_BTN).collidepoint(pos):
            return "cancel"
        return None

    @staticmethod
    def hit_test(pos: tuple[int, int], state: GameState) -> Action | None:
        """返回被点击按钮对应的动作；未命中任何热点返回 None。"""
        if state is GameState.RUNNING:
            return Action.RESTART if pygame.Rect(theme.NEW_GAME_BTN).collidepoint(pos) else None

        if state is GameState.WIN:
            if pygame.Rect(theme.OVERLAY_BTN_LEFT).collidepoint(pos):
                return Action.CONTINUE
            if pygame.Rect(theme.OVERLAY_BTN_RIGHT).collidepoint(pos):
                return Action.RESTART
            return None

        return Action.RESTART if pygame.Rect(theme.OVERLAY_BTN_SINGLE).collidepoint(pos) else None
