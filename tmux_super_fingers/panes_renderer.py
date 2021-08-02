import re
from typing import List, Optional
from copy import deepcopy
from curses import ascii

from .pane import Pane
from .mark import Highlight, Mark
from .ui import UI
from .utils import flatten


class BreakTheLoop(Exception):
    pass


class PanesRenderer:
    """Renders panes with marks and handles user_input"""

    def __init__(self, ui: UI, panes: List[Pane]):
        self.ui = ui
        self.panes = panes

    def loop(self) -> None:
        user_input = ''

        while True:
            panes = self._discard_marks_that_dont_match_user_input(user_input)

            if user_input:
                chosen_mark = self._the_only_mark_left(panes)

                if chosen_mark:
                    chosen_mark.perform_primary_action()
                    break

            for pane in panes:
                self._render_pane_text(pane)
                self._overlay_marks(pane, user_input)

            self.ui.refresh()

            try:
                user_input = self._handle_user_input(user_input)
            except BreakTheLoop:
                break

    def _handle_user_input(self, user_input: str) -> str:
        char = self.ui.getch()

        if char == ascii.ESC:
            raise BreakTheLoop

        # backspace (ascii.BS does not work for some reason)
        if char == 127:
            if user_input:
                user_input = user_input[:-1]
            else:
                raise BreakTheLoop
        else:
            user_input += chr(char)

        return user_input

    def _the_only_mark_left(self, panes: List[Pane]) -> Optional[Mark]:
        marks_left = flatten([
            [m for m in p.marks] for p in panes
        ])

        if len(marks_left) == 1:
            return marks_left[0]

    def _discard_marks_that_dont_match_user_input(self, user_input: str) -> List[Pane]:
        panes = deepcopy(self.panes)

        for pane in panes:
            pane.marks = [
                m for m in pane.marks if m.hint and m.hint.startswith(user_input)
            ]

        return panes

    def _render_top_border(self, pane: Pane) -> None:
        pane_width = pane.right - pane.left + 1
        self.ui.render_line(pane.top - 1, pane.left, '─' * pane_width, self.ui.DIM)

    def _render_left_border(self, pane: Pane) -> None:
        pane_height = pane.bottom - pane.top + 1
        for ln in range(pane_height):
            self.ui.render_line(pane.top + ln, pane.left - 1, '│', self.ui.DIM)

    def _render_pane_text(self, pane: Pane) -> None:
        if pane.top > 0:
            self._render_top_border(pane)

        if pane.left > 0:
            self._render_left_border(pane)

        lines = pane.text.split('\n')
        for ln, line in enumerate(lines):
            self.ui.render_line(pane.top + ln, pane.left, line, self.ui.DIM)

    def _overlay_marks(self, pane: Pane, user_input: str) -> None:
        running_character_total = 0
        wrapped_mark_tail = None

        for ln, line in enumerate(pane.text.split('\n')):
            line_start = running_character_total
            running_character_total += len(line)
            line_end = running_character_total

            highlights_that_start_on_current_line: List[Highlight] = [
                m for m in pane.marks if line_end > m.start >= line_start
            ]

            if wrapped_mark_tail:
                highlights_that_start_on_current_line = [
                    wrapped_mark_tail] + highlights_that_start_on_current_line

            for highlight in highlights_that_start_on_current_line:
                mark_line_start = highlight.start - line_start
                text = highlight.text

                if highlight.end > line_end:
                    tail_length = highlight.end - line_end
                    wrapped_mark_tail = Highlight(
                        text=text[-tail_length:],
                        start=line_end,
                    )
                    text = text[:-tail_length]
                else:
                    wrapped_mark_tail = None

                self.ui.render_line(
                    pane.top + ln,
                    pane.left + mark_line_start,
                    text,
                    self.ui.BOLD
                )

                if isinstance(highlight, Mark):
                    mark = highlight
                    if mark.hint:
                        hint = re.sub(f'^{user_input}', '', mark.hint)

                        if hint:
                            self.ui.render_line(
                                pane.top + ln,
                                pane.left + mark_line_start + len(user_input),
                                hint,
                                self.ui.BLACK_ON_CYAN | self.ui.BOLD
                            )