"""Deterministic rules-action adapter shared by research agents.

The engine remains the sole authority for placement legality.  This layer adds
the identity state needed to represent pie takeover and the two players'
separate first-ending accept/resume decisions without changing saved games.
"""

from dataclasses import dataclass, field

from varde import BLACK, WHITE, Game, Illegal, other, signature


ACTION_ORDER = {
    "swap": 0,
    "extend": 1,
    "play": 2,
    "pass": 3,
    "finish-extension": 4,
    "resume": 5,
    "accept": 6,
}


@dataclass(frozen=True, order=True)
class RulesAction:
    kind: str
    point: tuple | None = None

    def __post_init__(self):
        if self.kind not in ACTION_ORDER:
            raise ValueError("unknown rules action")
        if (self.kind in ("play", "extend")) != (self.point is not None):
            raise ValueError("only play and extend actions contain a point")

    def sort_key(self):
        return (ACTION_ORDER[self.kind], self.point or ())

    def to_dict(self):
        payload = {"action": self.kind}
        if self.point is not None:
            payload["point"] = list(self.point)
        return payload


@dataclass
class RulesState:
    game: Game
    seats: dict = field(
        default_factory=lambda: {BLACK: "seat-black", WHITE: "seat-white"}
    )
    end_acceptances: set = field(default_factory=set)
    end_decider: str | None = None
    accepted: bool = False

    def __post_init__(self):
        if set(self.seats) != {BLACK, WHITE}:
            raise ValueError("rules state requires Black and White seats")
        if len(set(self.seats.values())) != 2:
            raise ValueError("rules state seats must be distinct")
        if self.end_decider not in (None, BLACK, WHITE):
            raise ValueError("invalid end decider")
        if self.game.finished and self.end_decider is None and not self.accepted:
            self.end_decider = self.game.to_move

    @classmethod
    def from_game(cls, game):
        return cls(game.clone())

    def clone(self):
        return RulesState(
            self.game.clone(),
            seats=dict(self.seats),
            end_acceptances=set(self.end_acceptances),
            end_decider=self.end_decider,
            accepted=self.accepted,
        )

    @property
    def terminal(self):
        return self.accepted

    @property
    def actor_color(self):
        if self.terminal:
            return None
        if self.game.finished:
            return self.end_decider
        return self.game.to_move

    @property
    def actor_seat(self):
        color = self.actor_color
        return self.seats[color] if color else None

    def color_for_seat(self, seat):
        for color, identity in self.seats.items():
            if identity == seat:
                return color
        raise ValueError("unknown seat")

    def key(self):
        game = self.game
        return (
            signature(game.board, game.state, game.to_move),
            game.rules,
            game.moves_played,
            game.consecutive_passes,
            game.quiet_moves,
            game.finished,
            game.no_progress_end,
            game.resumption_used,
            game.extension_used,
            tuple(game.extension_points),
            game.swap_decided,
            tuple((color, self.seats[color]) for color in (BLACK, WHITE)),
            tuple(sorted(self.end_acceptances)),
            self.end_decider,
            self.accepted,
        )


def legal_actions(state):
    """Enumerate every legal rules action in a stable order."""
    if state.terminal:
        return ()
    game = state.game
    if game.finished:
        actions = []
        if game.resumption_available:
            actions.append(RulesAction("resume"))
        actions.append(RulesAction("accept"))
        return tuple(actions)

    actions = []
    if game.swap_available:
        actions.append(RulesAction("swap"))
    actions.extend(
        RulesAction("extend", point)
        for point in game.extension_candidates()
    )
    if game.extension_only_turn:
        actions.append(RulesAction("finish-extension"))
    else:
        actions.extend(
            RulesAction("play", point) for point in game.legal_placements()
        )
        if game.moves_played > 0:
            actions.append(RulesAction("pass"))
    return tuple(actions)


def _apply_in_place(state, action, *, validate):
    if validate and action not in legal_actions(state):
        raise Illegal("action is not legal in this rules state")
    game = state.game
    if action.kind == "play":
        game.play(action.point)
        state.end_acceptances.clear()
        state.end_decider = game.to_move if game.finished else None
    elif action.kind == "pass":
        game.play_pass()
        state.end_decider = game.to_move if game.finished else None
    elif action.kind == "swap":
        game.take_over()
        state.seats[BLACK], state.seats[WHITE] = (
            state.seats[WHITE],
            state.seats[BLACK],
        )
    elif action.kind == "extend":
        game.play_extension(action.point)
        state.end_acceptances.clear()
    elif action.kind == "finish-extension":
        game.finish_extensions()
        state.end_acceptances.clear()
        state.end_decider = None
    elif action.kind == "resume":
        game.demand_resumption()
        state.end_acceptances.clear()
        state.end_decider = None
    elif action.kind == "accept":
        seat = state.actor_seat
        state.end_acceptances.add(seat)
        if game.resumption_used or game.no_progress_end:
            state.accepted = True
            state.end_decider = None
        else:
            other_color = other(state.end_decider)
            other_seat = state.seats[other_color]
            if other_seat in state.end_acceptances:
                state.accepted = True
                state.end_decider = None
            else:
                state.end_decider = other_color
    return state


def apply_action(state, action, *, copy=True, validate=True):
    """Apply a legal action, cloning by default so analysis is non-mutating."""
    target = state.clone() if copy else state
    return _apply_in_place(target, action, validate=validate)
