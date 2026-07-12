"""Dependency-free local web server for Cairn hotseat play."""

import argparse
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from cairn import BLACK, WHITE, Game, Illegal, has_sky


WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
GAME_LOCK = threading.Lock()
GAME = Game(3)


def public_view(game):
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
    }


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
                self._json(public_view(GAME))
            return
        if route == "/api/snapshot":
            with GAME_LOCK:
                self._json(GAME.to_dict())
            return
        super().do_GET()

    def do_POST(self):
        global GAME
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
                    if names:
                        for color in (BLACK, WHITE):
                            name = names.get(color)
                            if not isinstance(name, str) or not name.strip():
                                raise ValueError("both player names are required")
                            game.players[color] = name.strip()[:40]
                    GAME = game
                elif route == "/api/play":
                    raw = body.get("point")
                    if not isinstance(raw, list) or len(raw) != 2:
                        raise ValueError("point must be [x,y]")
                    point = (int(raw[0]), int(raw[1]))
                    if point not in GAME.state:
                        raise ValueError("point is off board")
                    GAME.play(point)
                elif route == "/api/pass":
                    GAME.play_pass()
                elif route == "/api/swap":
                    GAME.take_over()
                elif route == "/api/resume":
                    GAME.demand_resumption()
                elif route == "/api/load":
                    GAME = Game.from_dict(body)
                else:
                    self._json({"error": "unknown API route"}, 404)
                    return
                self._json(public_view(GAME))
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
