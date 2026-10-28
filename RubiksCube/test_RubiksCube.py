import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from RubiksCube import (
    Cube,
    FACE_GEOMETRY,
    FACE_SCREEN_OFFSETS,
    RENDER_SIZE,
    ALGORITHM_SHORTCUTS,
    _cell_position,
    _project,
    _project_face,
    apply_algorithm,
    calculate_averages,
    load_solve_records,
    parse_moves,
    print_algorithms,
    main,
    save_solve_record,
    _solved_banner,
)


class CubeTests(unittest.TestCase):
    def test_each_face_turn_four_times_returns_to_solved(self):
        for face in "UDLRFB":
            with self.subTest(face=face):
                cube = Cube()
                cube.apply_moves([face] * 4)
                self.assertTrue(cube.is_solved())

    def test_turn_and_inverse_restore_cube(self):
        for face in "UDLRFB":
            with self.subTest(face=face):
                cube = Cube()
                cube.apply_moves([face, face + "'"])
                self.assertTrue(cube.is_solved())

    def test_clockwise_up_turn_rotates_top_face_clockwise(self):
        cube = Cube()
        cube.faces["U"] = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
        ]

        cube.turn("U")

        self.assertEqual(
            cube.faces["U"],
            [["7", "4", "1"], ["8", "5", "2"], ["9", "6", "3"]],
        )

    def test_move_sequence_and_half_turn(self):
        cube = Cube()
        moves = parse_moves("rw U2 f'")
        self.assertEqual(moves, ["Rw", "U2", "F'"])
        cube.apply_moves(moves)
        cube.apply_moves(["F", "U2", "Rw'"])
        self.assertTrue(cube.is_solved())

    def test_solve_step_undoes_one_move_at_a_time(self):
        cube = Cube()
        cube.apply_moves(parse_moves("R U2 F'"))

        self.assertEqual(cube.solve_step(), "F")
        self.assertFalse(cube.is_solved())
        self.assertEqual(cube.solve_step(), "U2")
        self.assertFalse(cube.is_solved())
        self.assertEqual(cube.solve_step(), "R'")
        self.assertTrue(cube.is_solved())
        self.assertIsNone(cube.solve_step())

    def test_slice_moves_and_inverses_restore_cube(self):
        for move in "MES":
            with self.subTest(move=move):
                cube = Cube()
                cube.apply_moves([move, move + "'"])
                self.assertEqual(cube.faces, Cube().faces)

        for move in "mes":
            with self.subTest(move=move):
                cube = Cube()
                cube.apply_moves([move, move + "'"])
                self.assertEqual(cube.faces, Cube().faces)

    def test_parse_moves_accepts_lowercase_slice_moves(self):
        self.assertEqual(parse_moves("m e s M E S"), ["M", "E", "S"] * 2)

    def test_slice_moves_return_to_original_after_four_turns(self):
        for move in "MES":
            with self.subTest(move=move):
                cube = Cube()
                cube.apply_moves([move] * 4)
                self.assertEqual(cube.faces, Cube().faces)

    def test_wide_right_turn_is_outer_right_plus_inverse_middle(self):
        wide = Cube()
        equivalent = Cube()

        wide.apply_moves(parse_moves("rw"))
        equivalent.apply_moves(["R", "M'"])

        self.assertEqual(wide.faces, equivalent.faces)

    def test_uppercase_and_lowercase_face_turns_are_identical(self):
        for face in "UDLRFB":
            with self.subTest(face=face):
                upper = Cube()
                lower = Cube()
                upper.apply_moves(parse_moves(face))
                lower.apply_moves(parse_moves(face.lower()))
                self.assertEqual(upper.faces, lower.faces)

    def test_wide_notation_requires_w_suffix(self):
        wide = Cube()
        outer = Cube()

        wide.apply_moves(parse_moves("rw"))
        outer.apply_moves(parse_moves("r"))
        self.assertNotEqual(wide.faces, outer.faces)
        self.assertEqual(parse_moves("rw Uw lw"), ["Rw", "Uw", "Lw"])

    def test_parse_moves_rejects_invalid_tokens(self):
        with self.assertRaises(ValueError):
            parse_moves("R X")

    def test_render_supports_colored_tiles_and_letter_fallback(self):
        cube = Cube()

        colored = cube.render()
        plain = cube.render(color=False, view="net")

        self.assertIn("\033[", colored)
        self.assertIn(" W ", plain)
        self.assertNotIn("\033[", plain)

    def test_cube_view_shows_three_faces_and_net_shows_all_faces(self):
        cube = Cube()

        perspective = cube.render()
        net = cube.render(color=False, view="net")

        self.assertIn("3D view: U top | F front | R right", perspective)
        self.assertIn("\033[", perspective)
        self.assertIn("L       F       R       B", net)
        self.assertIn("       U", net)
        self.assertIn("L       F       R       B", net)
        self.assertIn("       D", net)

    def test_visible_cube_face_stickers_fit_inside_projection(self):
        for face in ("U", "F", "R"):
            _normal, right, up = FACE_GEOMETRY[face]
            projected_centers = set()
            for row in range(3):
                for column in range(3):
                    center = _cell_position(face, row, column)
                    corners = [
                        _project_face(
                            tuple(
                                center[index]
                                + right_sign * right[index]
                                + up_sign * up[index]
                                for index in range(3)
                            ),
                            face,
                        )
                        for right_sign, up_sign in (
                            (-0.5, -0.5),
                            (0.5, -0.5),
                            (0.5, 0.5),
                            (-0.5, 0.5),
                        )
                    ]
                    self.assertTrue(
                        all(
                            0 <= x < RENDER_SIZE and 0 <= y < RENDER_SIZE
                            for x, y in corners
                        )
                    )
                    projected_centers.add(_project_face(center, face))
            self.assertEqual(len(projected_centers), 9)

    def test_perspective_renderer_draws_dark_sticker_seams(self):
        rendered = Cube().render()
        self.assertIn("\033[38;5;15;48;5;0m▀", rendered)
        self.assertIn("\033[38;5;46;48;5;0m▀", rendered)
        self.assertIn(";48;5;0m", rendered)

    def test_perspective_faces_are_separated_on_screen(self):
        point = (0, 1, 0)
        base_x, base_y = _project(point)

        self.assertEqual(FACE_SCREEN_OFFSETS["U"], (4, -6))
        self.assertEqual(FACE_SCREEN_OFFSETS["R"], (8, 0))
        self.assertEqual(
            _project_face(point, "U"),
            (
                base_x + FACE_SCREEN_OFFSETS["U"][0],
                base_y + FACE_SCREEN_OFFSETS["U"][1],
            ),
        )
        self.assertEqual(_project_face(point, "F"), (base_x, base_y))
        self.assertEqual(
            _project_face(point, "R"),
            (
                base_x + FACE_SCREEN_OFFSETS["R"][0],
                base_y + FACE_SCREEN_OFFSETS["R"][1],
            ),
        )

    def test_whole_cube_rotations_return_to_original_after_four_turns(self):
        for rotation in "xyz":
            with self.subTest(rotation=rotation):
                cube = Cube()
                cube.apply_moves([rotation] * 4)
                self.assertEqual(cube.faces, Cube().faces)

    def test_cube_rotation_moves_face_colors_and_inverse_restores_cube(self):
        for rotation in "xyz":
            with self.subTest(rotation=rotation):
                cube = Cube()
                cube.rotate(rotation)
                self.assertNotEqual(cube.faces, Cube().faces)
                cube.rotate(rotation + "'")
                self.assertEqual(cube.faces, Cube().faces)

    def test_parse_moves_accepts_cube_rotations(self):
        self.assertEqual(parse_moves("R x y' z2 F"), ["R", "x", "y'", "z2", "F"])

    def test_right_turn_tracks_current_view_after_cube_rotation(self):
        viewed_turn = Cube()
        viewed_turn.apply_moves(["y", "R", "y'"])

        original_back_turn = Cube()
        original_back_turn.turn("B")

        self.assertEqual(viewed_turn.faces, original_back_turn.faces        )

    def test_algorithm_shortcuts_match_their_sequences(self):
        for name, (_description, sequence) in ALGORITHM_SHORTCUTS.items():
            with self.subTest(name=name):
                shortcut_cube = Cube()
                sequence_cube = Cube()
                apply_algorithm(shortcut_cube, name.upper())
                sequence_cube.apply_moves(sequence)
                self.assertEqual(shortcut_cube.faces, sequence_cube.faces)

    def test_all_21_pll_shortcuts_are_available(self):
        pll_names = {name for name in ALGORITHM_SHORTCUTS if name.endswith("-perm")}
        self.assertEqual(
            pll_names,
            {
                "aa-perm", "ab-perm", "e-perm", "f-perm",
                "ga-perm", "gb-perm", "gc-perm", "gd-perm",
                "h-perm", "ja-perm", "jb-perm", "na-perm",
                "nb-perm", "ra-perm", "rb-perm", "t-perm",
                "ua-perm", "ub-perm", "v-perm", "y-perm", "z-perm",
            },
        )

    def test_algorithm_shortcuts_can_be_undone(self):
        for _description, sequence in ALGORITHM_SHORTCUTS.values():
            with self.subTest(sequence=sequence):
                cube = Cube()
                cube.apply_moves(sequence)
                inverse = [
                    move
                    if move.endswith("2")
                    else move[:-1]
                    if move.endswith("'")
                    else move + "'"
                    for move in reversed(sequence)
                ]
                cube.apply_moves(inverse)
                self.assertEqual(cube.faces, Cube().faces)

    def test_pll_shortcuts_preserve_top_orientation_and_first_two_layers(self):
        for name, (_description, sequence) in ALGORITHM_SHORTCUTS.items():
            if not name.endswith("-perm"):
                continue
            with self.subTest(name=name):
                cube = Cube()
                cube.apply_moves(sequence)
                self.assertTrue(all(color == "W" for row in cube.faces["U"] for color in row))
                self.assertTrue(all(color == "Y" for row in cube.faces["D"] for color in row))
                for face in ("F", "B", "L", "R"):
                    center_color = cube.faces[face][1][1]
                    for row in (1, 2):
                        self.assertEqual(cube.faces[face][row], [center_color] * 3)

    def test_algorithm_listing_shows_all_shortcuts(self):
        from io import StringIO
        from contextlib import redirect_stdout

        output = StringIO()
        with redirect_stdout(output):
            print_algorithms()
        for name in ALGORITHM_SHORTCUTS:
            self.assertIn(name, output.getvalue())

    def test_help_lists_algorithm_commands(self):
        from io import StringIO
        from contextlib import redirect_stdout
        from RubiksCube import print_help

        output = StringIO()
        with redirect_stdout(output):
            print_help()
        help_text = output.getvalue()
        self.assertIn("COMMANDS", help_text)
        self.assertIn("  algorithms    List algorithm shortcuts", help_text)
        self.assertIn("  timed         Start a timed solve with a fresh scramble", help_text)
        self.assertIn("  average       Show Ao5, Ao12, Ao100, and all-time average", help_text)
        self.assertIn("  solve         Undo one move toward the solved cube", help_text)
        self.assertNotIn("reset", help_text)
        self.assertIn("ALGORITHMS\n", help_text)
        self.assertIn("\n\nDISPLAY\n", help_text)

    def test_solved_banner_is_colored_when_enabled(self):
        colored = _solved_banner(color=True)
        plain = _solved_banner(color=False)

        self.assertIn("\033[38;5;208m", colored)
        self.assertIn("\033[38;5;226m", colored)
        self.assertIn("THE CUBE IS SOLVED!", plain)
        self.assertNotIn("\033[", plain)
        self.assertNotIn("Six faces aligned", plain)

    def test_solve_records_persist_elapsed_time_and_scramble(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "history" / "solves.json"
            record = save_solve_record(["R", "U'"], 12.34, path)

            self.assertEqual(record, {"time": 12.34, "scramble": "R U'"})
            self.assertEqual(load_solve_records(path), [record])

    def test_averages_use_recent_windows_and_trim_extremes(self):
        records = [
            {"time": float(seconds), "scramble": ""}
            for seconds in range(1, 101)
        ]

        averages = calculate_averages(records)

        self.assertEqual(averages["ao5"], 98.0)
        self.assertEqual(averages["ao12"], 94.5)
        self.assertEqual(averages["ao100"], 50.5)
        self.assertEqual(averages["all_time"], 50.5)

    def test_timed_solve_records_completion_and_its_scramble(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch

        output = StringIO()
        entries = iter(("timed", "U' R'", "average", "q"))

        def fixed_scramble(cube):
            moves = ["R", "U"]
            cube.apply_moves(moves)
            return moves

        with TemporaryDirectory() as directory:
            path = Path(directory) / "solves.json"
            with patch("builtins.input", side_effect=lambda _prompt: next(entries)):
                with patch("RubiksCube.SOLVE_RECORDS_PATH", path):
                    with patch("RubiksCube.scramble", side_effect=fixed_scramble):
                        with patch(
                            "RubiksCube.time.perf_counter", side_effect=(10.0, 13.25)
                        ):
                            with redirect_stdout(output):
                                main()

            self.assertEqual(
                load_solve_records(path),
                [{"time": 3.25, "scramble": "R U"}],
            )

        self.assertIn("Timed solve: 0:03.25. Result saved.", output.getvalue())
        self.assertIn("All-time average: 0:03.25", output.getvalue())

    def test_auto_solve_cancels_timed_attempt_without_recording(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch

        output = StringIO()
        entries = iter(("timed", "solve", "average", "q"))

        def fixed_scramble(cube):
            moves = ["R", "U"]
            cube.apply_moves(moves)
            return moves

        with TemporaryDirectory() as directory:
            path = Path(directory) / "solves.json"
            with patch("builtins.input", side_effect=lambda _prompt: next(entries)):
                with patch("RubiksCube.SOLVE_RECORDS_PATH", path):
                    with patch("RubiksCube.scramble", side_effect=fixed_scramble):
                        with patch("RubiksCube.time.perf_counter", return_value=10.0):
                            with patch("RubiksCube.time.sleep"):
                                with redirect_stdout(output):
                                    main()

            self.assertFalse(path.exists())

        self.assertIn("Timed solve canceled; result not recorded.", output.getvalue())
        self.assertIn("No timed solves recorded yet.", output.getvalue())

    def test_solve_command_shows_each_move_and_intermediate_cube(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch

        output = StringIO()
        entries = iter(("R U", "solve", "q"))
        with patch("builtins.input", side_effect=lambda _prompt: next(entries)):
            with patch("RubiksCube.time.sleep") as sleep:
                with redirect_stdout(output):
                    main()

        rendered = output.getvalue()
        first_move = rendered.index("Solve move 1: U'")
        second_move = rendered.index("Solve move 2: R'")
        self.assertLess(first_move, second_move)
        self.assertIn("THE CUBE IS SOLVED!", rendered[second_move:])
        sleep.assert_called_once_with(0.25)

    def test_unknown_algorithm_reports_available_shortcuts(self):
        with self.assertRaisesRegex(ValueError, "Available:"):
            apply_algorithm(Cube(), "not-a-perm")


if __name__ == "__main__":
    unittest.main()
