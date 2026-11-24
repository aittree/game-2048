"""程序入口：主菜单、游戏、设置、排行榜、昵称输入的状态机与主循环。

输入策略：动画期间方向键只缓冲最近 1 手，动画播完再执行，保证每一手动画完整。
退出策略：点 × / Alt+F4 / ESC 都先弹确认框；本局分数进前 10 时可先登记昵称。
"""

from __future__ import annotations

import ctypes
import os
import traceback
from pathlib import Path

import pygame

from src import config, storage
from src.game import Action, Game, GameState
from src.resource import resource_path
from src.ui.animator import Animator
from src.ui.renderer import Renderer

KEY_MAP = {
    pygame.K_LEFT: Action.LEFT,
    pygame.K_a: Action.LEFT,
    pygame.K_RIGHT: Action.RIGHT,
    pygame.K_d: Action.RIGHT,
    pygame.K_UP: Action.UP,
    pygame.K_w: Action.UP,
    pygame.K_DOWN: Action.DOWN,
    pygame.K_s: Action.DOWN,
    pygame.K_r: Action.RESTART,
    pygame.K_u: Action.UNDO,
}

_DIRECTION_ACTIONS = {Action.LEFT, Action.RIGHT, Action.UP, Action.DOWN}
_DIALOG_CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_y)

SCREEN_MENU = "menu"
SCREEN_GAME = "game"
SCREEN_SETTINGS = "settings"
SCREEN_RANKING = "ranking"
SCREEN_ENTRY = "entry"
SCREEN_ENTRY_EXIT = "entry_exit"    # 登记完成后直接退出


def enable_dpi_awareness() -> None:
    """高分屏下避免窗口发虚；失败不影响运行（docs/06 §6.5）。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)      # Win8.1+
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()       # Win7 兜底
        except (AttributeError, OSError):
            pass


def center_window() -> None:
    """把窗口摆到屏幕中央（FR-01）；拿不到句柄时保留系统默认位置。"""
    try:
        info = pygame.display.Info()
        hwnd = pygame.display.get_wm_info().get("window")
        if not hwnd:
            return
        x = max(0, (info.current_w - config.WINDOW_W) // 2)
        y = max(0, (info.current_h - config.WINDOW_H) // 2)
        swp_nosize, swp_nozorder = 0x0001, 0x0004
        ctypes.windll.user32.SetWindowPos(
            hwnd, 0, x, y, 0, 0, swp_nosize | swp_nozorder
        )
    except (AttributeError, OSError, pygame.error):
        pass


class Display:
    """固定 560x720 逻辑画布的显示层。

    全屏不依赖 SDL 的 SCALED 渲染器（部分环境创建失败），而是把画布等比缩放到
    桌面分辨率并居中，四周留黑边；鼠标坐标再反算回画布坐标。
    """

    def __init__(self, fullscreen: bool) -> None:
        self.canvas = pygame.Surface((config.WINDOW_W, config.WINDOW_H))
        self.screen: pygame.Surface
        self.fullscreen: bool
        self.scale: float
        self.offset: tuple[int, int]
        self._scaled_size: tuple[int, int]
        self.apply(fullscreen)

    def apply(self, fullscreen: bool) -> None:
        self.fullscreen = fullscreen
        if fullscreen:
            # (0, 0) 让 SDL 直接采用当前桌面分辨率；不请求具体尺寸，避免触发分辨率切换
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            width, height = self.screen.get_size()
            self.scale = min(width / config.WINDOW_W, height / config.WINDOW_H)
            self._scaled_size = (int(config.WINDOW_W * self.scale), int(config.WINDOW_H * self.scale))
            self.offset = (
                (width - self._scaled_size[0]) // 2,
                (height - self._scaled_size[1]) // 2,
            )
        else:
            self.screen = pygame.display.set_mode((config.WINDOW_W, config.WINDOW_H))
            self.scale = 1.0
            self._scaled_size = (config.WINDOW_W, config.WINDOW_H)
            self.offset = (0, 0)
            center_window()

    def present(self) -> None:
        """把画布贴到窗口：窗口模式 1:1，全屏模式等比缩放居中。"""
        if not self.fullscreen:
            self.screen.blit(self.canvas, (0, 0))
        else:
            self.screen.fill((0, 0, 0))
            self.screen.blit(
                pygame.transform.smoothscale(self.canvas, self._scaled_size), self.offset
            )
        pygame.display.flip()

    def to_canvas(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        """把屏幕坐标反算回 560x720 画布坐标；点在黑边上返回 None。"""
        x = (pos[0] - self.offset[0]) / self.scale
        y = (pos[1] - self.offset[1]) / self.scale
        if 0 <= x < config.WINDOW_W and 0 <= y < config.WINDOW_H:
            return int(x), int(y)
        return None

    def canvas_rect_to_screen(self, rect: pygame.Rect) -> pygame.Rect:
        """把画布矩形换算成窗口坐标，供输入法候选框定位。"""
        return pygame.Rect(
            self.offset[0] + int(rect.x * self.scale),
            self.offset[1] + int(rect.y * self.scale),
            int(rect.width * self.scale),
            int(rect.height * self.scale),
        )


def _dispatch(game: Game, animator: Animator, action: Action) -> None:
    """把抽象动作交给状态机；只有本手真的执行且发生了移动才播动画。"""
    previous = game.last_result
    if action not in _DIRECTION_ACTIONS:
        animator.stop()
    game.handle_action(action)
    result = game.last_result
    if action in _DIRECTION_ACTIONS and result is not previous and result.changed:
        animator.start(result, game.last_new_tile)


def _run() -> None:
    enable_dpi_awareness()
    pygame.init()
    pygame.display.set_caption(config.APP_NAME)
    try:
        pygame.display.set_icon(pygame.image.load(resource_path("assets", "icon.png")))
    except (pygame.error, FileNotFoundError):
        pass                                    # 图标缺失不阻断启动

    profile = storage.load_profile()
    display = Display(profile.fullscreen)
    clock = pygame.time.Clock()
    pygame.key.set_repeat(120, 60)              # 长按 120ms 后每 60ms 重复

    game = Game(best=profile.best)
    renderer = Renderer(resource_path("assets", "fonts", "msyh.ttc"))
    animator = Animator()

    screen_name = SCREEN_MENU
    dialog: str | None = None                   # None / "restart" / "exit"
    pending: Action | None = None               # 动画期间缓冲的最近一手
    recorded = False                            # 本局是否已登记成绩
    name_text = ""
    preedit = ""                                # 输入法未上屏的预编辑文本
    entry_score = 0

    def persist() -> None:
        profile.best = max(profile.best, game.best)
        storage.save_profile(profile)

    def dispatch(act: Action) -> None:
        nonlocal recorded
        _dispatch(game, animator, act)
        if act is Action.RESTART:
            recorded = False

    def can_record() -> bool:
        return not recorded and storage.qualifies(profile, game.score)

    def sync_text_input_rect() -> None:
        """把输入法候选框定位到昵称输入框（窗口坐标）。"""
        pygame.key.set_text_input_rect(
            display.canvas_rect_to_screen(Renderer.name_input_rect())
        )

    def apply_fullscreen(value: bool) -> None:
        profile.fullscreen = value
        persist()
        display.apply(value)
        if screen_name in (SCREEN_ENTRY, SCREEN_ENTRY_EXIT):
            sync_text_input_rect()              # 全屏切换后候选框位置随画布缩放

    def open_entry(then_exit: bool) -> None:
        nonlocal dialog, screen_name, name_text, entry_score, preedit
        dialog = None
        entry_score = game.score
        name_text = ""
        preedit = ""
        screen_name = SCREEN_ENTRY_EXIT if then_exit else SCREEN_ENTRY
        pygame.key.start_text_input()
        sync_text_input_rect()

    def leave_entry(save: bool) -> bool:
        """离开昵称输入；返回 True 表示主循环应结束。"""
        nonlocal screen_name, recorded, preedit
        pygame.key.stop_text_input()
        preedit = ""
        exiting = screen_name == SCREEN_ENTRY_EXIT
        if save:
            name = name_text.strip() or "匿名"
            if storage.insert_record(profile, name, entry_score) is not None:
                recorded = True
            persist()
        if exiting:
            persist()
            return True
        screen_name = SCREEN_RANKING if save else SCREEN_GAME
        return False

    def confirm_dialog() -> bool:
        """执行弹窗确认；返回 True 表示退出程序。"""
        nonlocal dialog, pending
        if dialog == "restart":
            dialog = None
            pending = None
            dispatch(Action.RESTART)
            return False
        dialog = None
        if screen_name == SCREEN_GAME and can_record():
            open_entry(then_exit=True)
            return False
        persist()
        return True

    running = True
    while running:
        dt = clock.tick(config.FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:       # 点 × 或 Alt+F4：先确认再退出
                dialog = "exit"
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                apply_fullscreen(not display.fullscreen)
                continue
            if event.type == pygame.TEXTEDITING and screen_name in (SCREEN_ENTRY, SCREEN_ENTRY_EXIT):
                preedit = event.text             # 输入法预编辑：随打字实时显示在输入框
                continue
            if event.type == pygame.TEXTINPUT and screen_name in (SCREEN_ENTRY, SCREEN_ENTRY_EXIT):
                name_text = (name_text + event.text)[: config.MAX_NAME_LEN]
                preedit = ""
                continue

            # 确认弹窗是模态的，优先处理
            if dialog is not None:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        dialog = None
                    elif event.key in _DIALOG_CONFIRM_KEYS or (
                        dialog == "restart" and event.key == pygame.K_r
                    ):
                        running = not confirm_dialog()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = display.to_canvas(event.pos)
                    if pos is None:
                        continue
                    if Renderer.hit_dialog(pos) == "confirm":
                        running = not confirm_dialog()
                    else:
                        dialog = None           # 「取消」或点空白都关闭弹窗
                continue

            if screen_name == SCREEN_MENU:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    dialog = "exit"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = display.to_canvas(event.pos)
                    if pos is None:
                        continue
                    choice = Renderer.hit_menu(pos)
                    if choice == "start":
                        game.reset()
                        recorded = False
                        animator.stop()
                        pending = None
                        screen_name = SCREEN_GAME
                    elif choice == "settings":
                        screen_name = SCREEN_SETTINGS
                    elif choice == "leaderboard":
                        screen_name = SCREEN_RANKING
                    elif choice == "exit":
                        dialog = "exit"
            elif screen_name == SCREEN_SETTINGS:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    screen_name = SCREEN_MENU
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = display.to_canvas(event.pos)
                    if pos is None:
                        continue
                    choice = Renderer.hit_settings(pos)
                    if choice == "back":
                        screen_name = SCREEN_MENU
                    elif choice == "window" and display.fullscreen:
                        apply_fullscreen(False)
                    elif choice == "fullscreen" and not display.fullscreen:
                        apply_fullscreen(True)
            elif screen_name == SCREEN_RANKING:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    screen_name = SCREEN_MENU
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = display.to_canvas(event.pos)
                    if pos is not None and Renderer.hit_back(pos):
                        screen_name = SCREEN_MENU
            elif screen_name in (SCREEN_ENTRY, SCREEN_ENTRY_EXIT):
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = not leave_entry(save=False)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        running = not leave_entry(save=True)
                    elif event.key == pygame.K_BACKSPACE:
                        name_text = name_text[:-1]
            else:                                # SCREEN_GAME
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        dialog = "exit"
                        continue
                    action = KEY_MAP.get(event.key)
                    if action is None:
                        continue
                    if action in _DIRECTION_ACTIONS and animator.active:
                        pending = action        # 动画未播完：只留最近一手，不打断动画
                        continue
                    pending = None
                    dispatch(action)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = display.to_canvas(event.pos)
                    if pos is None:
                        continue
                    if animator.active and game.state is not GameState.RUNNING:
                        continue                # 浮层还没出现，先不响应点击
                    if (
                        game.state is GameState.GAME_OVER
                        and can_record()
                        and Renderer.hit_record(pos)
                    ):
                        open_entry(then_exit=False)
                        continue
                    action = Renderer.hit_test(pos, game.state)
                    if action is Action.RESTART and game.state is GameState.RUNNING:
                        dialog = "restart"      # 「新游戏」先二次确认，避免误触丢进度
                        pending = None
                        continue
                    pending = None
                    if action is not None:
                        dispatch(action)

        if screen_name == SCREEN_GAME:
            animator.update(dt)
            if not animator.active and pending is not None:
                action, pending = pending, None  # 动画播完后补执行缓冲的一手
                dispatch(action)

        if screen_name == SCREEN_MENU:
            renderer.draw_menu(display.canvas, max(profile.best, game.best))
        elif screen_name == SCREEN_SETTINGS:
            renderer.draw_settings(display.canvas, display.fullscreen)
        elif screen_name == SCREEN_RANKING:
            renderer.draw_leaderboard(display.canvas, profile.leaderboard)
        elif screen_name in (SCREEN_ENTRY, SCREEN_ENTRY_EXIT):
            renderer.draw_name_entry(display.canvas, entry_score, name_text, preedit)
        else:
            show_record = game.state is GameState.GAME_OVER and can_record()
            renderer.draw(display.canvas, game.snapshot(), animator, can_record=show_record)
        if dialog is not None:
            renderer.draw_dialog(display.canvas, dialog)
        display.present()

    persist()
    pygame.quit()


def main() -> None:
    try:
        _run()
    except Exception:
        # -w 打包后没有控制台，把堆栈落到 AppData，便于远程定位（docs/06 §6.6）
        crash_log = Path(os.environ.get("APPDATA") or Path.home()) / config.APP_ID / "crash.log"
        crash_log.parent.mkdir(parents=True, exist_ok=True)
        crash_log.write_text(traceback.format_exc(), encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
