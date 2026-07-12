"""Dependency-free local web server for Cairn hotseat and computer play."""

import argparse
from dataclasses import dataclass
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from cairn import BLACK, WHITE, Game, Illegal, has_sky, other
from opponent import DIFFICULTIES, BotDecision, choose_decision


WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
GAME_LOCK = threading.Lock()


@dataclass
class MatchConfig:
    mode: str = "hotseat"
    human_color: str | None = None
    computer_color: str | None = None
    difficulty: str = "standard"
    explain: bool = True
    seed: int = 1
    end_decided: bool = False

    @classmethod
    def from_new_game(cls, game, body):
        mode = body.get("mode", "hotseat")
        if mode not in ("hotseat", "computer"):
            raise ValueError("mode must be hotseat or computer")
        if mode == "hotseat":
            return cls()
        human_color = body.get("human_color", BLACK)
        if human_color not in (BLACK, WHITE):
            raise ValueError("human_color must be B or W")
        difficulty = body.get("difficulty", "standard")
        if difficulty not in DIFFICULTIES:
            raise ValueError("difficulty must be casual or standard")
        explain = body.get("explain", True)
        if not isinstance(explain, bool):
            raise ValueError("explain must be boolean")
        seed = body.get("seed", 1)
        if not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        computer_color = other(human_color)
        game.players = {
            human_color: "You",
            computer_color: "Computer",
        }
        return cls(
            mode="computer",
            human_color=human_color,
            computer_color=computer_color,
            difficulty=difficulty,
            explain=explain,
            seed=seed,
        )

    @classmethod
    def from_snapshot(cls, payload):
        saved = payload.get("computer")
        if saved is None:
            return cls()
        if not isinstance(saved, dict) or not saved.get("enabled", False):
            raise ValueError("invalid computer configuration")
        computer_color = saved.get("color")
        if computer_color not in (BLACK, WHITE):
            raise ValueError("invalid computer color")
        difficulty = saved.get("difficulty", "standard")
        if difficulty not in DIFFICULTIES:
            raise ValueError("invalid computer difficulty")
        explain = saved.get("explain", True)
        seed = saved.get("seed", 1)
        if not isinstance(explain, bool) or not isinstance(seed, int):
            raise ValueError("invalid computer configuration")
        return cls(
            mode="computer",
            human_color=other(computer_color),
            computer_color=computer_color,
            difficulty=difficulty,
            explain=explain,
            seed=seed,
        )

    def computer_can_act(self, game):
        if self.mode != "computer":
            return False
        if game.finished:
            return not self.end_decided
        return game.to_move == self.computer_color

    def swap_owners(self):
        if self.mode == "computer":
            self.human_color = other(self.human_color)
            self.computer_color = other(self.computer_color)

    def snapshot_data(self):
        if self.mode != "computer":
            return None
        return {
            "enabled": True,
            "color": self.computer_color,
            "difficulty": self.difficulty,
            "explain": self.explain,
            "seed": self.seed,
        }


GAME = Game(3)
MATCH = MatchConfig()
LAST_DECISION = None


def snapshot_payload(game, match):
    payload = game.to_dict()
    computer = match.snapshot_data()
    if computer is not None:
        payload["computer"] = computer
    return payload


def load_snapshot(payload):
    return Game.from_dict(payload), MatchConfig.from_snapshot(payload)


def _decision_payload(decision, explain):
    if decision is None:
        return None
    payload = decision.to_dict()
    if not explain:
        payload["reason_text"] = ""
    return payload


def public_view(game, match=None, last_decision=None):
    match = match or MatchConfig()
    legal = set() if game.finished else set(game.legal_placements())
    board = game.board
    points = []
    for point in board.points:
        points.append(
            {
                "coord": list(point),
                "stack": list(game.state[point]),
                "rim": point in board.rim,
                "deep": point in board.deep,
                "legal": point in legal,
                "sky": has_sky(board, game.state, point, None),
            }
        )
    edges = []
    for point in board.points:
        for neighbor in board.neighbors[point]:
            if point < neighbor:
                edges.append([list(point), list(neighbor)])
    return {
        "n": board.n,
        "points": points,
        "edges": edges,
        "to_move": game.to_move,
        "current_player": game.current_player,
        "players": dict(game.players),
        "moves_played": game.moves_played,
        "consecutive_passes": game.consecutive_passes,
        "finished": game.finished,
        "resumption_available": game.finished and not game.resumption_used,
        "resumption_used": game.resumption_used,
        "swap_available": game.swap_available,
        "score": game.score(),
        "capture_waves": [
            [list(point) for point in wave] for wave in game.last_capture_waves
        ],
        "match": {
            "mode": match.mode,
            "human_color": match.human_color,
            "computer_color": match.computer_color,
            "difficulty": match.difficulty,
            "explain": match.explain,
            "computer_turn": (
                match.mode == "computer"
                and not game.finished
                and game.to_move == match.computer_color
            ),
            "computer_can_act": match.computer_can_act(game),
        },
        "computer_decision": _decision_payload(last_decision, match.explain),
    }


def assert_human_action(game, match):
    if match.mode == "computer" and not game.finished:
        if game.to_move == match.computer_color:
            raise Illegal("wait for the computer's move")


def apply_computer_action(game, match):
    if match.mode != "computer":
        raise Illegal("computer opponent is not enabled")
    if not match.computer_can_act(game):
        raise Illegal("it is not the computer's turn")
    decision = choose_decision(
        game,
        match.computer_color,
        difficulty=match.difficulty,
        seed=match.seed,
    )
    if decision.action == "play":
        game.play(decision.point)
    elif decision.action == "pass":
        game.play_pass()
    elif decision.action == "swap":
        game.take_over()
        match.swap_owners()
    elif decision.action == "resume":
        game.demand_resumption()
    elif decision.action == "accept":
        match.end_decided = True
    else:
        raise ValueError("unsupported computer action")
    return decision


class CairnHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def _json(self, payload, status=200):
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("invalid JSON body") from exc

    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/api/state":
            with GAME_LOCK:
                self._json(public_view(GAME, MATCH, LAST_DECISION))
            return
        if route == "/api/snapshot":
            with GAME_LOCK:
                self._json(snapshot_payload(GAME, MATCH))
            return
        super().do_GET()

    def do_POST(self):
        global GAME, MATCH, LAST_DECISION
        route = urlparse(self.path).path
        try:
            body = self._body()
            with GAME_LOCK:
                if route == "/api/new":
                    n = int(body.get("n", 3))
                    if n not in (3, 4, 5):
                        raise ValueError("board size must be 3, 4, or 5")
                    game = Game(n)
                    names = body.get("players", {})
                    if names and body.get("mode", "hotseat") == "hotseat":
                        for color in (BLACK, WHITE):
                            name = names.get(color)
                            if not isinstance(name, str) or not name.strip():
                                raise ValueError("both player names are required")
                            game.players[color] = name.strip()[:40]
                    MATCH = MatchConfig.from_new_game(game, body)
                    GAME = game
                    LAST_DECISION = None
                elif route == "/api/play":
                    assert_human_action(GAME, MATCH)
                    raw = body.get("point")
                    if not isinstance(raw, list) or len(raw) != 2:
                        raise ValueError("point must be [x,y]")
                    point = (int(raw[0]), int(raw[1]))
                    if point not in GAME.state:
                        raise ValueError("point is off board")
                    GAME.play(point)
                    MATCH.end_decided = False
                elif route == "/api/pass":
                    assert_human_action(GAME, MATCH)
                    GAME.play_pass()
                elif route == "/api/swap":
                    assert_human_action(GAME, MATCH)
                    GAME.take_over()
                    MATCH.swap_owners()
                elif route == "/api/resume":
                    assert_human_action(GAME, MATCH)
                    GAME.demand_resumption()
                    MATCH.end_decided = False
                elif route == "/api/computer":
                    LAST_DECISION = apply_computer_action(GAME, MATCH)
                elif route == "/api/load":
                    GAME, MATCH = load_snapshot(body)
                    LAST_DECISION = None
                else:
                    self._json({"error": "unknown API route"}, 404)
                    return
                self._json(public_view(GAME, MATCH, LAST_DECISION))
        except (Illegal, ValueError, TypeError) as exc:
            self._json({"error": str(exc)}, 400)

    def log_message(self, format, *args):
        print(f"[cairn] {self.address_string()} {format % args}")


def main():
    parser = argparse.ArgumentParser(description="Run the local Cairn web game")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), CairnHandler)
    print(f"Cairn ready at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
