"""TUI library"""
import curses


def agent_menu(stdscr, agents) -> dict[str, str] | None:
    """Display a menu of agents"""
    curses.curs_set(0)
    current_row = 0

    while True:
        stdscr.clear()

        # ---- Header ----
        header = f"{'Index':<10}{'IPAddress':<20}{'Port':<20}{'Hostname':<20}"
        stdscr.addstr(0, 0, header, curses.A_BOLD | curses.A_UNDERLINE)

        
        # ---- Agent list ----
        for item in agents:
            row = item["id"] + 2  # leave space for header
            if item["id"] == current_row:
                prefix = ">"
                attr = curses.A_REVERSE
            else:
                prefix = str(item['id'])
                attr = curses.A_NORMAL

            line = f"{item['id']:<10}{item['ip']:<20}{item['port']:<20}{item['hostname']:<20}"
            stdscr.addstr(row, 0, line, attr)

        key = stdscr.getch()
        if not agents:
            return None
        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(agents) - 1:
            current_row += 1
        elif key in (curses.KEY_ENTER, 10, 13):
            return agents[current_row]
        elif key == 27:  # ESC
            return None

        stdscr.refresh()
