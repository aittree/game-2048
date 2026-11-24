"""程序入口：初始化 pygame 与窗口，创建 Game / Renderer / Animator，驱动主循环。

输入策略：动画期间方向键只缓冲最近 1 手，动画播完再执行，保证每一手动画完整。
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

    screen = pygame.display.set_mode((config.WINDOW_W, config.WINDOW_H))
    center_window()
    clock = pygame.time.Clock()
    pygame.key.set_repeat(120, 60)              # 长按 120ms 后每 60ms 重复

    game = Game(best=storage.load_best())
    renderer = Renderer(resource_path("assets", "fonts", "msyh.ttc"))
    animator = Animator()
    pending: Action | None = None               # 动画期间缓冲的最近一手
    confirm_restart = False                     # 「新游戏」二次确认弹窗

    running = True
    while running:
        dt = clock.tick(config.FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # ESC 不退出程序；确认弹窗下取消，通关浮层下等价于「继续挑战」
                    if confirm_restart:
                        confirm_restart = False
                    elif game.state is GameState.WIN:
                        pending = None
                        _dispatch(game, animator, Action.CONTINUE)
                    continue
                if confirm_restart:
                    if event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_y):
                        confirm_restart = False
                        pending = None
                        _dispatch(game, animator, Action.RESTART)
                    continue                    # 弹窗期间其余按键忽略
                action = KEY_MAP.get(event.key)
                if action is None:
                    continue
                if action in _DIRECTION_ACTIONS and animator.active:
                    pending = action            # 动画未播完：只留最近一手，不打断动画
                    continue
                pending = None
                _dispatch(game, animator, action)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if confirm_restart:
                    if Renderer.hit_confirm(event.pos) == "confirm":
                        confirm_restart = False
                        pending = None
                        _dispatch(game, animator, Action.RESTART)
                    else:
                        confirm_restart = False     # 「取消」或点空白都关闭弹窗
                    continue
                if animator.active and game.state is not GameState.RUNNING:
                    continue                    # 浮层还没出现，先不响应点击
                action = Renderer.hit_test(event.pos, game.state)
                if action is Action.RESTART and game.state is GameState.RUNNING:
                    confirm_restart = True      # 「新游戏」先二次确认，避免误触丢进度
                    pending = None
                    continue
                pending = None
                if action is not None:
                    _dispatch(game, animator, action)

        animator.update(dt)
        if not animator.active and pending is not None:
            action, pending = pending, None     # 动画播完后补执行缓冲的一手
            _dispatch(game, animator, action)

        renderer.draw(screen, game.snapshot(), animator, confirm_restart)
        pygame.display.flip()

    storage.save_best(game.best)                # 退出前落盘
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
