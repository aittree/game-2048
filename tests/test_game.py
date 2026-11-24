"""游戏状态机单元测试（docs/05 §2.6），不依赖 pygame。"""

import pytest

from src.board import Board
from src.game import Action, Game, GameState


@pytest.fixture
def game(monkeypatch):
    monkeypatch.setattr("src.game.storage.save_best", lambda best: None)
    return Game(best=0)


def test_score_accumulates(game):
    game.board = Board([[2, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    game.score = 0
    game.handle_action(Action.LEFT)
    assert game.score == 4
    assert game.best == 4


def test_best_never_decreases(game):
    game.best = 100
    game.score = 100
    game.handle_action(Action.RESTART)
    assert game.score == 0
    assert game.best == 100


def test_win_state_triggers_once(game):
    game.board = Board([[1024, 1024, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    game.handle_action(Action.LEFT)
    assert game.state is GameState.WIN
    assert game.win_shown is True

    # 浮层期间方向键应被忽略
    score = game.score
    game.handle_action(Action.RIGHT)
    assert game.score == score and game.state is GameState.WIN

    game.handle_action(Action.CONTINUE)
    assert game.state is GameState.RUNNING


def test_undo_restores_grid_and_score(game):
    game.board = Board([[2, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    game.score = 0
    game.handle_action(Action.LEFT)
    assert game.score == 4

    game.handle_action(Action.UNDO)
    assert game.score == 0
    assert game.board.grid[0][0] == 2


def test_invalid_move_does_not_spawn_or_score(game, monkeypatch):
    game.board = Board([[2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    game.score = 0

    def _fail():
        raise AssertionError("无效移动不应生成新方块")

    monkeypatch.setattr(game.board, "spawn", _fail)
    game.handle_action(Action.LEFT)

    assert game.score == 0
    assert game.board.grid[0] == [2, 0, 0, 0]
    assert game._undo_stack == []
