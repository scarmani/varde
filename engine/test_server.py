import unittest

from cairn import BLACK, WHITE, Game
from server import public_view


class TestPublicView(unittest.TestCase):
    def test_fresh_view_exposes_playable_geometry(self):
        view = public_view(Game(3))
        self.assertEqual(len(view["points"]), 54)
        self.assertEqual(sum(point["legal"] for point in view["points"]), 54)
        self.assertFalse(view["swap_available"])
        self.assertEqual(view["score"], {BLACK: 0, WHITE: 0})

    def test_opening_exposes_swap_and_identity(self):
        game = Game(3)
        game.play(game.board.points[0])
        view = public_view(game)
        self.assertTrue(view["swap_available"])
        self.assertEqual(view["current_player"], "Player 2")
        game.take_over()
        view = public_view(game)
        self.assertEqual(view["current_player"], "Player 1")
        self.assertEqual(view["players"], {BLACK: "Player 2", WHITE: "Player 1"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
