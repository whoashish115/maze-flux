import sys, random
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

CELL_SIZE = 25
MIN_GRID = 10
MAX_GRID = 100

def heuristic(a, b):
    return abs(a.x - b.x) + abs(a.y - b.y)

class Cell:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.start = self.end = self.wall = self.path = False
        self.visited = False
        self.parent = None
        self.g = self.h = self.f = 0
        self.is_main_path = False

    def rect(self):
        return QRectF(self.x * CELL_SIZE, self.y * CELL_SIZE, CELL_SIZE, CELL_SIZE)

class MazeWidget(QWidget):
    def __init__(self, width=60, height=34):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.grid_width = width
        self.grid_height = height
        self.grid = [[Cell(x, y) for y in range(self.grid_height)] for x in range(self.grid_width)]
        self.setStyleSheet("background-color: #05080f;")
        self.start = self.end = None
        self.mode = 'wall'
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.path_queue = []
        self.solving = False
        self.mouse_down = False
        self.adding_wall = True
        self.offset = QPoint(0, 0)
        self.dragging = False
        self.solution_path = []
        self.setMinimumSize(width * CELL_SIZE, height * CELL_SIZE)
        self.color_palette = [QColor("#2266cc")]
        self.wall_color_palette = [QColor("#242830")]
        self.theme_colors = {
            'Blue': [QColor("#2266cc")],
            'Red': [QColor("#cc2222")],
            'Purple': [QColor("#9933cc")]
        }
        self.wall_add_mode = None

    def sizeHint(self):
        return QSize(self.grid_width * CELL_SIZE, self.grid_height * CELL_SIZE)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.translate(self.offset)
        for col in self.grid:
            for cell in col:
                if cell.wall:
                    color = self.wall_color_palette[0]
                elif cell.is_main_path:
                    color = self.color_palette[0].lighter(150)
                elif cell.visited:
                    color = self.color_palette[0].darker(140)
                elif cell.path:
                    color = self.color_palette[0].darker(120)
                else:
                    color = QColor("#0e1219")
                painter.fillRect(cell.rect(), color)
                painter.setPen(QColor("#0a0d12"))
                painter.drawRect(cell.rect())

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.start:
            painter.setBrush(QBrush(self.color_palette[0].lighter(130)))
            painter.drawEllipse(self.start.rect().center(), CELL_SIZE // 2 - 2, CELL_SIZE // 2 - 2)
        if self.end:
            painter.setBrush(QBrush(self.color_palette[0].lighter(130)))
            painter.drawEllipse(self.end.rect().center(), CELL_SIZE // 2 - 2, CELL_SIZE // 2 - 2)

        painter.resetTransform()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.MiddleButton:
            self.drag_start = e.position().toPoint()
            self.dragging = True
        else:
            self.mouse_down = True
            self.wall_add_mode = None
            self._edit_cell(e)

    def mouseMoveEvent(self, e):
        if self.dragging:
            self.offset += e.position().toPoint() - self.drag_start
            self.drag_start = e.position().toPoint()
            self.update()
        elif self.mouse_down and self.mode == 'wall':
            self._edit_cell(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.MiddleButton:
            self.dragging = False
        else:
            self.mouse_down = False
            self.wall_add_mode = None

    def _edit_cell(self, e):
        pos = e.position().toPoint() - self.offset
        x, y = int(pos.x()) // CELL_SIZE, int(pos.y()) // CELL_SIZE
        if not (0 <= x < self.grid_width and 0 <= y < self.grid_height): return
        cell = self.grid[x][y]
        if self.mode == 'start':
            if cell.wall: return
            if self.start: self.start.start = False
            self.start = cell
            cell.start = True
        elif self.mode == 'end':
            if cell.wall: return
            if self.end: self.end.end = False
            self.end = cell
            cell.end = True
        elif self.mode == 'wall':
            if self.wall_add_mode is None:
                self.wall_add_mode = not cell.wall
            cell.wall = self.wall_add_mode
        self.update()

    def keyPressEvent(self, e):
        key = e.key()
        if key == Qt.Key.Key_S: self.mode = 'start'
        elif key == Qt.Key.Key_E: self.mode = 'end'
        elif key == Qt.Key.Key_W: self.mode = 'wall'
        elif key == Qt.Key.Key_Space: self.solve()
        elif key == Qt.Key.Key_R: self.generate_solvable_maze()
        elif key == Qt.Key.Key_C: self.clear_all()
        elif key == Qt.Key.Key_Plus or key == Qt.Key.Key_Equal: self.resize_grid(1)
        elif key == Qt.Key.Key_Minus: self.resize_grid(-1)
        elif key == Qt.Key.Key_X: self.stop_solving()
        self.update()

    def stop_solving(self):
        self.timer.stop()
        self.path_queue.clear()
        self.solution_path.clear()
        self.solving = False
        self.update()

    def clear_all(self):
        self.grid = [[Cell(x, y) for y in range(self.grid_height)] for x in range(self.grid_width)]
        self.start = self.end = None
        self.timer.stop()
        self.path_queue.clear()
        self.solution_path.clear()
        self.offset = QPoint(0, 0) 
        self.update()

    def reset_path(self):
        for col in self.grid:
            for cell in col:
                cell.visited = cell.path = cell.is_main_path = False
                cell.parent = None
                cell.g = cell.h = cell.f = 0
        self.timer.stop()
        self.path_queue.clear()
        self.solution_path.clear()
        self.solving = False
        self.update()

    def resize_grid(self, delta):
        new_w = max(MIN_GRID, min(MAX_GRID, self.grid_width + delta * 4))
        new_h = max(MIN_GRID, min(MAX_GRID, self.grid_height + delta * 2))
        self.grid_width, self.grid_height = new_w, new_h
        self.clear_all()
        self.setMinimumSize(new_w * CELL_SIZE, new_h * CELL_SIZE)
        self.updateGeometry()

    def generate_solvable_maze(self):
        self.offset = QPoint(0, 0) 
        while True:
            self.clear_all()
            for col in self.grid:
                for cell in col:
                    if random.random() < 0.3:
                        cell.wall = True
            self.start = self.grid[0][0]
            self.end = self.grid[self.grid_width - 1][self.grid_height - 1]
            self.start.wall = self.end.wall = False
            if self.path_exists():
                break
        self.update()

    def path_exists(self):
        self.reset_path()
        open_set = [self.start]
        visited = set()
        while open_set:
            current = open_set.pop()
            if current == self.end:
                return True
            visited.add(current)
            for neighbor in self.get_neighbors(current):
                if neighbor not in visited and not neighbor.wall:
                    neighbor.parent = current
                    open_set.append(neighbor)
        return False

    def solve(self):
        if not self.start or not self.end: return
        self.reset_path()
        self.start.g = 0
        self.start.h = heuristic(self.start, self.end)
        self.start.f = self.start.h
        open_set = [self.start]
        closed_set = set()
        while open_set:
            current = min(open_set, key=lambda c: c.f)
            if current == self.end:
                path = []
                while current.parent:
                    path.append(current)
                    current = current.parent
                path.reverse()
                self.solution_path = path
                self.timer.start(10)
                return
            open_set.remove(current)
            closed_set.add(current)
            for neighbor in self.get_neighbors(current):
                if neighbor in closed_set or neighbor.wall: continue
                tentative_g = current.g + 1
                if neighbor not in open_set or tentative_g < neighbor.g:
                    neighbor.parent = current
                    neighbor.g = tentative_g
                    neighbor.h = heuristic(neighbor, self.end)
                    neighbor.f = neighbor.g + neighbor.h
                    if neighbor not in open_set:
                        open_set.append(neighbor)
                        self.path_queue.append(neighbor)

    def animate(self):
        if self.path_queue:
            cell = self.path_queue.pop(0)
            if not (cell.start or cell.end):
                cell.visited = True
        elif self.solution_path:
            cell = self.solution_path.pop(0)
            if not (cell.start or cell.end):
                cell.is_main_path = True
        else:
            self.timer.stop()
        self.update()

    def get_neighbors(self, c):
        result = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = c.x + dx, c.y + dy
            if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                result.append(self.grid[nx][ny])
        return result

    def set_theme_color(self, name):
        if name in self.theme_colors:
            self.color_palette = self.theme_colors[name]
            self.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("icon.png"))
        self.setWindowTitle("Maze Flux")
        self.setStyleSheet("color: #ccddee; background: #05080f; font-size: 14px; QScrollBar:vertical { background: #aaa; } QScrollBar::handle:vertical { background: #222; } QScrollBar:horizontal { background: #aaa; } QScrollBar::handle:horizontal { background: #222; }")
        self.maze = MazeWidget()
        scroll = QScrollArea()
        scroll.setWidget(self.maze)
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(scroll)

        self.toolbar = QToolBar("Tools")
        self.toolbar.setIconSize(QSize(22, 22))
        self.toolbar.setMovable(True)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        for name, icon, mode in [
            ("Start", "📍", "start"),
            ("End", "🏋", "end"),
            ("Wall", "🧱", "wall"),
        ]:
            act = QAction(icon + " " + name, self)
            act.triggered.connect(lambda _, m=mode: self.set_mode(m))
            self.toolbar.addAction(act)

        self.toolbar.addSeparator()
        self.toolbar.addAction("🧠 Solve").triggered.connect(self.maze.solve)
        self.toolbar.addAction("🚓 Stop").triggered.connect(self.maze.stop_solving)
        self.toolbar.addAction("🎲 Maze").triggered.connect(self.maze.generate_solvable_maze)
        self.toolbar.addAction("🧹 Clear").triggered.connect(self.maze.clear_all)
        self.toolbar.addSeparator()
        self.toolbar.addAction("➕ Zoom In").triggered.connect(lambda: self.maze.resize_grid(1))
        self.toolbar.addAction("➖ Zoom Out").triggered.connect(lambda: self.maze.resize_grid(-1))

        self.toolbar.addSeparator()
        theme_menu = QMenu("🎨 Theme", self)
        for name in self.maze.theme_colors:
            act = QAction(name, self)
            act.triggered.connect(lambda _, n=name: self.maze.set_theme_color(n))
            theme_menu.addAction(act)
        theme_button = QToolButton()
        theme_button.setText("🎨 Theme")
        theme_button.setMenu(theme_menu)
        theme_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.toolbar.addWidget(theme_button)

        self.footer = QLabel("Mode: WALL | W/S/E/R/Space/C/+/- | Drag: Middle Click")
        self.footer.setStyleSheet("background-color: #05080f; color: #88aaff; font-family: Consolas; font-size: 11px;")
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.statusBar().addWidget(self.footer, 1)

    def set_mode(self, mode):
        self.maze.mode = mode
        self.footer.setText(f"Mode: {mode.upper()} | W/S/E/R/Space/C/+/- | Drag: Middle Click")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1200, 675)
    win.show()
    sys.exit(app.exec())
