"""程序入口：初始化 pygame 与窗口，创建 Game / Renderer / Animator，驱动主循环。"""

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


def _dispatch(game: Game, animator: Animator, action: Action) -> None:
    """把抽象动作交给状态机；只有方向键且确实发生移动时才播动画。"""
    if action not in _DIRECTION_ACTIONS:
        animator.stop()
    game.handle_action(action)
    if action in _DIRECTION_ACTIONS and game.last_result is not None and game.last_result.changed:
        animator.start(game.last_result, game.last_new_tile)


def _run() -> None:
    enable_dpi_awareness()
    pygame.init()
    pygame.display.set_caption(config.APP_NAME)
    try:
        pygame.display.set_icon(pygame.image.load(resource_path("assets", "icon.png")))
    except (pygame.error, FileNotFoundError):
        pass                                    # 图标缺失不阻断启动

    screen = pygame.display.set_mode((config.WINDOW_W, config.WINDOW_H))
    clock = pygame.time.Clock()
    pygame.key.set_repeat(120, 60)              # 长按 120ms 后每 60ms 重复

    game = Game(best=storage.load_best())
    renderer = Renderer(resource_path("assets", "fonts", "msyh.ttc"))
    animator = Animator()

    running = True
    while running:
        dt = clock.tick(config.FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # ESC 不退出程序，仅在通关浮层下等价于「继续挑战」
                    if game.state is GameState.WIN:
                        _dispatch(game, animator, Action.CONTINUE)
                    continue
                action = KEY_MAP.get(event.key)
                if action is not None:
                    _dispatch(game, animator, action)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = Renderer.hit_test(event.pos, game.state)
                if action is not None:
                    _dispatch(game, animator, action)

        animator.update(dt)
        renderer.draw(screen, game.snapshot(), animator)
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
