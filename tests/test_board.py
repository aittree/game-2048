"""棋盘模型单元测试（docs/05 §2.5），不依赖 pygame。"""

import random

import pytest

# noinspection PyProtectedMember
from src.board import Board, Direction, _merge_line


def make_board(grid):
    return Board([row[:] for row in grid])


@pytest.mark.parametrize("line, expected, gain", [
    ([2, 2, 2, 2], [4, 4, 0, 0], 8),
    ([2, 2, 2, 0], [4, 2, 0, 0], 4),
    ([0, 2, 2, 2], [4, 2, 0, 0], 4),
    ([4, 4, 8, 8], [8, 16, 0, 0], 24),
    ([2, 0, 2, 0], [4, 0, 0, 0], 4),
    ([4, 0, 0, 4], [8, 0, 0, 0], 8),
    ([2, 4, 2, 4], [2, 4, 2, 4], 0),
    ([0, 0, 0, 2], [2, 0, 0, 0], 0),
    ([0, 0, 0, 0], [0, 0, 0, 0], 0),
    ([1024, 1024, 0, 0], [2048, 0, 0, 0], 2048),
])
def test_merge_line(line, expected, gain):
    out, gained, _ = _merge_line(line)
    assert out == expected
    assert gained == gain


@pytest.mark.parametrize("direction, expected", [
    (Direction.LEFT, [4, 8, 0, 0]),
    (Direction.RIGHT, [0, 0, 4, 8]),
])
def test_move_horizontal(direction, expected):
    grid = [[2, 2, 4, 4], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    b = make_board(grid)
    r = b.move(direction)
    assert b.grid[0] == expected
    assert r.gained == 12
    assert r.changed is True


@pytest.mark.parametrize("direction, expected_col", [
    (Direction.UP, [4, 8, 0, 0]),
    (Direction.DOWN, [0, 0, 4, 8]),
])
def test_move_vertical(direction, expected_col):
    grid = [[2, 0, 0, 0], [2, 0, 0, 0], [4, 0, 0, 0], [4, 0, 0, 0]]
    b = make_board(grid)
    b.move(direction)
    assert [row[0] for row in b.grid] == expected_col


def test_invalid_move_returns_unchanged():
    b = make_board([[2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    r = b.move(Direction.LEFT)
    assert r.changed is False
    assert r.gained == 0
    assert b.grid[0] == [2, 0, 0, 0]


def test_spawn_on_empty_board_all_cells_free(monkeypatch):
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(random, "random", lambda: 0.99)
    b = Board()
    pos = b.spawn()
    assert pos == (0, 0) and b.grid[0][0] == 2


def test_spawn_returns_none_when_full():
    full = [[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 2]]
    b = make_board(full)
    assert b.spawn() is None


def test_spawn_four_probability(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 0.05)
    b = Board()
    b.spawn()
    assert b.max_tile() == 4


def test_game_over_when_full_and_no_merge():
    full = [[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 2]]
    assert make_board(full).is_game_over() is True


def test_not_game_over_when_merge_possible():
    full = [[2, 2, 4, 8], [16, 32, 64, 128], [256, 512, 1024, 2], [4, 8, 16, 32]]
    assert make_board(full).is_game_over() is False


def test_tile_count_after_move():
    grid = [[2, 2, 4, 4], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    b = make_board(grid)
    before = sum(1 for row in grid for v in row if v)
    r = b.move(Direction.LEFT)
    merges = len(r.merges)
    after = sum(1 for row in b.grid for v in row if v)
    assert after == before - merges
