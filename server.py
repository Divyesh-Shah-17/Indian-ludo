"""
Chauka Bara — Socket.io Multiplayer Server
==========================================
Real-time 4-player game server with room-based matchmaking
and a turn-based state machine.

Start:  python server.py
"""

from __future__ import annotations

import asyncio
import logging
import random
import string
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, Any

import socketio
from aiohttp import web

from chauka_bara import Game, PieceState, grants_extra_turn, roll_cowrie

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("chauka-server")

# ── Room State Machine ───────────────────────────────────────────────────────


class RoomState(str, Enum):
    WAITING = "WAITING"
    PLAYING = "PLAYING"
    FINISHED = "FINISHED"


@dataclass
class PlayerSlot:
    """A connected player in a room."""
    sid: str                  # Socket.io session ID
    player_id: int            # 0-3
    name: str = ""
    turns_taken: int = 0
    is_host: bool = False


@dataclass
class GameRoom:
    """A single game room with up to 4 players."""
    code: str
    state: RoomState = RoomState.WAITING
    slots: list[Optional[PlayerSlot]] = field(default_factory=lambda: [None] * 4)
    game: Optional[Game] = None
    pending_roll: Optional[int] = None   # Dice value awaiting a move

    @property
    def player_count(self) -> int:
        return sum(1 for s in self.slots if s is not None)

    def get_slot_by_sid(self, sid: str) -> Optional[PlayerSlot]:
        for s in self.slots:
            if s and s.sid == sid:
                return s
        return None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "state": self.state.value,
            "players": [
                {"player_id": s.player_id, "name": s.name, "turns_taken": s.turns_taken, "is_host": s.is_host}
                if s else None
                for s in self.slots
            ],
            "player_count": self.player_count,
            "pending_roll": self.pending_roll,
        }


# ── Server ───────────────────────────────────────────────────────────────────

sio = socketio.AsyncServer(async_mode="aiohttp", cors_allowed_origins="*")
app = web.Application()
sio.attach(app)

rooms: Dict[str, GameRoom] = {}
sid_to_room: Dict[str, str] = {}          # maps session → room code
matchmaking_queue: list[dict[str, Any]] = [] # {"sid": "...", "joined_at": 1600.0}


def _generate_code(length: int = 6) -> str:
    """Generate a unique alphanumeric room code."""
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if code not in rooms:
            return code

def _get_player_name(data: Optional[dict]) -> str:
    name = data.get("playerName", "").strip() if data else ""
    if not name:
        guests = ["Gujarati_Hero", "Player_42", "Chauka_Master", "Ludo_King", "Vadodara_Viper", "Surat_Striker", "Ahmedabad_Ace", "Ludo_Champ", "Bhai_01"]
        name = f"{random.choice(guests)}_{random.randint(100, 999)}"
    return name


# ── Serve static files ───────────────────────────────────────────────────────

async def index(request: web.Request) -> web.FileResponse:
    return web.FileResponse("test_client.html")


app.router.add_get("/", index)
app.router.add_static("/static", ".", show_index=False)

# ── Socket.io Event Handlers ────────────────────────────────────────────────


@sio.event
async def connect(sid: str, environ: dict) -> None:
    log.info(f"[CONNECT] {sid}")


@sio.event
async def disconnect(sid: str) -> None:
    log.info(f"[DISCONNECT] {sid}")
    
    global matchmaking_queue
    matchmaking_queue = [p for p in matchmaking_queue if p["sid"] != sid]

    code = sid_to_room.pop(sid, None)
    if code and code in rooms:
        room = rooms[code]
        slot = room.get_slot_by_sid(sid)
        if slot:
            pid = slot.player_id
            room.slots[pid] = None
            await sio.emit("player_left", {"player_id": pid}, room=code)
            await sio.emit("room_updated", {"room": room.to_dict()}, room=code)
            log.info(f"  Player {pid + 1} left room {code}")


@sio.event
async def create_room(sid: str, data: Optional[dict] = None) -> None:
    """Create a new game room and join as Player 1."""
    code = _generate_code()
    room = GameRoom(code=code)

    name = _get_player_name(data)
    # Creator joins as Player 1 (index 0)
    slot = PlayerSlot(sid=sid, player_id=0, name=name, is_host=True)
    room.slots[0] = slot

    rooms[code] = room
    sid_to_room[sid] = code
    await sio.enter_room(sid, code)

    log.info(f"[CREATE] Room {code} by {sid}")
    await sio.emit("room_created", {"code": code, "player_id": 0, "room": room.to_dict()}, to=sid)
    await sio.emit("room_updated", {"room": room.to_dict()}, room=code)


@sio.event
async def join_room(sid: str, data: dict) -> None:
    """Join an existing room by code."""
    code = data.get("code", "").strip().upper()

    if code not in rooms:
        await sio.emit("error", {"message": f"Room '{code}' not found."}, to=sid)
        return

    room = rooms[code]

    if room.state != RoomState.WAITING:
        await sio.emit("error", {"message": "Game already in progress."}, to=sid)
        return

    # Find first empty slot
    slot_idx = None
    for i, s in enumerate(room.slots):
        if s is None:
            slot_idx = i
            break

    if slot_idx is None:
        await sio.emit("error", {"message": "Room is full."}, to=sid)
        return

    name = _get_player_name(data)
    slot = PlayerSlot(sid=sid, player_id=slot_idx, name=name)
    room.slots[slot_idx] = slot
    sid_to_room[sid] = code
    await sio.enter_room(sid, code)

    log.info(f"[JOIN] {sid} -> Room {code} as P{slot_idx + 1}")
    await sio.emit("room_joined", {
        "code": code,
        "player_id": slot_idx,
        "room": room.to_dict(),
    }, to=sid)
    await sio.emit("player_joined", {
        "player_id": slot_idx,
        "player_count": room.player_count,
    }, room=code)
    await sio.emit("room_updated", {"room": room.to_dict()}, room=code)

@sio.event
async def join_public_queue(sid: str, data: Optional[dict] = None) -> None:
    """Join the public matchmaking queue."""
    if sid in sid_to_room:
        await sio.emit("error", {"message": "Already in a room."}, to=sid)
        return
        
    for p in matchmaking_queue:
        if p["sid"] == sid:
            return  # Already queued
            
    name = _get_player_name(data)
    matchmaking_queue.append({"sid": sid, "joined_at": time.time(), "name": name})
    log.info(f"[QUEUE] {sid} joined public matchmaking. Queue size: {len(matchmaking_queue)}")

@sio.event
async def start_game(sid: str, data: Optional[dict] = None) -> None:
    """Host starts the game manually."""
    code_str = str(sid_to_room.get(sid, ""))
    if not code_str or code_str not in rooms:
        await sio.emit("error", {"message": "Not in a room."}, to=sid)
        return

    room = rooms[code_str]
    slot = room.get_slot_by_sid(sid)
    if not slot or not slot.is_host:
        await sio.emit("error", {"message": "Only the host can start the game."}, to=sid)
        return

    if room.player_count < 2:
        await sio.emit("error", {"message": "Need at least 2 players to start."}, to=sid)
        return

    if room.state != RoomState.WAITING:
        await sio.emit("error", {"message": "Game already in progress."}, to=sid)
        return

    await _start_game(room)

async def _start_game(room: GameRoom) -> None:
    """Initialize game state and broadcast start."""
    active_slots = [s for s in room.slots if s is not None]
    count = len(active_slots)
    
    if count == 2:
        pids = [0, 2]
    elif count == 3:
        pids = [0, 1, 2]
    else:
        pids = [0, 1, 2, 3]

    new_slots: list[Optional[PlayerSlot]] = [None, None, None, None]
    for i, slot in enumerate(active_slots):
        slot.player_id = pids[i]
        new_slots[slot.player_id] = slot
    room.slots = new_slots

    # Notify clients of their finalized player_ids
    for slot in active_slots:
        await sio.emit("player_id_updated", {"player_id": slot.player_id}, to=slot.sid)

    room.game = Game(active_pids=pids, pieces_per_player=4)
    room.state = RoomState.PLAYING
    room.pending_roll = None

    log.info(f"[START] Room {room.code} — game started with {count} players: {pids}!")
    
    # Broadcast updated room before game logic
    await sio.emit("room_updated", {"room": room.to_dict()}, room=room.code)
    await sio.emit("game_started", {
        "game_state": room.game.to_dict(),
        "room": room.to_dict(),
    }, room=room.code)
    await sio.emit("turn_changed", {
        "player_id": pids[0],
    }, room=room.code)


@sio.event
async def roll_dice(sid: str, data: dict = None) -> None:
    """Current player rolls the cowrie dice."""
    code = sid_to_room.get(sid)
    if not code or code not in rooms:
        await sio.emit("error", {"message": "Not in a room."}, to=sid)
        return

    room = rooms[code]
    if room.state != RoomState.PLAYING or room.game is None:
        await sio.emit("error", {"message": "Game not active."}, to=sid)
        return

    slot = room.get_slot_by_sid(sid)
    if not slot:
        await sio.emit("error", {"message": "Not a player."}, to=sid)
        return

    game = room.game
    if slot.player_id != game.current_turn:
        await sio.emit("error", {"message": "Not your turn."}, to=sid)
        return

    if room.pending_roll is not None:
        await sio.emit("error", {"message": "Already rolled. Choose a piece to move."}, to=sid)
        return

    value = roll_cowrie()
    room.pending_roll = value
    extra = grants_extra_turn(value)

    log.info(f"  P{slot.player_id + 1} rolled {value} {'(EXTRA TURN!)' if extra else ''}")
    await sio.emit("dice_rolled", {
        "player_id": slot.player_id,
        "value": value,
        "extra_turn": extra,
    }, room=room.code)


@sio.event
async def move_piece(sid: str, data: dict) -> None:
    """Current player moves a specific piece using the pending roll value."""
    code = sid_to_room.get(sid)
    if not code or code not in rooms:
        await sio.emit("error", {"message": "Not in a room."}, to=sid)
        return

    room = rooms[code]
    if room.state != RoomState.PLAYING or room.game is None:
        await sio.emit("error", {"message": "Game not active."}, to=sid)
        return

    slot = room.get_slot_by_sid(sid)
    if not slot:
        await sio.emit("error", {"message": "Not a player."}, to=sid)
        return

    game = room.game
    if slot.player_id != game.current_turn:
        await sio.emit("error", {"message": "Not your turn."}, to=sid)
        return

    if room.pending_roll is None:
        await sio.emit("error", {"message": "Roll the dice first."}, to=sid)
        return

    piece_id = data.get("piece_id", 0)
    player = game.players[slot.player_id]

    if piece_id < 0 or piece_id >= len(player.pieces):
        await sio.emit("error", {"message": f"Invalid piece_id: {piece_id}"}, to=sid)
        return

    piece = player.pieces[piece_id]
    log.info(f"  P{slot.player_id + 1} piece {piece_id}: {room.pending_roll} roll Pending")
    result = game.move_piece(piece, room.pending_roll)

    log.info(f"  P{slot.player_id + 1} piece {piece_id} path_index {result.piece.path_index}: {result.message}")

    await sio.emit("piece_moved", {
        "player_id": slot.player_id,
        "piece_id": piece_id,
        "roll_value": room.pending_roll,
        "result": result.to_dict(),
    }, room=room.code)

    if not result.success:
        # Move failed — let client try another piece or skip
        return

    # Move succeeded
    room.pending_roll = None
    slot.turns_taken += 1

    # Check for winner
    winner = game.get_winner()
    if winner:
        room.state = RoomState.FINISHED
        log.info(f"[WINNER] Room {room.code}: Player {winner.id + 1}!")
        await sio.emit("game_over", {
            "winner_id": winner.id,
            "game_state": game.to_dict(),
        }, room=room.code)
        return

    # Advance turn (unless extra turn)
    if result.extra_turn:
        log.info(f"  P{slot.player_id + 1} gets an extra turn!")
    else:
        game.advance_turn()

    await sio.emit("state_update", {
        "game_state": game.to_dict(),
        "room": room.to_dict(),
    }, room=room.code)
    await sio.emit("turn_changed", {
        "player_id": game.current_turn,
    }, room=room.code)


@sio.event
async def skip_turn(sid: str, data: dict = None) -> None:
    """Player opts to skip (no valid moves for the current roll)."""
    code = sid_to_room.get(sid)
    if not code or code not in rooms:
        return

    room = rooms[code]
    if room.state != RoomState.PLAYING or room.game is None:
        return

    slot = room.get_slot_by_sid(sid)
    if not slot or slot.player_id != room.game.current_turn:
        return

    game = room.game
    room.pending_roll = None
    slot.turns_taken += 1

    log.info(f"  P{slot.player_id + 1} skipped (no valid moves)")
    game.advance_turn()

    await sio.emit("state_update", {
        "game_state": game.to_dict(),
        "room": room.to_dict(),
    }, room=room.code)
    await sio.emit("turn_changed", {
        "player_id": game.current_turn,
    }, room=room.code)


# ── Matchmaking Worker ────────────────────────────────────────────────────────

async def _create_match_from_queue(players: list[dict[str, Any]]) -> None:
    code = _generate_code()
    room = GameRoom(code=code)
    
    for i, p_info in enumerate(players):
        sid = p_info["sid"]
        name = p_info.get("name") or _get_player_name(None)
        slot = PlayerSlot(sid=sid, player_id=i, name=name, is_host=(i == 0))
        room.slots[i] = slot
        sid_to_room[sid] = code
        await sio.enter_room(sid, code)
    
    rooms[code] = room
    
    for slot in room.slots:
        if slot:
            log.info(f"[MATCHMAKING] {slot.sid} -> Room {code} as P{slot.player_id + 1}")
            await sio.emit("room_joined", {
                "code": code,
                "player_id": slot.player_id,
                "room": room.to_dict(),
            }, to=slot.sid)
            
    await sio.emit("room_updated", {"room": room.to_dict()}, room=code)
    await _start_game(room)

async def matchmaking_worker() -> None:
    while True:
        await asyncio.sleep(1.0)
        global matchmaking_queue
        
        n = len(matchmaking_queue)
        if n >= 4:
            players = matchmaking_queue[:4]
            matchmaking_queue = matchmaking_queue[4:]
            await _create_match_from_queue(players)
        elif n >= 2:
            longest_wait = time.time() - matchmaking_queue[0]["joined_at"]
            if longest_wait >= 30.0:
                players = matchmaking_queue[:4]
                matchmaking_queue = matchmaking_queue[4:]
                await _create_match_from_queue(players)

async def start_background_tasks(app: web.Application) -> None:
    app['matchmaking_worker'] = asyncio.create_task(matchmaking_worker())

# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.on_startup.append(start_background_tasks)
    PORT = 8765
    log.info(f"Chauka Bara server starting on http://localhost:{PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
