from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import messagebox, simpledialog


WHITE = "white"
BLACK = "black"
EMPTY = "."

LIGHT_SQUARE = "#f0d9b5"
DARK_SQUARE = "#b58863"
SELECTED_SQUARE = "#f6d365"
MOVE_DOT = "#355c7d"
CAPTURE_RING = "#c0392b"
BOARD_EDGE = "#2f3542"

FILES = "abcdefgh"

STARTING_BOARD = [
    list("rnbqkbnr"),
    list("pppppppp"),
    list("........"),
    list("........"),
    list("........"),
    list("........"),
    list("PPPPPPPP"),
    list("RNBQKBNR"),
]

PIECE_SYMBOLS = {
    "K": "\u2654",
    "Q": "\u2655",
    "R": "\u2656",
    "B": "\u2657",
    "N": "\u2658",
    "P": "\u2659",
    "k": "\u265a",
    "q": "\u265b",
    "r": "\u265c",
    "b": "\u265d",
    "n": "\u265e",
    "p": "\u265f",
}


@dataclass(frozen=True)
class Move:
    start: tuple[int, int]
    end: tuple[int, int]
    promotion: str | None = None
    castle: str | None = None
    en_passant: bool = False


def in_bounds(row: int, col: int) -> bool:
    return 0 <= row < 8 and 0 <= col < 8


def piece_color(piece: str) -> str | None:
    if piece == EMPTY:
        return None
    return WHITE if piece.isupper() else BLACK


def opponent(color: str) -> str:
    return BLACK if color == WHITE else WHITE


def square_name(square: tuple[int, int]) -> str:
    row, col = square
    return f"{FILES[col]}{8 - row}"


class ChessGame:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.board = [row[:] for row in STARTING_BOARD]
        self.turn = WHITE
        self.castling_rights = {"K": True, "Q": True, "k": True, "q": True}
        self.en_passant_target: tuple[int, int] | None = None
        self.move_number = 1
        self.history: list[str] = []
        self.undo_stack: list[tuple] = []

    def snapshot(self) -> tuple:
        return (
            [row[:] for row in self.board],
            self.turn,
            self.castling_rights.copy(),
            self.en_passant_target,
            self.move_number,
            self.history[:],
        )

    def restore(self, snapshot: tuple) -> None:
        (
            self.board,
            self.turn,
            self.castling_rights,
            self.en_passant_target,
            self.move_number,
            self.history,
        ) = snapshot

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        self.restore(self.undo_stack.pop())
        return True

    def legal_moves(self) -> list[Move]:
        moves: list[Move] = []
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece != EMPTY and piece_color(piece) == self.turn:
                    moves.extend(self._piece_moves(row, col))
        return [move for move in moves if not self._leaves_king_in_check(move)]

    def push(self, move: Move) -> None:
        before = self.snapshot()
        label = self.describe_move(move)
        self._apply_move(move, advance_turn=True)
        self.undo_stack.append(before)
        self.history.append(label)

    def result_text(self) -> str | None:
        if self.legal_moves():
            return None
        if self.is_in_check(self.turn):
            winner = "White" if self.turn == BLACK else "Black"
            return f"Checkmate. {winner} wins."
        return "Stalemate. Draw."

    def status_text(self) -> str:
        result = self.result_text()
        if result:
            return result
        current = "White" if self.turn == WHITE else "Black"
        if self.is_in_check(self.turn):
            return f"{current} to move. Check."
        return f"{current} to move."

    def describe_move(self, move: Move) -> str:
        piece = self.board[move.start[0]][move.start[1]]
        if move.castle == "kingside":
            move_text = "O-O"
        elif move.castle == "queenside":
            move_text = "O-O-O"
        else:
            target = self.board[move.end[0]][move.end[1]]
            capture = target != EMPTY or move.en_passant
            piece_letter = "" if piece.upper() == "P" else piece.upper()
            separator = "x" if capture else "-"
            move_text = (
                f"{piece_letter}{square_name(move.start)}"
                f"{separator}{square_name(move.end)}"
            )
            if move.promotion:
                move_text += f"={move.promotion}"

        if self.turn == WHITE:
            return f"{self.move_number}. {move_text}"
        return f"{self.move_number}... {move_text}"

    def is_in_check(self, color: str) -> bool:
        king = "K" if color == WHITE else "k"
        for row in range(8):
            for col in range(8):
                if self.board[row][col] == king:
                    return self.is_square_attacked((row, col), opponent(color))
        return True

    def is_square_attacked(self, square: tuple[int, int], by_color: str) -> bool:
        row, col = square

        pawn_direction = -1 if by_color == WHITE else 1
        pawn_row = row - pawn_direction
        pawn = "P" if by_color == WHITE else "p"
        for delta_col in (-1, 1):
            check_col = col + delta_col
            if in_bounds(pawn_row, check_col) and self.board[pawn_row][check_col] == pawn:
                return True

        knight = "N" if by_color == WHITE else "n"
        for delta_row, delta_col in (
            (-2, -1),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 1),
        ):
            check_row = row + delta_row
            check_col = col + delta_col
            if in_bounds(check_row, check_col) and self.board[check_row][check_col] == knight:
                return True

        king = "K" if by_color == WHITE else "k"
        for delta_row in (-1, 0, 1):
            for delta_col in (-1, 0, 1):
                if delta_row == 0 and delta_col == 0:
                    continue
                check_row = row + delta_row
                check_col = col + delta_col
                if in_bounds(check_row, check_col) and self.board[check_row][check_col] == king:
                    return True

        if self._attacked_by_slider(row, col, by_color, [(-1, 0), (1, 0), (0, -1), (0, 1)], {"R", "Q"}):
            return True
        return self._attacked_by_slider(
            row,
            col,
            by_color,
            [(-1, -1), (-1, 1), (1, -1), (1, 1)],
            {"B", "Q"},
        )

    def _attacked_by_slider(
        self,
        row: int,
        col: int,
        by_color: str,
        directions: list[tuple[int, int]],
        attackers: set[str],
    ) -> bool:
        for delta_row, delta_col in directions:
            check_row = row + delta_row
            check_col = col + delta_col
            while in_bounds(check_row, check_col):
                piece = self.board[check_row][check_col]
                if piece != EMPTY:
                    if piece_color(piece) == by_color and piece.upper() in attackers:
                        return True
                    break
                check_row += delta_row
                check_col += delta_col
        return False

    def _piece_moves(self, row: int, col: int) -> list[Move]:
        piece = self.board[row][col]
        kind = piece.upper()
        if kind == "P":
            return self._pawn_moves(row, col)
        if kind == "N":
            return self._knight_moves(row, col)
        if kind == "B":
            return self._slider_moves(row, col, [(-1, -1), (-1, 1), (1, -1), (1, 1)])
        if kind == "R":
            return self._slider_moves(row, col, [(-1, 0), (1, 0), (0, -1), (0, 1)])
        if kind == "Q":
            return self._slider_moves(
                row,
                col,
                [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)],
            )
        if kind == "K":
            return self._king_moves(row, col)
        return []

    def _pawn_moves(self, row: int, col: int) -> list[Move]:
        piece = self.board[row][col]
        color = piece_color(piece)
        assert color is not None
        direction = -1 if color == WHITE else 1
        start_row = 6 if color == WHITE else 1
        final_row = 0 if color == WHITE else 7
        moves: list[Move] = []

        one_row = row + direction
        if in_bounds(one_row, col) and self.board[one_row][col] == EMPTY:
            self._add_pawn_destination(moves, (row, col), (one_row, col), final_row)
            two_row = row + (2 * direction)
            if row == start_row and self.board[two_row][col] == EMPTY:
                moves.append(Move((row, col), (two_row, col)))

        for delta_col in (-1, 1):
            target_row = row + direction
            target_col = col + delta_col
            if not in_bounds(target_row, target_col):
                continue
            target = self.board[target_row][target_col]
            if target != EMPTY and piece_color(target) == opponent(color):
                self._add_pawn_destination(moves, (row, col), (target_row, target_col), final_row)
            elif self.en_passant_target == (target_row, target_col):
                side_piece = self.board[row][target_col]
                if side_piece.upper() == "P" and piece_color(side_piece) == opponent(color):
                    moves.append(Move((row, col), (target_row, target_col), en_passant=True))

        return moves

    def _add_pawn_destination(
        self,
        moves: list[Move],
        start: tuple[int, int],
        end: tuple[int, int],
        final_row: int,
    ) -> None:
        if end[0] == final_row:
            for promotion in ("Q", "R", "B", "N"):
                moves.append(Move(start, end, promotion=promotion))
        else:
            moves.append(Move(start, end))

    def _knight_moves(self, row: int, col: int) -> list[Move]:
        moves: list[Move] = []
        color = piece_color(self.board[row][col])
        for delta_row, delta_col in (
            (-2, -1),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 1),
        ):
            target_row = row + delta_row
            target_col = col + delta_col
            if self._can_land_on(target_row, target_col, color):
                moves.append(Move((row, col), (target_row, target_col)))
        return moves

    def _slider_moves(
        self,
        row: int,
        col: int,
        directions: list[tuple[int, int]],
    ) -> list[Move]:
        moves: list[Move] = []
        color = piece_color(self.board[row][col])
        for delta_row, delta_col in directions:
            target_row = row + delta_row
            target_col = col + delta_col
            while in_bounds(target_row, target_col):
                target = self.board[target_row][target_col]
                if target == EMPTY:
                    moves.append(Move((row, col), (target_row, target_col)))
                else:
                    if piece_color(target) == opponent(color):
                        moves.append(Move((row, col), (target_row, target_col)))
                    break
                target_row += delta_row
                target_col += delta_col
        return moves

    def _king_moves(self, row: int, col: int) -> list[Move]:
        moves: list[Move] = []
        color = piece_color(self.board[row][col])
        for delta_row in (-1, 0, 1):
            for delta_col in (-1, 0, 1):
                if delta_row == 0 and delta_col == 0:
                    continue
                target_row = row + delta_row
                target_col = col + delta_col
                if self._can_land_on(target_row, target_col, color):
                    moves.append(Move((row, col), (target_row, target_col)))
        moves.extend(self._castling_moves(row, col))
        return moves

    def _castling_moves(self, row: int, col: int) -> list[Move]:
        piece = self.board[row][col]
        color = piece_color(piece)
        if color not in (WHITE, BLACK):
            return []
        home_row = 7 if color == WHITE else 0
        if row != home_row or col != 4 or self.is_in_check(color):
            return []

        moves: list[Move] = []
        enemy = opponent(color)
        king_key = "K" if color == WHITE else "k"
        queen_key = "Q" if color == WHITE else "q"
        rook = "R" if color == WHITE else "r"

        if (
            self.castling_rights[king_key]
            and self.board[home_row][7] == rook
            and self.board[home_row][5] == EMPTY
            and self.board[home_row][6] == EMPTY
            and not self.is_square_attacked((home_row, 5), enemy)
            and not self.is_square_attacked((home_row, 6), enemy)
        ):
            moves.append(Move((row, col), (home_row, 6), castle="kingside"))

        if (
            self.castling_rights[queen_key]
            and self.board[home_row][0] == rook
            and self.board[home_row][1] == EMPTY
            and self.board[home_row][2] == EMPTY
            and self.board[home_row][3] == EMPTY
            and not self.is_square_attacked((home_row, 3), enemy)
            and not self.is_square_attacked((home_row, 2), enemy)
        ):
            moves.append(Move((row, col), (home_row, 2), castle="queenside"))

        return moves

    def _can_land_on(self, row: int, col: int, color: str | None) -> bool:
        if not in_bounds(row, col):
            return False
        target = self.board[row][col]
        return target == EMPTY or piece_color(target) == opponent(color)

    def _leaves_king_in_check(self, move: Move) -> bool:
        moving_color = self.turn
        before = self.snapshot()
        self._apply_move(move, advance_turn=False)
        in_check = self.is_in_check(moving_color)
        self.restore(before)
        return in_check

    def _apply_move(self, move: Move, advance_turn: bool) -> None:
        start_row, start_col = move.start
        end_row, end_col = move.end
        piece = self.board[start_row][start_col]
        color = piece_color(piece)
        assert color is not None
        target = self.board[end_row][end_col]

        self._update_castling_rights(piece, move.start, move.end, target)

        self.board[start_row][start_col] = EMPTY
        if move.en_passant:
            self.board[start_row][end_col] = EMPTY

        if move.castle == "kingside":
            self.board[start_row][5] = self.board[start_row][7]
            self.board[start_row][7] = EMPTY
        elif move.castle == "queenside":
            self.board[start_row][3] = self.board[start_row][0]
            self.board[start_row][0] = EMPTY

        placed_piece = piece
        if move.promotion:
            placed_piece = move.promotion if color == WHITE else move.promotion.lower()
        self.board[end_row][end_col] = placed_piece

        self.en_passant_target = None
        if piece.upper() == "P" and abs(end_row - start_row) == 2:
            middle_row = (start_row + end_row) // 2
            self.en_passant_target = (middle_row, start_col)

        if advance_turn:
            if color == BLACK:
                self.move_number += 1
            self.turn = opponent(color)

    def _update_castling_rights(
        self,
        piece: str,
        start: tuple[int, int],
        end: tuple[int, int],
        captured: str,
    ) -> None:
        if piece == "K":
            self.castling_rights["K"] = False
            self.castling_rights["Q"] = False
        elif piece == "k":
            self.castling_rights["k"] = False
            self.castling_rights["q"] = False
        elif piece == "R" and start == (7, 0):
            self.castling_rights["Q"] = False
        elif piece == "R" and start == (7, 7):
            self.castling_rights["K"] = False
        elif piece == "r" and start == (0, 0):
            self.castling_rights["q"] = False
        elif piece == "r" and start == (0, 7):
            self.castling_rights["k"] = False

        if captured == "R" and end == (7, 0):
            self.castling_rights["Q"] = False
        elif captured == "R" and end == (7, 7):
            self.castling_rights["K"] = False
        elif captured == "r" and end == (0, 0):
            self.castling_rights["q"] = False
        elif captured == "r" and end == (0, 7):
            self.castling_rights["k"] = False


class ChessApp(tk.Tk):
    square_size = 72
    board_size = square_size * 8

    def __init__(self) -> None:
        super().__init__()
        self.title("Python Chess")
        self.resizable(False, False)
        self.configure(bg="#f7f7f7")

        self.game = ChessGame()
        self.selected: tuple[int, int] | None = None
        self.selected_moves: list[Move] = []

        self.canvas = tk.Canvas(
            self,
            width=self.board_size,
            height=self.board_size,
            bg=BOARD_EDGE,
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, padx=14, pady=14)
        self.canvas.bind("<Button-1>", self.on_board_click)

        side = tk.Frame(self, bg="#f7f7f7")
        side.grid(row=0, column=1, sticky="n", padx=(0, 14), pady=14)

        self.status_var = tk.StringVar()
        tk.Label(
            side,
            textvariable=self.status_var,
            font=("Segoe UI", 14, "bold"),
            bg="#f7f7f7",
            fg="#202020",
            width=24,
            anchor="w",
        ).pack(anchor="w", pady=(0, 10))

        tk.Label(
            side,
            text="Moves",
            font=("Segoe UI", 10, "bold"),
            bg="#f7f7f7",
            fg="#555555",
            anchor="w",
        ).pack(anchor="w")

        self.history_box = tk.Listbox(
            side,
            width=26,
            height=22,
            font=("Consolas", 10),
            activestyle="none",
            borderwidth=1,
            relief="solid",
        )
        self.history_box.pack(pady=(4, 12))

        button_row = tk.Frame(side, bg="#f7f7f7")
        button_row.pack(anchor="w")
        tk.Button(button_row, text="Undo", command=self.undo_move, width=10).pack(side="left", padx=(0, 8))
        tk.Button(button_row, text="New Game", command=self.new_game, width=10).pack(side="left")

        self.draw()

    def on_board_click(self, event: tk.Event) -> None:
        col = event.x // self.square_size
        row = event.y // self.square_size
        if not in_bounds(row, col):
            return

        if self.game.result_text():
            self.clear_selection()
            return

        clicked = (row, col)
        if self.selected is not None:
            matching_moves = [move for move in self.selected_moves if move.end == clicked]
            if matching_moves:
                move = self.choose_promotion(matching_moves)
                if move is not None:
                    self.game.push(move)
                    self.clear_selection()
                    self.refresh_after_move()
                return

        piece = self.game.board[row][col]
        if piece != EMPTY and piece_color(piece) == self.game.turn:
            self.selected = clicked
            self.selected_moves = [
                move for move in self.game.legal_moves() if move.start == clicked
            ]
        else:
            self.clear_selection()
        self.draw()

    def choose_promotion(self, moves: list[Move]) -> Move | None:
        if len(moves) == 1:
            return moves[0]

        choices = {move.promotion: move for move in moves if move.promotion}
        choice = simpledialog.askstring(
            "Promote pawn",
            "Promote to Q, R, B, or N:",
            initialvalue="Q",
            parent=self,
        )
        if choice is None:
            return None
        promotion = choice.strip().upper()[:1]
        if promotion not in choices:
            messagebox.showinfo("Promotion", "That pawn will promote to a queen.")
            promotion = "Q"
        return choices[promotion]

    def refresh_after_move(self) -> None:
        self.draw()
        self.update_history()
        result = self.game.result_text()
        if result:
            messagebox.showinfo("Game over", result)

    def clear_selection(self) -> None:
        self.selected = None
        self.selected_moves = []

    def undo_move(self) -> None:
        if self.game.undo():
            self.clear_selection()
            self.draw()
            self.update_history()

    def new_game(self) -> None:
        self.game.reset()
        self.clear_selection()
        self.draw()
        self.update_history()

    def update_history(self) -> None:
        self.history_box.delete(0, tk.END)
        for item in self.game.history:
            self.history_box.insert(tk.END, item)
        if self.game.history:
            self.history_box.see(tk.END)

    def draw(self) -> None:
        self.canvas.delete("all")
        target_squares = {move.end for move in self.selected_moves}
        capture_squares = {
            move.end
            for move in self.selected_moves
            if self.game.board[move.end[0]][move.end[1]] != EMPTY or move.en_passant
        }

        for row in range(8):
            for col in range(8):
                x1 = col * self.square_size
                y1 = row * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size
                base_color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
                fill = SELECTED_SQUARE if self.selected == (row, col) else base_color
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=fill)

                label_color = "#6b4d32" if base_color == LIGHT_SQUARE else "#f8ead2"
                if col == 0:
                    self.canvas.create_text(
                        x1 + 8,
                        y1 + 10,
                        text=str(8 - row),
                        fill=label_color,
                        font=("Segoe UI", 8, "bold"),
                    )
                if row == 7:
                    self.canvas.create_text(
                        x2 - 9,
                        y2 - 10,
                        text=FILES[col],
                        fill=label_color,
                        font=("Segoe UI", 8, "bold"),
                    )

        for row, col in target_squares:
            center_x = col * self.square_size + self.square_size // 2
            center_y = row * self.square_size + self.square_size // 2
            if (row, col) in capture_squares:
                radius = 28
                self.canvas.create_oval(
                    center_x - radius,
                    center_y - radius,
                    center_x + radius,
                    center_y + radius,
                    outline=CAPTURE_RING,
                    width=4,
                )
            else:
                radius = 8
                self.canvas.create_oval(
                    center_x - radius,
                    center_y - radius,
                    center_x + radius,
                    center_y + radius,
                    fill=MOVE_DOT,
                    outline=MOVE_DOT,
                )

        for row in range(8):
            for col in range(8):
                piece = self.game.board[row][col]
                if piece == EMPTY:
                    continue
                center_x = col * self.square_size + self.square_size // 2
                center_y = row * self.square_size + self.square_size // 2 + 1
                self.canvas.create_text(
                    center_x + 1,
                    center_y + 2,
                    text=PIECE_SYMBOLS[piece],
                    font=("Segoe UI Symbol", 42),
                    fill="#593d2b",
                )
                self.canvas.create_text(
                    center_x,
                    center_y,
                    text=PIECE_SYMBOLS[piece],
                    font=("Segoe UI Symbol", 42),
                    fill="#111111",
                )

        self.status_var.set(self.game.status_text())


def main() -> None:
    ChessApp().mainloop()


if __name__ == "__main__":
    main()
