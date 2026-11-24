"""游戏状态机：分数、最高分、运行／通关／结束状态。

应用层，禁止 import pygame，只接收抽象 Action（docs/02 §2）。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from . import storage
from .board import Board, Direction, MoveResult
from .config import WIN_VALUE


class GameState(Enum):
    RUNNING = auto()
    WIN = auto()
    GAME_OVER = auto()


class Action(Enum):
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
    RESTART = auto()
    UNDO = auto()
    CONTINUE = auto()


@dataclass(frozen=True)
class GameSnapshot:
    """供渲染层消费的只读结构，grid 必须是深拷贝。"""

    grid: list
    score: int
    best: int
    state: GameState
    last_gain: int


_DIRECTIONS = {
    Action.LEFT: Direction.LEFT,
    Action.RIGHT: Direction.RIGHT,
    Action.UP: Direction.UP,
    Action.DOWN: Direction.DOWN,
}


class Game:
    """一局游戏的完整状态与对外唯一入口。"""

    def __init__(self, best: int = 0) -> None:
        self.board = Board()
        self.score = 0
        self.best = best
        self.state = GameState.RUNNING
        self.win_shown = False          # 通关提示只弹一次
        self._undo_stack: list[tuple[list[list[int]], int]] = []   # 只保留最近 1 步
        self.last_result: MoveResult | None = None
        self.last_new_tile: tuple[int, int] | None = None
        self.reset()                    # 构造即开局

    # —— 生命周期 ——
    def reset(self) -> None:
        self.board.reset()
        self.score = 0
        self.state = GameState.RUNNING
        self.win_shown = False
        self._undo_stack.clear()
        self.last_result = None
        self.last_new_tile = None

    # —— 对外唯一入口 ——
    def handle_action(self, action: Action) -> None:
        if action is Action.RESTART:
            self.reset()
            return
        if action is Action.UNDO:
            self.undo()
            return
        if action is Action.CONTINUE:
            if self.state is GameState.WIN:
                self.state = GameState.RUNNING
            return
        if self.state is not GameState.RUNNING:
            return                      # WIN / GAME_OVER 期间忽略方向键

        direction = _DIRECTIONS.get(action)
        if direction is not None:
            self._play(direction)

    # —— 核心一步 ——
    def _play(self, direction: Direction) -> None:
        snapshot = (self.board.clone().grid, self.score)
        result = self.board.move(direction)
        self.last_result = result
        if not result.changed:
            self.last_new_tile = None
            return                      # 无效移动：不生成、不加分、不入撤销栈

        self._undo_stack.append(snapshot)
        self._undo_stack = self._undo_stack[-1:]

        self.score += result.gained
        self.best = max(self.best, self.score)
        self.last_new_tile = self.board.spawn()

        if self.board.has_value(WIN_VALUE) and not self.win_shown:
            self.win_shown = True
            self.state = GameState.WIN
        elif self.board.is_game_over():
            self.state = GameState.GAME_OVER
            storage.save_best(self.best)

    def undo(self) -> None:
        # 撤销仅在 RUNNING 状态可用：WIN 浮层与 GAME_OVER 下不允许回退棋盘
        if not self._undo_stack or self.state is not GameState.RUNNING:
            return
        grid, score = self._undo_stack.pop()
        self.board.grid = [row[:] for row in grid]
        self.score = score
        self.last_result = None
        self.last_new_tile = None

    def snapshot(self) -> GameSnapshot:
        """导出只读快照；grid 必须深拷贝，避免渲染层意外改到模型。"""
        return GameSnapshot(
            grid=[row[:] for row in self.board.grid],
            score=self.score,
            best=self.best,
            state=self.state,
            last_gain=self.last_result.gained if self.last_result else 0,
        )
