"""棋盘模型：4×4 网格、四方向移动合并、随机生成与胜负判定。

纯逻辑层，禁止 import pygame，可在无图形环境下用 pytest 覆盖。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import IntEnum

from .config import GRID_SIZE, SPAWN_4_PROB


class Direction(IntEnum):
    """移动方向。"""

    LEFT, RIGHT, UP, DOWN = 0, 1, 2, 3


@dataclass
class MoveResult:
    """一次移动的结算结果，同时供表现层做动画插值。"""

    changed: bool = False                               # 是否有效移动
    gained: int = 0                                     # 本次得分
    slides: list[tuple[int, tuple[int, int], tuple[int, int]]] = field(default_factory=list)
    merges: list[tuple[int, int, int]] = field(default_factory=list)
    merged_from: list[tuple[int, int]] = field(default_factory=list)


def _merge_line(values: list[int]) -> tuple[list[int], int, list[tuple[int, ...]]]:
    """把一行向左合并。

    values: 长度为 4 的一行，按「移动方向前端在前」排列
    返回: (合并后的行, 本行得分, 每个输出格的来源索引组)
    """
    nz = [i for i, v in enumerate(values) if v != 0]   # 非零元素的原始索引
    out: list[int] = []
    groups: list[tuple[int, ...]] = []
    gained = 0
    k = 0
    while k < len(nz):
        i = nz[k]
        if k + 1 < len(nz) and values[i] == values[nz[k + 1]]:
            j = nz[k + 1]
            merged = values[i] * 2
            out.append(merged)
            groups.append((i, j))
            gained += merged
            k += 2                        # 跳过已被合并的那一块
        else:
            out.append(values[i])
            groups.append((i,))
            k += 1
    while len(out) < len(values):         # 补 0 到满行
        out.append(0)
        groups.append(())
    return out, gained, groups


class Board:
    """4×4 棋盘。0 表示空格。"""

    def __init__(self, grid: list[list[int]] | None = None) -> None:
        self.grid = grid if grid is not None else [[0] * GRID_SIZE for _ in range(GRID_SIZE)]

    # —— 查询 ——
    def clone(self) -> "Board":
        """深拷贝棋盘，用于撤销快照与只读导出。"""
        return Board([row[:] for row in self.grid])

    def max_tile(self) -> int:
        return max(v for row in self.grid for v in row)

    def has_value(self, value: int) -> bool:
        return any(v == value for row in self.grid for v in row)

    def is_game_over(self) -> bool:
        """满盘且横纵方向都不存在相邻等值方块即为死局。

        相邻关系对称，只需比较右邻与下邻，无需重复检查四个方向。
        """
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                v = self.grid[r][c]
                if v == 0:
                    return False
                if c + 1 < GRID_SIZE and self.grid[r][c + 1] == v:
                    return False
                if r + 1 < GRID_SIZE and self.grid[r + 1][c] == v:
                    return False
        return True

    # —— 变更 ——
    def reset(self) -> None:
        """清空棋盘并生成两个初始方块。"""
        self.grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.spawn()
        self.spawn()

    def spawn(self) -> tuple[int, int] | None:
        """在随机空格生成 2（90%）或 4（10%）；无空格时返回 None。"""
        empties = [
            (r, c)
            for r in range(GRID_SIZE)
            for c in range(GRID_SIZE)
            if self.grid[r][c] == 0
        ]
        if not empties:
            return None
        r, c = random.choice(empties)
        self.grid[r][c] = 4 if random.random() < SPAWN_4_PROB else 2
        return r, c

    @staticmethod
    def _lines(direction: Direction) -> list[list[tuple[int, int]]]:
        """按移动方向拆成 4 条线，每条线首个元素最靠近目标边界。"""
        s = GRID_SIZE
        if direction == Direction.LEFT:
            return [[(r, c) for c in range(s)] for r in range(s)]
        if direction == Direction.RIGHT:
            return [[(r, c) for c in range(s - 1, -1, -1)] for r in range(s)]
        if direction == Direction.UP:
            return [[(r, c) for r in range(s)] for c in range(s)]
        return [[(r, c) for r in range(s - 1, -1, -1)] for c in range(s)]

    def move(self, direction: Direction) -> MoveResult:
        """一次性算完整个移动，返回结算结果；无效移动不修改棋盘。"""
        result = MoveResult()
        new_grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]

        for line in self._lines(direction):
            values = [self.grid[r][c] for r, c in line]
            if not any(values):
                continue
            out, gained, groups = _merge_line(values)
            result.gained += gained

            for k, srcs in enumerate(groups):
                if not srcs:
                    continue
                tr, tc = line[k]
                new_grid[tr][tc] = out[k]
                for gi in srcs:                    # 位移记录（供动画使用）
                    sr, sc = line[gi]
                    result.slides.append((values[gi], (sr, sc), (tr, tc)))
                if len(srcs) > 1:                  # 发生合并
                    result.merges.append((tr, tc, out[k]))
                    result.merged_from.append(line[srcs[1]])

        result.changed = new_grid != self.grid
        if result.changed:
            self.grid = new_grid
        return result

    def dump(self) -> str:
        """只读文本视图，便于调试对照。"""
        return "\n".join(
            " ".join(f"{v:4d}" if v else "   ." for v in row) for row in self.grid
        )
