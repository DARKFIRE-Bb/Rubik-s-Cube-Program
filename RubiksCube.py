"""Play with a virtual Rubik's Cube in the terminal."""

import os
import json
import random
import re
import sys
import time
from pathlib import Path


# Each face is described from the viewpoint of someone looking directly at it.
# The right/up vectors also define how its rows and columns appear in the net.
FACE_GEOMETRY = {
    "U": ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
    "D": ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
    "F": ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    "B": ((0, 0, -1), (-1, 0, 0), (0, 1, 0)),
    "R": ((1, 0, 0), (0, 0, -1), (0, 1, 0)),
    "L": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
}
FACE_COLORS = {
    "U": "W",
    "D": "Y",
    "F": "G",
    "B": "B",
    "R": "R",
    "L": "O",
}
FACE_ORDER = ("U", "D", "L", "R", "F", "B")
FACE_MOVE_PATTERN = re.compile(r"([UDLRFB])([2']?)", re.IGNORECASE)
WIDE_MOVE_PATTERN = re.compile(r"([UDLRFB])[wW]([2']?)", re.IGNORECASE)
SLICE_MOVE_PATTERN = re.compile(r"([MES])([2']?)", re.IGNORECASE)
COLOR_CODES = {
    "W": "\033[107m",
    "Y": "\033[103m",
    "G": "\033[102m",
    "B": "\033[104m",
    "R": "\033[101m",
    "O": "\033[48;5;208m",
}
COLOR_256 = {
    "W": 15,
    "Y": 226,
    "G": 46,
    "B": 21,
    "R": 196,
    "O": 208,
}
COLOR_RESET = "\033[0m"
RENDER_SIZE = 55
SOLVE_STEP_DELAY = 0.25
SOLVE_RECORDS_PATH = Path.home() / ".rubikscube" / "solve_records.json"
FACE_SCREEN_OFFSETS = {
    "U": (4, -6),
    "F": (0, 0),
    "R": (8, 0),
}
ROTATION_AXES = {
    "x": FACE_GEOMETRY["R"][0],
    "y": FACE_GEOMETRY["U"][0],
    "z": FACE_GEOMETRY["F"][0],
}
SLICE_AXES = {
    "M": FACE_GEOMETRY["L"][0],
    "E": FACE_GEOMETRY["D"][0],
    "S": FACE_GEOMETRY["F"][0],
}
ALGORITHM_SHORTCUTS = {
    "insert": (
        "Right F2L insert",
        ("R", "U", "R'", "U'"),
    ),
    "t-perm": (
        "T permutation",
        ("R", "U", "R'", "U'", "R'", "F", "R2", "U'", "R'", "U'", "R", "U", "R'", "F'"),
    ),
    "y-perm": (
        "Y permutation",
        ("F", "R", "U'", "R'", "U'", "R", "U", "R'", "F'", "R", "U", "R'", "U'", "R'", "F", "R", "F'"),
    ),
    "ua-perm": (
        "Ua edge permutation",
        ("R", "U'", "R", "U", "R", "U", "R", "U'", "R'", "U'", "R2"),
    ),
    "ub-perm": (
        "Ub edge permutation",
        ("R2", "U", "R", "U", "R'", "U'", "R'", "U'", "R'", "U", "R'"),
    ),
    "h-perm": (
        "H permutation",
        ("M2", "U", "M2", "U2", "M2", "U", "M2"),
    ),
    "z-perm": (
        "Z permutation",
        ("M'", "U", "M2", "U", "M2", "U", "M'", "U2", "M2"),
    ),
    "aa-perm": (
        "Aa corner permutation",
        ("x", "R'", "U", "R'", "D2", "R", "U'", "R'", "D2", "R2", "x'"),
    ),
    "ab-perm": (
        "Ab corner permutation",
        ("x", "R2", "D2", "R", "U", "R'", "D2", "R", "U'", "R", "x'"),
    ),
    "e-perm": (
        "E corner permutation",
        ("x'", "R", "U'", "R'", "D", "R", "U", "R'", "D'", "R", "U", "R'", "D", "R", "U'", "R'", "D'", "x"),
    ),
    "f-perm": (
        "F permutation",
        ("R'", "U'", "F'", "R", "U", "R'", "U'", "R'", "F", "R2", "U'", "R'", "U'", "R", "U", "R'", "U", "R"),
    ),
    "ja-perm": (
        "Ja adjacent corner swap",
        ("R'", "U", "L'", "U2", "R", "U'", "R'", "U2", "R", "L"),
    ),
    "jb-perm": (
        "Jb adjacent corner swap",
        ("R", "U", "R'", "F'", "R", "U", "R'", "U'", "R'", "F", "R2", "U'", "R'"),
    ),
    "na-perm": (
        "Na diagonal corner swap",
        ("L", "U'", "R", "U2", "L'", "U", "R'", "L", "U'", "R", "U2", "L'", "U", "R'"),
    ),
    "nb-perm": (
        "Nb diagonal corner swap",
        ("R'", "U", "L'", "U2", "R", "U'", "L", "R'", "U", "L'", "U2", "R", "U'", "L"),
    ),
    "ra-perm": (
        "Ra adjacent corner swap",
        ("R", "U", "R'", "F'", "R", "U2", "R'", "U2", "R'", "F", "R", "U", "R", "U2", "R'"),
    ),
    "rb-perm": (
        "Rb adjacent corner swap",
        ("R'", "U2", "R", "U2", "R'", "F", "R", "U", "R'", "U'", "R'", "F'", "R2"),
    ),
    "ga-perm": (
        "Ga permutation",
        ("R2", "U", "R'", "U", "R'", "U'", "R", "U'", "R2", "U'", "D", "R'", "U", "R", "D'"),
    ),
    "gb-perm": (
        "Gb permutation",
        ("R'", "U'", "R", "U", "D'", "R2", "U", "R'", "U", "R", "U'", "R", "U'", "R2", "D"),
    ),
    "gc-perm": (
        "Gc permutation",
        ("R2", "U'", "R", "U'", "R", "U", "R'", "U", "R2", "U", "D'", "R", "U'", "R'", "D"),
    ),
    "gd-perm": (
        "Gd permutation",
        ("R", "U", "R'", "U'", "D", "R2", "U'", "R", "U'", "R'", "U", "R'", "U", "R2", "D'"),
    ),
    "v-perm": (
        "V diagonal corner swap",
        ("R'", "U", "R'", "U'", "y", "R'", "F'", "R2", "U'", "R'", "U", "R'", "F", "R", "F"),
    ),
}
RESERVED_BIND_KEYS = frozenset("udlrfbmesxyzw2'qh?")


def _project(point):
    x, y, z = point
    return round(26 + (x - z) * 8), round(27 + (x + z) * 4 - y * 8 + 4)


def _project_face(point, face):
    x, y = _project(point)
    offset_x, offset_y = FACE_SCREEN_OFFSETS[face]
    return x + offset_x, y + offset_y


def _point_in_polygon(x, y, polygon):
    inside = False
    previous_x, previous_y = polygon[-1]
    for current_x, current_y in polygon:
        if (current_y > y) != (previous_y > y):
            crossing_x = (previous_x - current_x) * (y - current_y) / (
                previous_y - current_y
            ) + current_x
            if x < crossing_x:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


def _dot(left, right):
    return sum(a * b for a, b in zip(left, right))


def _cross(left, right):
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _rotate_clockwise(vector, axis):
    """Rotate a vector 90 degrees clockwise when viewed along the face normal."""
    cross = _cross(axis, vector)
    parallel = _dot(axis, vector)
    return tuple(axis[i] * parallel - cross[i] for i in range(3))


def _cell_position(face, row, column):
    normal, right, up = FACE_GEOMETRY[face]
    return tuple(
        normal[i] + (column - 1) * right[i] + (1 - row) * up[i]
        for i in range(3)
    )


CELL_LOOKUP = {
    (_cell_position(face, row, column), FACE_GEOMETRY[face][0]): (
        face,
        row,
        column,
    )
    for face in FACE_ORDER
    for row in range(3)
    for column in range(3)
}


class Cube:
    """A 3x3 cube whose faces contain single-letter color labels."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Return the cube to its solved state."""
        self.faces = {
            face: [[FACE_COLORS[face]] * 3 for _ in range(3)]
            for face in FACE_ORDER
        }

    def turn(self, move):
        """Apply one parsed face move (for example, R, U', or F2)."""
        match = FACE_MOVE_PATTERN.fullmatch(move)
        if match is None:
            raise ValueError(f"Invalid move: {move}")

        face = match.group(1).upper()
        suffix = match.group(2)
        turns = 2 if suffix == "2" else (3 if suffix == "'" else 1)
        axis = FACE_GEOMETRY[face][0]
        self._turn_layers(axis, lambda position: _dot(position, axis) == 1, turns)

    def turn_wide(self, move):
        """Apply a wide turn such as Rw, rotating outer and middle layers."""
        match = WIDE_MOVE_PATTERN.fullmatch(move)
        if match is None:
            raise ValueError(f"Invalid wide move: {move}")

        face = match.group(1).upper()
        suffix = match.group(2)
        turns = 2 if suffix == "2" else (3 if suffix == "'" else 1)
        axis = FACE_GEOMETRY[face][0]
        self._turn_layers(axis, lambda position: _dot(position, axis) >= 0, turns)

    def turn_slice(self, move):
        """Apply a middle-slice move using standard M, E, and S directions."""
        match = SLICE_MOVE_PATTERN.fullmatch(move)
        if match is None:
            raise ValueError(f"Invalid slice move: {move}")

        slice_name = match.group(1).upper()
        suffix = match.group(2)
        turns = 2 if suffix == "2" else (3 if suffix == "'" else 1)
        axis = SLICE_AXES[slice_name]
        self._turn_layers(axis, lambda position: _dot(position, axis) == 0, turns)

    def _turn_layers(self, axis, includes_position, turns):
        for _ in range(turns):
            updated = {
                name: [row[:] for row in grid] for name, grid in self.faces.items()
            }
            for source_face in FACE_ORDER:
                for row in range(3):
                    for column in range(3):
                        position = _cell_position(source_face, row, column)
                        normal = FACE_GEOMETRY[source_face][0]
                        if includes_position(position):
                            position = _rotate_clockwise(position, axis)
                            normal = _rotate_clockwise(normal, axis)
                        target_face, target_row, target_column = CELL_LOOKUP[
                            (position, normal)
                        ]
                        updated[target_face][target_row][target_column] = self.faces[
                            source_face
                        ][row][column]
            self.faces = updated

    def apply_moves(self, moves):
        for move in moves:
            if move[0] in ROTATION_AXES:
                self.rotate(move)
            elif move[0].upper() in "MES":
                move = move.upper()
                self.turn_slice(move)
            elif "w" in move.casefold():
                self.turn_wide(move)
            else:
                self.turn(move.upper())

    def solve(self):
        """Return a solution for the current sticker state, independent of move history."""
        if self.is_solved():
            return []

        try:
            from rubik_solver import utils as rubik_solver_utils
            from rubik_solver.CubieCube import (
                DupedCorner,
                DupedEdge,
                FlipError,
                ParityError,
                TwistError,
            )
            from rubik_solver.Solver.Kociemba.Search import (
                DupedFacelet,
                NoSolution,
                SolverTimeoutError,
            )
        except ImportError as error:
            raise RuntimeError(
                "The solver dependency is missing. Install it with "
                "'python -m pip install --no-deps -r requirements.txt'."
            ) from error

        color_to_face = {self.faces[face][1][1]: face for face in FACE_ORDER}
        if len(color_to_face) != len(FACE_ORDER):
            raise ValueError("The cube must have six distinct center colors.")
        stickers = [
            color for face in FACE_ORDER for row in self.faces[face] for color in row
        ]
        if set(stickers) != set(color_to_face) or any(
            stickers.count(color) != 9 for color in color_to_face
        ):
            raise ValueError("The cube must contain nine stickers of each center color.")
        face_to_solver_color = {
            "U": "y",
            "L": "b",
            "F": "r",
            "R": "g",
            "B": "o",
            "D": "w",
        }

        facelets = "".join(
            face_to_solver_color[color_to_face[color]]
            for face in ("U", "L", "F", "R", "B", "D")
            for row in self.faces[face]
            for color in row
        )
        try:
            solver_moves = rubik_solver_utils.solve(facelets, "Kociemba")
            return parse_moves(" ".join(str(move) for move in solver_moves))
        except (
            ValueError,
            DupedCorner,
            DupedEdge,
            DupedFacelet,
            FlipError,
            NoSolution,
            ParityError,
            TwistError,
        ) as error:
            raise ValueError(f"Could not solve this cube state: {error}") from error
        except SolverTimeoutError as error:
            raise RuntimeError(f"The cube solver timed out: {error}") from error

    def rotate(self, rotation):
        """Rotate the whole cube using x, y, or z notation."""
        match = re.fullmatch(r"([xyz])([2']?)", rotation)
        if match is None:
            raise ValueError(f"Invalid cube rotation: {rotation}")

        axis = ROTATION_AXES[match.group(1)]
        suffix = match.group(2)
        turns = 2 if suffix == "2" else (3 if suffix == "'" else 1)
        for _ in range(turns):
            updated = {
                face: [[None] * 3 for _ in range(3)]
                for face in FACE_ORDER
            }
            for source_face in FACE_ORDER:
                for row in range(3):
                    for column in range(3):
                        position = _cell_position(source_face, row, column)
                        normal = FACE_GEOMETRY[source_face][0]
                        target = CELL_LOOKUP[
                            (
                                _rotate_clockwise(position, axis),
                                _rotate_clockwise(normal, axis),
                            )
                        ]
                        target_face, target_row, target_column = target
                        updated[target_face][target_row][target_column] = self.faces[
                            source_face
                        ][row][column]
            self.faces = updated

    def is_solved(self):
        return all(
            all(color == grid[0][0] for row in grid for color in row)
            for grid in self.faces.values()
        )

    def _render_cube(self):
        """Draw three offset isometric faces with visible gaps between them."""
        pixels = [[" " for _ in range(RENDER_SIZE)] for _ in range(RENDER_SIZE)]
        for face in ("U", "F", "R"):
            _normal, right, up = FACE_GEOMETRY[face]
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
                    min_x = max(0, min(point[0] for point in corners))
                    max_x = min(RENDER_SIZE - 1, max(point[0] for point in corners))
                    min_y = max(0, min(point[1] for point in corners))
                    max_y = min(RENDER_SIZE - 1, max(point[1] for point in corners))
                    for y in range(min_y, max_y + 1):
                        for x in range(min_x, max_x + 1):
                            if _point_in_polygon(x + 0.5, y + 0.5, corners):
                                pixels[y][x] = "edge"

        for face in ("U", "F", "R"):
            _normal, right, up = FACE_GEOMETRY[face]
            for row in range(3):
                for column in range(3):
                    center = _cell_position(face, row, column)
                    corners = []
                    for right_sign, up_sign in (
                        (-0.38, -0.38),
                        (0.38, -0.38),
                        (0.38, 0.38),
                        (-0.38, 0.38),
                    ):
                        point = tuple(
                            center[index]
                            + right_sign * right[index]
                            + up_sign * up[index]
                            for index in range(3)
                        )
                        corners.append(_project_face(point, face))

                    min_x = max(0, min(point[0] for point in corners))
                    max_x = min(RENDER_SIZE - 1, max(point[0] for point in corners))
                    min_y = max(0, min(point[1] for point in corners))
                    max_y = min(RENDER_SIZE - 1, max(point[1] for point in corners))
                    color = self.faces[face][row][column]
                    for y in range(min_y, max_y + 1):
                        for x in range(min_x, max_x + 1):
                            if _point_in_polygon(x + 0.5, y + 0.5, corners):
                                pixels[y][x] = color

        lines = ["3D view: U top | F front | R right"]
        for y in range(0, RENDER_SIZE, 2):
            rendered_row = []
            for x in range(RENDER_SIZE):
                top_pixel = pixels[y][x]
                bottom_pixel = (
                    pixels[y + 1][x] if y + 1 < RENDER_SIZE else " "
                )
                top = top_pixel if top_pixel not in (" ", "edge") else None
                bottom = (
                    bottom_pixel if bottom_pixel not in (" ", "edge") else None
                )
                if top_pixel == "edge" and bottom_pixel == "edge":
                    rendered_row.append("\033[40m \033[0m")
                elif top_pixel == "edge" and bottom is not None:
                    rendered_row.append(
                        f"\033[38;5;{COLOR_256[bottom]};48;5;0m▄\033[0m"
                    )
                elif bottom_pixel == "edge" and top is not None:
                    rendered_row.append(
                        f"\033[38;5;{COLOR_256[top]};48;5;0m▀\033[0m"
                    )
                elif top is None and bottom is None:
                    rendered_row.append(" ")
                elif top is None:
                    rendered_row.append(f"\033[38;5;{COLOR_256[bottom]}m▄\033[0m")
                elif bottom is None:
                    rendered_row.append(f"\033[38;5;{COLOR_256[top]}m▀\033[0m")
                else:
                    rendered_row.append(
                        f"\033[38;5;{COLOR_256[top]};48;5;{COLOR_256[bottom]}m▀\033[0m"
                    )
            lines.append("".join(rendered_row).rstrip())
        return "\n".join(lines)

    def render(self, color=True, view="cube"):
        """Render a perspective cube or the full unfolded net."""
        if view == "cube" and color:
            return self._render_cube()

        def tile(label):
            if color:
                return f"{COLOR_CODES[label]}   {COLOR_RESET}"
            return f" {label} "

        def render_face_row(row):
            return " ".join(tile(label) for label in row)

        if view not in ("cube", "net"):
            raise ValueError("View must be 'cube' or 'net'.")

        lines = ["       U"]
        lines.extend(f"      {render_face_row(row)}" for row in self.faces["U"])
        lines.append("     L       F       R       B")
        for row in range(3):
            sides = [
                render_face_row(self.faces[face][row])
                for face in ("L", "F", "R", "B")
            ]
            lines.append("   " + " | ".join(sides))
        lines.append("       D")
        lines.extend(f"      {render_face_row(row)}" for row in self.faces["D"])
        return "\n".join(lines)


def parse_moves(text):
    """Parse face, wide, slice, and whole-cube rotation notation."""
    tokens = text.split()
    if not tokens:
        raise ValueError("Enter at least one move.")

    moves = []
    for token in tokens:
        rotation_match = re.fullmatch(r"([xyz])([2']?)", token)
        wide_match = WIDE_MOVE_PATTERN.fullmatch(token)
        face_match = FACE_MOVE_PATTERN.fullmatch(token)
        slice_match = SLICE_MOVE_PATTERN.fullmatch(token)
        match = rotation_match or face_match or wide_match or slice_match
        if match is None:
            raise ValueError(
                f"Invalid move {token!r}. Use U/D/L/R/F/B face turns (case "
                "does not matter), moves such as Rw/Uw for wide turns, M/E/S "
                "slice turns, or x/y/z rotations, optionally followed by ' or 2."
            )
        if rotation_match is not None:
            move = match.group(1) + match.group(2)
        elif wide_match is not None:
            move = match.group(1).upper() + "w" + match.group(2)
        elif face_match is not None:
            move = match.group(1).upper() + match.group(2)
        else:
            move = match.group(1).upper() + match.group(2)
        moves.append(move)
    return moves


def parse_bound_moves(text, keybinds):
    """Parse move notation and expand any user-defined key aliases."""
    moves = []
    for token in text.split():
        binding = keybinds.get(token.casefold())
        moves.extend(binding if binding is not None else parse_moves(token))
    if not moves:
        raise ValueError("Enter at least one move.")
    return moves


def set_keybind(keybinds, key, moves_text):
    """Bind one printable key to a valid move or move sequence."""
    normalized_key = key.casefold()
    if (
        len(key) != 1
        or not key.isascii()
        or not key.isprintable()
        or key.isspace()
        or normalized_key in RESERVED_BIND_KEYS
    ):
        raise ValueError(
            "Choose one printable key that is not part of move notation "
            "and is not reserved for help or quit."
        )
    moves = parse_moves(moves_text)
    keybinds[normalized_key] = moves
    return moves


def print_binds(keybinds):
    """Display the current custom key aliases."""
    print("Custom keybinds (these last for this run):")
    if not keybinds:
        print("  None")
        return
    for key, moves in sorted(keybinds.items()):
        print(f"  {key} -> {' '.join(moves)}")


def print_algorithms():
    """Display the available named algorithm shortcuts and their sequences."""
    print("Available algorithm shortcuts (run with: alg <name>):")
    for name, (description, sequence) in ALGORITHM_SHORTCUTS.items():
        print(f"  {name:<8} {description}: {' '.join(sequence)}")


def apply_algorithm(cube, name):
    """Apply a named algorithm shortcut to a cube."""
    key = name.casefold()
    try:
        _description, sequence = ALGORITHM_SHORTCUTS[key]
    except KeyError as error:
        choices = ", ".join(ALGORITHM_SHORTCUTS)
        raise ValueError(f"Unknown algorithm {name!r}. Available: {choices}") from error
    cube.apply_moves(sequence)


def scramble(cube, length=20):
    """Apply and return a random sequence without consecutive same-face turns."""
    moves = []
    previous_face = None
    suffixes = ("", "'", "2")
    for _ in range(length):
        face = random.choice([face for face in "UDLRFB" if face != previous_face])
        move = face + random.choice(suffixes)
        moves.append(move)
        previous_face = face
    cube.apply_moves(moves)
    return moves


def load_solve_records(path=SOLVE_RECORDS_PATH):
    try:
        with Path(path).open(encoding="utf-8") as records_file:
            records = json.load(records_file)
    except FileNotFoundError:
        return []

    if not isinstance(records, list) or any(
        not isinstance(record, dict)
        or not isinstance(record.get("time"), (int, float))
        or not isinstance(record.get("scramble"), str)
        for record in records
    ):
        raise ValueError("Solve history has an invalid format.")
    return records


def save_solve_record(scramble_moves, elapsed, path=SOLVE_RECORDS_PATH):
    path = Path(path)
    records = load_solve_records(path)
    record = {"time": elapsed, "scramble": " ".join(scramble_moves)}
    records.append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as records_file:
        json.dump(records, records_file, indent=2)
        records_file.write("\n")
    return record


def calculate_averages(records):
    times = [record["time"] for record in records]

    def rolling_average(size):
        if len(times) < size:
            return None
        window = sorted(times[-size:])
        trim = 1 if size < 100 else size // 20
        counted_times = window[trim:-trim]
        return sum(counted_times) / len(counted_times)

    return {
        "ao5": rolling_average(5),
        "ao12": rolling_average(12),
        "ao100": rolling_average(100),
        "all_time": sum(times) / len(times) if times else None,
    }


def format_time(seconds):
    total_centiseconds = round(seconds * 100)
    minutes, remaining_centiseconds = divmod(total_centiseconds, 6000)
    whole_seconds, centiseconds = divmod(remaining_centiseconds, 100)
    return f"{minutes}:{whole_seconds:02}.{centiseconds:02}"


def print_averages(records):
    if not records:
        print("No timed solves recorded yet.")
        return

    averages = calculate_averages(records)
    print("Solve averages (trimmed rolling averages):")
    for label, key, required in (
        ("Average of 5", "ao5", 5),
        ("Average of 12", "ao12", 12),
        ("Average of 100", "ao100", 100),
    ):
        average = averages[key]
        result = format_time(average) if average is not None else f"N/A (need {required})"
        print(f"  {label}: {result}")
    print(f"  All-time average: {format_time(averages['all_time'])}")


def print_help():
    print(
        "MOVES\n"
        "  Enter turns separated by spaces, for example: R U R' U'\n"
        "  Faces: U up, D down, L left, R right, F front, B back\n"
        "  Uppercase and lowercase face turns are the same.\n"
        "  Wide turns use w: Rw, Uw, Lw. Slices: M, E, S.\n"
        "  Rotate the whole cube with x, y, or z. Turns follow the current view.\n"
        "  Add ' for a counterclockwise turn or 2 for a half-turn.\n"
        "  Custom keys can be added with: bind <key> <move sequence>\n"
        "\n"
        "ALGORITHMS\n"
        "  Type algorithms to list shortcuts, then alg <name> to run one.\n"
        "\n"
        "DISPLAY\n"
        "  The 3D view shows the top, front, and right faces.\n"
        "  Type net to show all six faces, or cube to return to 3D view.\n"
        "  Tile colors: white, yellow, green, blue, red, orange.\n"
        "\n"
        "COMMANDS\n"
        "  help          Show this help\n"
        "  algorithms    List algorithm shortcuts\n"
        "  alg <name>    Run an algorithm shortcut\n"
        "  scramble      Randomize the cube\n"
        "  timed         Start a timed solve with a fresh scramble\n"
        "  average       Show Ao5, Ao12, Ao100, and all-time average\n"
        "  solve         Solve the current cube from its sticker state\n"
        "  bind <key> <moves>  Bind a key to one move or a move sequence\n"
        "  binds         Show custom keybinds\n"
        "  reset binds   Remove custom keybinds\n"
        "  net / cube    Change the display view\n"
        "  quit          Exit the program"
    )


def _solved_banner(color):
    border = "+" + "-" * 38 + "+"
    title = "|" + "THE CUBE IS SOLVED!".center(38) + "|"
    if color:
        return "\n".join(
            (
                f"\033[38;5;208m{border}{COLOR_RESET}",
                f"\033[38;5;226m{title}{COLOR_RESET}",
                f"\033[38;5;46m{border}{COLOR_RESET}",
            )
        )
    return "\n".join((border, title, border))


def main():
    cube = Cube()
    display = "cube"
    timed_attempt = None
    keybinds = {}
    print("Virtual Rubik's Cube")
    print_help()

    def finish_timed_attempt():
        nonlocal timed_attempt
        if timed_attempt is None or not cube.is_solved():
            return

        elapsed = time.perf_counter() - timed_attempt["started_at"]
        try:
            save_solve_record(
                timed_attempt["scramble"], elapsed, SOLVE_RECORDS_PATH
            )
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"Solved in {format_time(elapsed)}, but the result was not saved: {error}")
        else:
            print(f"Timed solve: {format_time(elapsed)}. Result saved.")
        timed_attempt = None

    while True:
        print()
        use_color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
        print(cube.render(color=use_color, view=display))
        if cube.is_solved():
            print(f"\n{_solved_banner(use_color)}")

        try:
            entry = input("\nMove(s) or command: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        command = entry.casefold()
        if command in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if command in ("help", "h", "?"):
            print_help()
            continue
        if command == "binds":
            print_binds(keybinds)
            continue
        if command == "reset binds":
            keybinds.clear()
            print("Custom keybinds reset.")
            continue
        if command == "bind" or command.startswith("bind "):
            parts = entry.split(maxsplit=2)
            if len(parts) != 3:
                print("Usage: bind <key> <move sequence>")
                continue
            try:
                moves = set_keybind(keybinds, parts[1], parts[2])
            except ValueError as error:
                print(error)
            else:
                print(f"Bound {parts[1]} to {' '.join(moves)}.")
            continue
        if command == "algorithms":
            print_algorithms()
            continue
        if command.startswith("alg "):
            name = command[4:].strip()
            if not name:
                print("Usage: alg <name>. Type algorithms to list shortcuts.")
                continue
            try:
                apply_algorithm(cube, name)
            except ValueError as error:
                print(error)
            finish_timed_attempt()
            continue
        if command == "timed":
            if timed_attempt is not None:
                print("A timed solve is already active.")
                continue
            if not cube.is_solved():
                print("Solve the current cube before starting a timed solve.")
                continue
            scramble_moves = scramble(cube)
            timed_attempt = {
                "scramble": scramble_moves,
                "started_at": time.perf_counter(),
            }
            print("Timed solve started. Scramble:", " ".join(scramble_moves))
            continue
        if command == "average":
            try:
                print_averages(load_solve_records(SOLVE_RECORDS_PATH))
            except (OSError, ValueError, json.JSONDecodeError) as error:
                print(f"Could not read solve history: {error}")
            continue
        if command == "solve":
            if timed_attempt is not None:
                timed_attempt = None
                print("Timed solve canceled; result not recorded.")
            try:
                solution = cube.solve()
            except (RuntimeError, ValueError) as error:
                print(error)
                continue
            for move_count, move in enumerate(solution, start=1):
                cube.apply_moves([move])
                print(f"Solving... {move_count}/{len(solution)}: {move}")
                print(cube.render(color=use_color, view=display))
                if move_count < len(solution):
                    time.sleep(SOLVE_STEP_DELAY)
            if not solution:
                print("The cube is already solved.")
            continue
        if command == "net":
            display = "net"
            continue
        if command == "cube":
            display = "cube"
            continue
        if command == "scramble":
            if timed_attempt is not None:
                timed_attempt = None
                print("Timed solve canceled; result not recorded.")
            moves = scramble(cube)
            print("Scramble:", " ".join(moves))
            continue
        if not entry:
            continue

        try:
            for move in parse_bound_moves(entry, keybinds):
                cube.apply_moves([move])
                finish_timed_attempt()
        except ValueError as error:
            print(error)


if __name__ == "__main__":
    main()