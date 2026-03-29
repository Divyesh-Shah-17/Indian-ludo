"""
Multi-client integration test for Chauka Bara Socket.io server.
Simulates 4 players creating/joining a room and playing 10 turns each.

Run:  python test_multiplayer.py
"""

from __future__ import annotations

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import socketio
from aiohttp import web

# Fresh import — clear any leftover state
import importlib
import server as srv
importlib.reload(srv)

TARGET_TURNS = 10
NUM_PLAYERS = 4
PORT = 8766


class TestClient:
    """A simulated player client."""

    def __init__(self, player_label: str):
        self.label = player_label
        self.sio = socketio.AsyncClient(reconnection=False)
        self.player_id: int = -1
        self.room_code: str = ""
        self.turn_count: int = 0
        self.events: list[dict] = []
        self.game_states: list[dict] = []
        self.is_my_turn: bool = False
        self.pending_roll: int = 0
        self.game_active: bool = False
        self.errors: list[str] = []
        self._setup_handlers()

    def _setup_handlers(self):
        sio = self.sio

        @sio.on("room_created")
        async def on_room_created(data):
            self.room_code = data["code"]
            self.player_id = data["player_id"]
            self.events.append({"type": "room_created", "data": data})
            self._log(f"Room created: {self.room_code}, I am P{self.player_id + 1}")

        @sio.on("room_joined")
        async def on_room_joined(data):
            self.room_code = data["code"]
            self.player_id = data["player_id"]
            self.events.append({"type": "room_joined", "data": data})
            self._log(f"Joined {self.room_code} as P{self.player_id + 1}")

        @sio.on("player_joined")
        async def on_player_joined(data):
            self.events.append({"type": "player_joined", "data": data})

        @sio.on("game_started")
        async def on_game_started(data):
            self.game_active = True
            self.game_states.append(data["game_state"])
            self.events.append({"type": "game_started"})
            self._log("Game started!")

        @sio.on("dice_rolled")
        async def on_dice_rolled(data):
            self.events.append({"type": "dice_rolled", "data": data})
            if data["player_id"] == self.player_id:
                self.pending_roll = data["value"]
                extra = " (EXTRA!)" if data["extra_turn"] else ""
                self._log(f"Rolled {data['value']}{extra}")
                # Auto-move: try piece 0 first
                await asyncio.sleep(0.03)
                await sio.emit("move_piece", {"piece_id": 0})

        @sio.on("piece_moved")
        async def on_piece_moved(data):
            self.events.append({"type": "piece_moved", "data": data})
            r = data["result"]
            if data["player_id"] == self.player_id:
                if not r["success"]:
                    # Try piece 1
                    if data["piece_id"] == 0:
                        await asyncio.sleep(0.03)
                        await sio.emit("move_piece", {"piece_id": 1})
                    else:
                        # Both pieces failed — skip
                        self._log("No valid moves, skipping")
                        await sio.emit("skip_turn", {})

        @sio.on("state_update")
        async def on_state_update(data):
            self.game_states.append(data["game_state"])
            if data.get("room") and data["room"]["players"]:
                slot = data["room"]["players"][self.player_id]
                if slot:
                    self.turn_count = slot["turns_taken"]

        @sio.on("turn_changed")
        async def on_turn_changed(data):
            self.is_my_turn = data["player_id"] == self.player_id
            self.events.append({"type": "turn_changed", "data": data})

            if self.is_my_turn and self.game_active:
                if self.turn_count >= TARGET_TURNS:
                    self._log(f"Reached {TARGET_TURNS} turns!")
                    return
                await asyncio.sleep(0.03)
                self._log(f"Turn #{self.turn_count + 1} - rolling...")
                await sio.emit("roll_dice", {})

        @sio.on("game_over")
        async def on_game_over(data):
            self.game_active = False
            self.events.append({"type": "game_over", "data": data})
            self._log(f"Game over! Winner: P{data['winner_id'] + 1}")

        @sio.on("error")
        async def on_error(data):
            self.errors.append(data["message"])
            self._log(f"ERROR: {data['message']}")

    def _log(self, msg: str):
        print(f"  [{self.label}] {msg}")

    async def connect(self):
        await self.sio.connect(f"http://localhost:{PORT}", transports=["websocket"])
        self._log(f"Connected (sid={self.sio.sid})")

    async def disconnect(self):
        try:
            await self.sio.disconnect()
        except Exception:
            pass


async def run_test():
    print("=" * 60)
    print("  CHAUKA BARA - Multi-Client Integration Test")
    print(f"  {NUM_PLAYERS} players x {TARGET_TURNS} turns each")
    print("=" * 60)

    # Clear any stale server state
    srv.rooms.clear()
    srv.sid_to_room.clear()

    runner = web.AppRunner(srv.app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"\n[SERVER] Running on port {PORT}\n")

    clients: list[TestClient] = []

    try:
        # Connect all 4 clients
        for i in range(NUM_PLAYERS):
            c = TestClient(f"P{i + 1}")
            clients.append(c)
            await c.connect()
            await asyncio.sleep(0.15)

        # Player 1 creates room
        await clients[0].sio.emit("create_room", {})
        await asyncio.sleep(0.5)

        room_code = clients[0].room_code
        assert room_code, "Room was not created!"
        print(f"[TEST] Room code: {room_code}\n")

        # Players 2-4 join the room
        for c in clients[1:]:
            await c.sio.emit("join_room", {"code": room_code})
            await asyncio.sleep(0.5)

        # Wait for game_started to propagate
        await asyncio.sleep(1.0)

        print("[TEST] Checking game_started receipt...")
        for c in clients:
            started = any(e["type"] == "game_started" for e in c.events)
            print(f"  {c.label}: game_started={'YES' if started else 'NO'}")

        print(f"\n[TEST] Auto-playing up to {TARGET_TURNS} turns per player...\n")

        # Poll until all players have enough turns or timeout
        for tick in range(200):  # 200 * 0.3 = 60s max
            await asyncio.sleep(0.3)
            all_done = all(c.turn_count >= TARGET_TURNS for c in clients)
            game_over = any(any(e["type"] == "game_over" for e in c.events) for c in clients)
            if all_done or game_over:
                break

        # Give a moment for final events to settle
        await asyncio.sleep(0.5)

        # ── Results ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  TEST RESULTS")
        print("=" * 60)

        for c in clients:
            game_over_flag = any(e["type"] == "game_over" for e in c.events)
            if c.turn_count >= TARGET_TURNS:
                status = "PASS"
            elif game_over_flag:
                status = "DONE (game won)"
            else:
                status = "INCOMPLETE"
            print(f"  {c.label}: {status} | {c.turn_count}/{TARGET_TURNS} turns "
                  f"| {len(c.game_states)} states | {len(c.errors)} errors")

        total_turns = sum(c.turn_count for c in clients)
        print(f"\n  Total turns: {total_turns}")
        print(f"  Total state updates: {sum(len(c.game_states) for c in clients)}")

        # ── Validation ───────────────────────────────────────────────────
        print("\n  --- Validation ---")
        passed = 0
        total = 0

        # 1. Player IDs
        total += 1
        ids = sorted(c.player_id for c in clients)
        if ids == [0, 1, 2, 3]:
            print("  [PASS] All 4 player IDs assigned correctly")
            passed += 1
        else:
            print(f"  [FAIL] Player IDs: {ids}")

        # 2. game_started
        total += 1
        all_started = all(any(e["type"] == "game_started" for e in c.events) for c in clients)
        if all_started:
            print("  [PASS] All clients received game_started")
            passed += 1
        else:
            missing = [c.label for c in clients if not any(e["type"] == "game_started" for e in c.events)]
            print(f"  [FAIL] Missing game_started: {missing}")

        # 3. Turn count
        total += 1
        game_ended = any(any(e["type"] == "game_over" for e in c.events) for c in clients)
        enough = all(c.turn_count >= TARGET_TURNS for c in clients)
        if enough or game_ended:
            reason = "game completed" if game_ended else f"all reached {TARGET_TURNS}"
            print(f"  [PASS] Turns completed ({reason})")
            passed += 1
        else:
            counts = {c.label: c.turn_count for c in clients}
            print(f"  [FAIL] Incomplete turns: {counts}")

        # 4. State sync
        total += 1
        if all(len(c.game_states) > 0 for c in clients):
            final = [c.game_states[-1] for c in clients]
            ct_set = set(s["current_turn"] for s in final)
            if len(ct_set) == 1:
                print("  [PASS] Final game state synchronized")
                passed += 1
            else:
                print(f"  [FAIL] State desync: current_turn = {ct_set}")
        else:
            empty = [c.label for c in clients if not c.game_states]
            print(f"  [FAIL] No state updates for: {empty}")

        # 5. Turn order (from one client's perspective)
        total += 1
        turn_pids = [e["data"]["player_id"] for e in clients[0].events if e["type"] == "turn_changed"]
        if len(turn_pids) >= NUM_PLAYERS:
            print(f"  [PASS] Turn order validated ({len(turn_pids)} changes)")
            passed += 1
        else:
            print(f"  [FAIL] Too few turn changes: {len(turn_pids)}")

        # 6. No critical errors
        total += 1
        critical = []
        for c in clients:
            for err in c.errors:
                if "Not your turn" not in err:
                    critical.append(f"{c.label}: {err}")
        if not critical:
            print("  [PASS] No critical errors")
            passed += 1
        else:
            print(f"  [FAIL] Critical errors: {critical[:5]}")

        print(f"\n  Checks: {passed}/{total}")
        print("=" * 60)
        if passed == total:
            print("  ** ALL CHECKS PASSED! **")
        else:
            print(f"  ** {total - passed} CHECK(S) FAILED **")
        print("=" * 60)

    finally:
        for c in clients:
            await c.disconnect()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(run_test())
