import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from RubiksCube import Cube, main, parse_bound_moves, print_binds, set_keybind


class KeybindTests(unittest.TestCase):
    def test_keybind_expands_to_a_move_sequence(self):
        keybinds = {}
        set_keybind(keybinds, "v", "R U R' U'")

        self.assertEqual(
            parse_bound_moves("v F", keybinds),
            ["R", "U", "R'", "U'", "F"],
        )

    def test_binding_an_existing_key_replaces_its_sequence(self):
        keybinds = {}
        set_keybind(keybinds, "v", "R")
        set_keybind(keybinds, "v", "U2 F")

        self.assertEqual(parse_bound_moves("v", keybinds), ["U2", "F"])

    def test_original_move_notation_remains_available(self):
        keybinds = {}
        set_keybind(keybinds, "v", "R")

        self.assertEqual(parse_bound_moves("U2 v F'", keybinds), ["U2", "R", "F'"])

    def test_binding_rejects_move_notation_and_command_keys(self):
        for key in ("R", "2", "'", "q", "h", "?", "ab"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    set_keybind({}, key, "R")

    def test_binding_rejects_invalid_move_sequences(self):
        with self.assertRaises(ValueError):
            set_keybind({}, "v", "R X")

    def test_bind_list_and_reset_commands(self):
        output = StringIO()
        with patch(
            "builtins.input",
            side_effect=["bind v R U R'", "binds", "reset binds", "binds", "quit"],
        ):
            with redirect_stdout(output):
                main()

        text = output.getvalue()
        self.assertIn("Bound v to R U R'.", text)
        self.assertIn("v -> R U R'", text)
        self.assertIn("Custom keybinds reset.", text)
        self.assertIn("Custom keybinds (these last for this run):\n  None", text)

    def test_main_applies_moves_from_a_custom_key(self):
        cube = Cube()
        output = StringIO()
        with patch("RubiksCube.Cube", return_value=cube):
            with patch("builtins.input", side_effect=["bind v R U", "v", "quit"]):
                with redirect_stdout(output):
                    main()

        expected = Cube()
        expected.apply_moves(["R", "U"])
        self.assertEqual(cube.faces, expected.faces)

    def test_print_binds_lists_empty_and_populated_bindings(self):
        output = StringIO()
        with redirect_stdout(output):
            print_binds({"v": ["R", "U2"]})

        self.assertIn("v -> R U2", output.getvalue())


if __name__ == "__main__":
    unittest.main()
