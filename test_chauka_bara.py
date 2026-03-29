"""
Tests for the Chauka Bara core game engine.
Run with:  python -m pytest test_chauka_bara.py -v
"""

import pytest

from chauka_bara import (
    CENTER,
    EXTRA_TURN_VALUES,
    INNER_RING,
    OUTER_RING,
    PATHS,
    SAFE_ZONES,
    Game,
    MoveResult,
    Piece,
    PieceState,
    Player,
    grants_extra_turn,
    roll_cowrie,
)


# ── Path Tests ───────────────────────────────────────────────────────────────


class TestPaths:
    """Validate the four spiral path definitions."""

    EXPECTED_STARTS = {0: (0, 2), 1: (2, 0), 2: (4, 2), 3: (2, 4)}

    @pytest.mark.parametrize("pid", [0, 1, 2, 3])
    def test_paths_length(self, pid: int):
        """Each path must have exactly 25 steps."""
        assert len(PATHS[pid]) == 25

    @pytest.mark.parametrize("pid", [0, 1, 2, 3])
    def test_paths_unique(self, pid: int):
        """No duplicate coordinates within a single path."""
        assert len(set(PATHS[pid])) == 25

    @pytest.mark.parametrize("pid", [0, 1, 2, 3])
    def test_paths_start_end(self, pid: int):
        """Each path starts at its expected entry and ends at center (2,2)."""
        path = PATHS[pid]
        assert path[0] == self.EXPECTED_STARTS[pid]
        assert path[24] == CENTER

    @pytest.mark.parametrize("pid", [0, 1, 2, 3])
    def test_paths_outer_inner_split(self, pid: int):
        """Steps 0-15 are on the outer ring; steps 16-23 on the inner ring."""
        path = PATHS[pid]
        for i in range(16):
            assert path[i] in OUTER_RING, f"Step {i} = {path[i]} not in outer ring"
        for i in range(16, 24):
            assert path[i] in INNER_RING, f"Step {i} = {path[i]} not in inner ring"


# ── Dice Tests ───────────────────────────────────────────────────────────────


class TestDice:
    """Validate cowrie-shell dice mechanics."""

    def test_roll_cowrie_range(self):
        """1000 rolls must all produce values in {1, 2, 3, 4, 8}."""
        valid = {1, 2, 3, 4, 8}
        results = {roll_cowrie() for _ in range(1000)}
        assert results.issubset(valid), f"Unexpected values: {results - valid}"

    def test_extra_turn(self):
        """Rolls of 4 and 8 grant extra turns; 1, 2, 3 do not."""
        assert grants_extra_turn(4) is True
        assert grants_extra_turn(8) is True
        assert grants_extra_turn(1) is False
        assert grants_extra_turn(2) is False
        assert grants_extra_turn(3) is False


# ── Safe Zone & Capture Tests ────────────────────────────────────────────────


class TestCapture:
    """Validate capture and safe-zone logic."""

    def _setup_game(self) -> Game:
        """Create a fresh 4-player game with 1 piece each for test clarity."""
        return Game(pieces_per_player=1)

    def test_safe_zone_no_capture(self):
        """A piece on a safe zone must NOT be captured."""
        game = self._setup_game()
        p0 = game.players[0]
        p1 = game.players[1]
        piece0 = p0.pieces[0]
        piece1 = p1.pieces[0]

        # Manually place piece1 on P0's start (a safe zone)
        piece1.path_index = 4  # (0,2) appears at index 4 in P1's path
        piece1.state = PieceState.ON_BOARD
        pos = piece1.position
        game.board[pos[0]][pos[1]].append(piece1)

        # Now enter piece0 onto its start (0,2) — same cell, but it's safe
        result = game.move_piece(piece0, 1)
        assert result.success
        assert result.captured is None  # No capture on safe zone!
        assert piece1.state == PieceState.ON_BOARD  # piece1 is still alive

    def test_capture_sends_home(self):
        """Capturing on a non-safe cell sends the opponent home."""
        game = self._setup_game()
        p0 = game.players[0]
        p1 = game.players[1]
        piece0 = p0.pieces[0]
        piece1 = p1.pieces[0]

        # Place piece0 on the board at path index 0
        piece0.path_index = 0
        piece0.state = PieceState.ON_BOARD
        game._place_on_board(piece0)

        # P0 path step 1 = (0,3), which is NOT a safe zone
        target_cell = PATHS[0][1]
        assert target_cell == (0, 3)
        assert target_cell not in SAFE_ZONES, "Test setup error: cell is safe"

        # Find piece1's valid path index for the same cell (0,3)
        # P1 path: (2,0),(1,0),(0,0),(0,1),(0,2),(0,3),... → index 5 is (0,3)
        p1_index = PATHS[1].index((0, 3))
        piece1.path_index = p1_index
        piece1.state = PieceState.ON_BOARD
        game._place_on_board(piece1)

        # Move piece0 forward 1 step to land on target_cell
        result = game.move_piece(piece0, 1)
        assert result.success
        assert result.captured is piece1
        assert piece1.is_home

    def test_gate_blocks_inner(self):
        """A piece cannot enter the inner ring without can_enter_inner = True."""
        game = self._setup_game()
        player = game.players[0]
        piece = player.pieces[0]

        # Place piece at step 15 (last outer step)
        piece.path_index = 15
        piece.state = PieceState.ON_BOARD
        game._place_on_board(piece)

        # Gate is locked
        assert player.can_enter_inner is False

        # Try to move 1 step forward → should be blocked
        result = game.move_piece(piece, 1)
        assert result.success is False
        assert "Gate" in result.message or "locked" in result.message.lower()

    def test_gate_unlocks_on_capture(self):
        """After a capture, can_enter_inner flips to True."""
        game = self._setup_game()
        p0 = game.players[0]
        piece0 = p0.pieces[0]
        p1 = game.players[1]
        piece1 = p1.pieces[0]

        # Place piece0 at step 2 (path[2] = (0,4), which is safe — use step 3)
        piece0.path_index = 2
        piece0.state = PieceState.ON_BOARD
        game._place_on_board(piece0)

        # Step 3 for P0 is (1,4) — NOT a safe zone
        step3_cell = PATHS[0][3]
        assert step3_cell == (1, 4)
        assert step3_cell not in SAFE_ZONES

        # Find piece1's valid path index for the same cell (1,4)
        # P1 path: ...(0,4),(1,4),... → index 7 is (1,4)
        p1_index = PATHS[1].index((1, 4))
        piece1.path_index = p1_index
        piece1.state = PieceState.ON_BOARD
        game._place_on_board(piece1)

        assert p0.can_enter_inner is False

        # Move piece0 one step → capture
        result = game.move_piece(piece0, 1)
        assert result.success
        assert result.captured is piece1
        assert p0.can_enter_inner is True
