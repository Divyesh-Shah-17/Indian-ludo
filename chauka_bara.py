"""
Chauka Bara (Gujarati Ludo) — Core Game Engine
================================================
A 4-player board game played on a 5×5 grid with cowrie-shell dice.
Players spiral inward from their starting edge toward the center (2,2).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

# ── Constants ────────────────────────────────────────────────────────────────

BOARD_SIZE = 5
CENTER: tuple[int, int] = (2, 2)

# Cells on the perimeter (outer ring) and the 3×3 interior minus center (inner ring)
OUTER_RING: set[tuple[int, int]] = {
    (r, c)
    for r in range(BOARD_SIZE)
    for c in range(BOARD_SIZE)
    if r == 0 or r == 4 or c == 0 or c == 4
}

INNER_RING: set[tuple[int, int]] = {
    (r, c)
    for r in range(1, 4)
    for c in range(1, 4)
    if (r, c) != CENTER
}

# Cells where no capture is allowed
SAFE_ZONES: set[tuple[int, int]] = {(0, 2), (2, 0), (4, 2), (2, 4), CENTER}

# Number of cowrie shells
NUM_COWRIES = 4

# Rolls that grant an extra turn
EXTRA_TURN_VALUES: set[int] = {4, 8}

# ── Paths ────────────────────────────────────────────────────────────────────
# Each path has 25 steps:
#   Steps  0-15  →  Outer Ring  (16 border cells, clockwise)
#   Steps 16-23  →  Inner Ring  (8 interior cells, clockwise)
#   Step  24     →  Center (2,2)

PATHS: dict[int, list[tuple[int, int]]] = {
    # Player 1 — starts top-middle (0,2), spirals clockwise
    0: [
        # Outer ring (clockwise from top-mid)
        (0, 2), (0, 3), (0, 4), (1, 4), (2, 4),
        (3, 4), (4, 4), (4, 3), (4, 2), (4, 1),
        (4, 0), (3, 0), (2, 0), (1, 0), (0, 0), (0, 1),
        # Inner ring (clockwise from top-left)
        (1, 1), (1, 2), (1, 3), (2, 3),
        (3, 3), (3, 2), (3, 1), (2, 1),
        # Center
        (2, 2),
    ],

    # Player 2 — starts left-middle (2,0), spirals clockwise
    1: [
        # Outer ring (clockwise from left-mid)
        (2, 0), (1, 0), (0, 0), (0, 1), (0, 2),
        (0, 3), (0, 4), (1, 4), (2, 4), (3, 4),
        (4, 4), (4, 3), (4, 2), (4, 1), (4, 0), (3, 0),
        # Inner ring (clockwise from bottom-left)
        (3, 1), (2, 1), (1, 1), (1, 2),
        (1, 3), (2, 3), (3, 3), (3, 2),
        # Center
        (2, 2),
    ],

    # Player 3 — starts bottom-middle (4,2), spirals clockwise
    2: [
        # Outer ring (clockwise from bottom-mid)
        (4, 2), (4, 1), (4, 0), (3, 0), (2, 0),
        (1, 0), (0, 0), (0, 1), (0, 2), (0, 3),
        (0, 4), (1, 4), (2, 4), (3, 4), (4, 4), (4, 3),
        # Inner ring (clockwise from bottom-right)
        (3, 3), (3, 2), (3, 1), (2, 1),
        (1, 1), (1, 2), (1, 3), (2, 3),
        # Center
        (2, 2),
    ],

    # Player 4 — starts right-middle (2,4), spirals clockwise
    3: [
        # Outer ring (clockwise from right-mid)
        (2, 4), (3, 4), (4, 4), (4, 3), (4, 2),
        (4, 1), (4, 0), (3, 0), (2, 0), (1, 0),
        (0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (1, 4),
        # Inner ring (clockwise from top-right)
        (1, 3), (2, 3), (3, 3), (3, 2),
        (3, 1), (2, 1), (1, 1), (1, 2),
        # Center
        (2, 2),
    ],
}

# Boundary between outer and inner rings (last outer step index)
OUTER_LAST_INDEX = 15
INNER_FIRST_INDEX = 16

# ── Dice ─────────────────────────────────────────────────────────────────────


def roll_cowrie() -> int:
    """Simulate rolling 4 cowrie shells.

    Each shell lands as 0 or 1.  The move value is the sum of the four
    shells, with the special case that all-zero (0+0+0+0) counts as **8**.

    Returns
    -------
    int
        A value in {1, 2, 3, 4, 8}.
    """
    bits = [random.randint(0, 1) for _ in range(NUM_COWRIES)]
    total = sum(bits)
    return 8 if total == 0 else total


def grants_extra_turn(roll: int) -> bool:
    """Return *True* if the rolled value earns an extra turn (4 or 8)."""
    return roll in EXTRA_TURN_VALUES


# ── Game Entities ────────────────────────────────────────────────────────────


class PieceState(IntEnum):
    """Lifecycle states of a game piece."""
    HOME = -1       # Not yet on the board
    ON_BOARD = 0    # Travelling the path
    FINISHED = 1    # Reached the center


@dataclass
class Piece:
    """A single game token belonging to a player."""

    player_id: int
    piece_id: int
    path_index: int = -1          # -1 = at home, 0-24 = position on path
    state: PieceState = PieceState.HOME

    # ── Derived helpers ──────────────────────────────────────────────────

    @property
    def is_home(self) -> bool:
        return self.state == PieceState.HOME

    @property
    def is_finished(self) -> bool:
        return self.state == PieceState.FINISHED

    @property
    def position(self) -> Optional[tuple[int, int]]:
        """Current (row, col) on the board, or *None* if at home / finished."""
        if self.state != PieceState.ON_BOARD:
            return None
        return PATHS[self.player_id][self.path_index]

    def send_home(self) -> None:
        """Reset piece back to home."""
        self.path_index = -1
        self.state = PieceState.HOME

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dictionary."""
        pos = self.position
        return {
            "player_id": self.player_id,
            "piece_id": self.piece_id,
            "path_index": self.path_index,
            "state": self.state.name,
            "position": list(pos) if pos else None,
        }

    def __repr__(self) -> str:
        return f"Piece(P{self.player_id + 1}-{self.piece_id}, idx={self.path_index}, {self.state.name})"


@dataclass
class Player:
    """A player in the game, owning multiple pieces."""

    id: int
    pieces: list[Piece] = field(default_factory=list)
    can_enter_inner: bool = False     # Gate rule flag

    @property
    def start_cell(self) -> tuple[int, int]:
        return PATHS[self.id][0]

    @property
    def all_finished(self) -> bool:
        return all(p.is_finished for p in self.pieces)

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "can_enter_inner": self.can_enter_inner,
            "all_finished": self.all_finished,
            "pieces": [p.to_dict() for p in self.pieces],
        }

    def __repr__(self) -> str:
        gate = "OPEN" if self.can_enter_inner else "LOCKED"
        return f"Player(P{self.id + 1}, gate={gate}, pieces={self.pieces})"


# ── Game Engine ──────────────────────────────────────────────────────────────


@dataclass
class MoveResult:
    """Outcome of a single move attempt."""
    success: bool
    piece: Optional[Piece] = None
    captured: Optional[Piece] = None
    extra_turn: bool = False
    message: str = ""

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dictionary."""
        return {
            "success": self.success,
            "piece": self.piece.to_dict() if self.piece is not None else None,
            "captured": self.captured.to_dict() if self.captured is not None else None,
            "extra_turn": self.extra_turn,
            "message": self.message,
        }


class Game:
    """Core Chauka Bara game engine for 4 players.

    Parameters
    ----------
    pieces_per_player : int
        Number of tokens each player controls (typically 2 or 4).
    """

    def __init__(self, active_pids: Optional[list[int]] = None, pieces_per_player: int = 4) -> None:
        if active_pids is None:
            active_pids = [0, 1, 2, 3]
        self.active_pids = active_pids
        self.players: list[Player] = []
        self.current_turn: int = active_pids[0]          # the actual player id
        self.board: list[list[list[Piece]]] = [
            [[] for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)
        ]
        for pid in range(4):
            player = Player(id=pid)
            if pid in active_pids:
                for i in range(pieces_per_player):
                    player.pieces.append(Piece(player_id=pid, piece_id=i))
            self.players.append(player)

    # ── Public API ───────────────────────────────────────────────────────

    @property
    def current_player(self) -> Player:
        return self.players[self.current_turn]

    def roll(self) -> int:
        """Roll the cowrie dice and return the value."""
        return roll_cowrie()

    def move_piece(self, piece: Piece, steps: int) -> MoveResult:
        """Attempt to move *piece* forward by *steps* on its path.

        Handles:
        - Entering the board from home (must roll to enter)
        - Normal forward movement
        - Gate rule (blocks entry into the inner ring)
        - Captures on non-safe cells
        - Reaching the center (finishing)

        Returns a ``MoveResult`` describing what happened.
        """
        player = self.players[piece.player_id]
        extra = grants_extra_turn(steps)

        # ── Enter the board from home ────────────────────────────────────
        if piece.is_home:
            return self._enter_board(piece, player, steps, extra)

        if piece.is_finished:
            return MoveResult(False, piece, message="Piece already finished.")

        # ── Calculate target index ───────────────────────────────────────
        target_index = piece.path_index + steps

        # Overshoot — cannot move past center
        if target_index > 24:
            return MoveResult(
                False, piece,
                message=f"Roll of {steps} overshoots the center. {target_index}",
            )

        # ── Gate rule — cannot enter inner ring without a capture ────────
        if (
            piece.path_index <= OUTER_LAST_INDEX
            and target_index >= INNER_FIRST_INDEX
            and not player.can_enter_inner
        ):
            return MoveResult(
                False, piece,
                message="Gate is locked — capture an opponent first.",
            )

        # ── Execute the move ─────────────────────────────────────────────
        old_pos = piece.position
        self._remove_from_board(piece)

        piece.path_index = target_index
        new_pos = PATHS[piece.player_id][target_index]

        # Check for reaching center
        if target_index == 24:
            piece.state = PieceState.FINISHED
            return MoveResult(
                True, piece, extra_turn=extra,
                message=f"Piece reached the center!",
            )

        # ── Capture check ────────────────────────────────────────────────
        captured = self._try_capture(piece, new_pos, player)

        self._place_on_board(piece)

        cap_msg = f" Captured {captured}!" if captured else ""
        return MoveResult(
            True, piece, captured=captured, extra_turn=extra,
            message=f"Moved to {new_pos}.{cap_msg}",
        )

    def advance_turn(self) -> Player:
        """Move to the next active player's turn. Returns the new current player."""
        idx = self.active_pids.index(self.current_turn)
        next_idx = (idx + 1) % len(self.active_pids)
        self.current_turn = self.active_pids[next_idx]
        return self.current_player

    def get_winner(self) -> Optional[Player]:
        """Return the winning player, or *None* if no one has won yet."""
        for p in self.players:
            if p.all_finished:
                return p
        return None

    # ── Private helpers ──────────────────────────────────────────────────

    def _enter_board(self, piece: Piece, player: Player, steps: int, extra: bool) -> MoveResult:
        """Place a piece on its starting cell (index derived from steps)."""
        start = player.start_cell
        piece.path_index = steps
        piece.state = PieceState.ON_BOARD

        new_pos = PATHS[piece.player_id][piece.path_index]
        captured = self._try_capture(piece, new_pos, player)
        self._place_on_board(piece)

        cap_msg = f" Captured {captured}!" if captured else ""
        return MoveResult(
            True, piece, captured=captured, extra_turn=extra,
            message=f"Entered the board at {new_pos}.{cap_msg}",
        )

    def _try_capture(
        self, piece: Piece, cell: tuple[int, int], player: Player
    ) -> Optional[Piece]:
        """If *cell* has an opponent and is not safe, capture it."""
        if cell in SAFE_ZONES:
            return None

        r, c = cell
        occupants: list[Piece] = self.board[r][c]
        for occ in occupants:
            if occ.player_id != piece.player_id:
                # Capture!
                self._remove_from_board(occ)
                occ.send_home()
                player.can_enter_inner = True
                return occ
        return None

    def _place_on_board(self, piece: Piece) -> None:
        pos = piece.position
        if pos is not None:
            r, c = pos
            self.board[r][c].append(piece)

    def _remove_from_board(self, piece: Piece) -> None:
        pos = piece.position
        if pos is not None:
            r, c = pos
            cell = self.board[r][c]
            if piece in cell:
                cell.remove(piece)

    # ── Serialization ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize full game state to a JSON-safe dictionary."""
        # Build a simple 5x5 board view: each cell is a list of piece labels
        board_view: list[list[list[str]]] = []
        for r in range(BOARD_SIZE):
            row: list[list[str]] = []
            for c in range(BOARD_SIZE):
                row.append([f"P{p.player_id+1}-{p.piece_id}" for p in self.board[r][c]])
            board_view.append(row)

        return {
            "current_turn": self.current_turn,
            "players": [p.to_dict() for p in self.players],
            "board": board_view,
            "safe_zones": [list(z) for z in SAFE_ZONES],
            "winner": self.get_winner().to_dict() if self.get_winner() is not None else None,
        }

    # ── Pretty-print ─────────────────────────────────────────────────────

    def print_board(self) -> str:
        """Return a human-readable board representation."""
        lines: list[str] = []
        lines.append("     " + "   ".join(f"C{c}" for c in range(BOARD_SIZE)))
        lines.append("   " + "+" + "------+" * BOARD_SIZE)
        for r in range(BOARD_SIZE):
            row_cells: list[str] = []
            for c in range(BOARD_SIZE):
                occupants = self.board[r][c]
                if occupants:
                    labels = ",".join(f"P{p.player_id+1}" for p in occupants)
                    row_cells.append(f"{labels:^6}")
                elif (r, c) in SAFE_ZONES:
                    row_cells.append("  **  ")
                else:
                    row_cells.append("      ")
            line = f"R{r} |" + "|".join(row_cells) + "|"
            lines.append(line)
            lines.append("   " + "+" + "------+" * BOARD_SIZE)
        return "\n".join(lines)


# ── Path Validation Utility ──────────────────────────────────────────────────


def validate_paths() -> None:
    """Run sanity checks on every defined path. Raises AssertionError on failure."""
    expected_starts = {0: (0, 2), 1: (2, 0), 2: (4, 2), 3: (2, 4)}

    for pid, path in PATHS.items():
        tag = f"Player {pid + 1}"
        assert len(path) == 25, f"{tag}: expected 25 steps, got {len(path)}"
        assert len(set(path)) == 25, f"{tag}: duplicate cells in path"
        assert path[0] == expected_starts[pid], f"{tag}: wrong start {path[0]}"
        assert path[24] == CENTER, f"{tag}: path does not end at center"

        # Outer ring check (steps 0-15)
        for i in range(16):
            assert path[i] in OUTER_RING, f"{tag}: step {i} {path[i]} not in outer ring"

        # Inner ring check (steps 16-23)
        for i in range(16, 24):
            assert path[i] in INNER_RING, f"{tag}: step {i} {path[i]} not in inner ring"

    print("[OK] All paths validated successfully.")


if __name__ == "__main__":
    validate_paths()
