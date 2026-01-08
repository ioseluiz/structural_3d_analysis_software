#
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
                             QTextEdit, QLabel, QPushButton, QFrame, QSizePolicy, 
                             QTabWidget, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QRect
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QVector3D, QMatrix4x4, QTextCursor, QPen, QBrush
import numpy as np
import pyqtgraph.opengl as gl
from pyqtgraph.opengl import GLViewWidget
import math

# --- SISTEMA DE TEXTO VECTORIAL ---
VECTOR_FONT_DEFS = {
    '0': [[0,0], [1,0], [1,2], [0,2], [0,0]],
    '1': [[0.5,0], [0.5,2]],
    '2': [[0,2], [1,2], [1,1], [0,1], [0,0], [1,0]],
    '3': [[0,2], [1,2], [1,1], [0,1], [1,1], [1,0], [0,0]],
    '4': [[1,0], [1,2], [1,1], [0,1], [0,2]],
    '5': [[1,2], [0,2], [0,1], [1,1], [1,0], [0,0]],
    '6': [[1,2], [0,2], [0,0], [1,0], [1,1], [0,1]],
    '7': [[0,2], [1,2], [0.5,0]],
    '8': [[0,1], [1,1], [1,2], [0,2], [0,0], [1,0], [1,1]],
    '9': [[1,0], [1,2], [0,2], [0,1], [1,1]],
    'X': [[0,0], [1,2], [0.5,1], [0,2], [1,0]], 
    'Y': [[0,2], [0.5,1], [1,2], [0.5,1], [0.5,0]], 
    'Z': [[0,2], [1,2], [0,0], [1,0]],
    '-': [[0,1], [1,1]],
    'F': [[0,0], [0,2], [1,2], [0,2], [0,1], [0.8,1]] 
}

def generate_vector_text(text, origin, scale=1.0, color=(0,0,0,1), width=1):
    points = []
    ox, oy, oz = origin
    cursor_x = 0
    text = str(text)

    for char in text:
        if char in VECTOR_FONT_DEFS:
            stroke_points = VECTOR_FONT_DEFS[char]
            for i in range(len(stroke_points) - 1):
                lx1, ly1 = stroke_points[i]
                p1 = [ox + (cursor_x + lx1) * scale, oy, oz + ly1 * scale]
                lx2, ly2 = stroke_points[i+1]
                p2 = [ox + (cursor_x + lx2) * scale, oy, oz + ly2 * scale]
                points.append(p1)
                points.append(p2)
        cursor_x += 1.5 

    if not points:
        return None

    pos = np.array(points, dtype=np.float32)
    item = gl.GLLinePlotItem(pos=pos, color=color, width=width, antialias=True, mode='lines') 
    return item

# --- FUNCIONES MATEMÁTICAS ---

def dist_sq_point_to_segment_2d(px, py, x1, y1, x2, y2):
    """
    Calcula la distancia al cuadrado desde un punto (px, py) 
    a un segmento de línea 2D definido por (x1, y1) y (x2, y2).
    """
    l2 = (x1 - x2)**2 + (y1 - y2)**2
    if l2 == 0: return (px - x1)**2 + (py - y1)**2
    
    t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2
    t = max(0, min(1, t))
    
    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)
    
    return (px - proj_x)**2 + (py - proj_y)**2

def create_color_icon(color: QColor, text: str = "") -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(color)
    if text:
        painter = QPainter(pixmap)
        painter.setPen(Qt.GlobalColor.white if color.lightness() < 128 else Qt.GlobalColor.black)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
    return QIcon(pixmap)

# --- WIDGETS AUXILIARES ---

class WorkTreeWidget(QWidget):
    itemSelected = pyqtSignal(str) 
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Work Tree")
        self.root = QTreeWidgetItem(self.tree, ["Document"])
        QTreeWidgetItem(self.root, ["Geometry"])
        QTreeWidgetItem(self.root, ["Materials"]) 
        QTreeWidgetItem(self.root, ["Sections"])  
        QTreeWidgetItem(self.root, ["Elements"]) 
        self.root.setExpanded(True)
        layout.addWidget(self.tree)
        self.setLayout(layout)
        self.tree.itemClicked.connect(self._on_click)
    def _on_click(self, item, col):
        self.itemSelected.emit(item.text(0))

class NodeTableWidget(QWidget):
    selectionChanged = pyqtSignal(list) 
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "X", "Y", "Z"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(QLabel("Nodes Table"))
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.table.itemSelectionChanged.connect(self._on_selection_change)
        self._block_signal = False
    def update_data(self, full_node_list):
        self._block_signal = True
        self.table.setRowCount(len(full_node_list))
        for row, node_data in enumerate(full_node_list):
            id_item = QTableWidgetItem(str(node_data[0]))
            id_item.setData(Qt.ItemDataRole.UserRole, node_data[0])
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, QTableWidgetItem(f"{node_data[1]:.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{node_data[2]:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{node_data[3]:.2f}"))
        self._block_signal = False
    def select_rows_by_ids(self, ids_set):
        self._block_signal = True
        self.table.clearSelection()
        if ids_set:
            for row in range(self.table.rowCount()):
                item_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                if item_id in ids_set:
                    self.table.selectRow(row)
        self._block_signal = False
    def _on_selection_change(self):
        if self._block_signal: return
        selected_ids = []
        rows = set(index.row() for index in self.table.selectedIndexes())
        for row in rows:
            item = self.table.item(row, 0)
            if item:
                selected_ids.append(item.data(Qt.ItemDataRole.UserRole))
        self.selectionChanged.emit(selected_ids)

class ElementTableWidget(QWidget):
    selectionChanged = pyqtSignal(list)
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Frame ID", "Node A", "Node B"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(QLabel("Frames Table"))
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.table.itemSelectionChanged.connect(self._on_selection_change)
        self._block_signal = False
    def update_data(self, elements_list):
        self._block_signal = True
        self.table.setRowCount(len(elements_list))
        for row, elem in enumerate(elements_list):
            id_item = QTableWidgetItem(str(elem[0]))
            id_item.setData(Qt.ItemDataRole.UserRole, elem[0])
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, QTableWidgetItem(str(elem[1])))
            self.table.setItem(row, 2, QTableWidgetItem(str(elem[2])))
        self._block_signal = False
    def select_rows_by_ids(self, ids_set):
        self._block_signal = True
        self.table.clearSelection()
        if ids_set:
            for row in range(self.table.rowCount()):
                item_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                if item_id in ids_set:
                    self.table.selectRow(row)
        self._block_signal = False
    def _on_selection_change(self):
        if self._block_signal: return
        selected_ids = []
        rows = set(index.row() for index in self.table.selectedIndexes())
        for row in rows:
            item = self.table.item(row, 0)
            if item:
                selected_ids.append(item.data(Qt.ItemDataRole.UserRole))
        self.selectionChanged.emit(selected_ids)

class MaterialTableWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "E (MPa)", "Nu (v)", "Rho"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(QLabel("Materials Definitions"))
        layout.addWidget(self.table)
        self.setLayout(layout)
    def update_data(self, materials_list):
        self.table.setRowCount(len(materials_list))
        for row, mat in enumerate(materials_list):
            self.table.setItem(row, 0, QTableWidgetItem(str(mat[0])))
            self.table.setItem(row, 1, QTableWidgetItem(str(mat[1])))
            self.table.setItem(row, 2, QTableWidgetItem(f"{mat[2]:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{mat[3]:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{mat[4]:.2f}"))

class TerminalWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("background-color: #FFFFFF; color: #000000; font-family: Consolas; border: 1px solid #CCC;")
        self.text_area.setText("System initialized.")
        layout.addWidget(QLabel("Terminal Output"))
        layout.addWidget(self.text_area)
        self.setLayout(layout)
    def print_message(self, message: str):
        self.text_area.append(message)
        cursor = self.text_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_area.setTextCursor(cursor)

class ScriptEditorWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        tabs = QTabWidget()
        tabs.addTab(QLabel("Script Editor Placeholder"), "Editor")
        layout.addWidget(tabs)
        self.setLayout(layout)

class CoordStatusWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background-color: rgba(0, 0, 0, 180); border-radius: 6px; } QLabel { color: #00FF00; font-family: Consolas; font-weight: bold; font-size: 11pt; }")
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        self.label = QLabel("X: 0.00   Y: 0.00   Z: 0.00")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        self.setFixedWidth(400) 
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setLayout(layout) 
    def update_coords(self, x, y, z, snapped=False):
        txt = f"X: {x:.2f}    Y: {y:.2f}    Z: {z:.2f}"
        if snapped:
            txt += " [SNAP]"
            self.label.setStyleSheet("color: #00FFFF; font-family: Consolas; font-weight: bold; font-size: 11pt;")
        else:
            self.label.setStyleSheet("color: #00FF00; font-family: Consolas; font-weight: bold; font-size: 11pt;")
        self.label.setText(txt)

# --- VIEWPORT 3D (Corazón Gráfico) ---

class Viewport3DWidget(GLViewWidget):
    mouseMovedSignal = pyqtSignal(float, float, float, bool)
    nodeSelectionChanged = pyqtSignal(set)
    frameSelectionChanged = pyqtSignal(set)
    createFrameSignal = pyqtSignal(int, int) 

    def __init__(self):
        super().__init__()
        self.setCameraPosition(distance=150, elevation=30, azimuth=45)
        self.setBackgroundColor('w')
        self.setMouseTracking(True)

        self.full_nodes_data = [] 
        self.full_elements_data = []

        self.selected_node_ids = set()
        self.selected_frame_ids = set()
        
        # FLAGS
        self.node_ids_visible = False
        self.frame_ids_visible = False
        self.axes_visible = True
        self.add_frame_mode = False 
        self.temp_first_node_id = None 
        
        # --- Variables de Box Selection ---
        self.box_selection_mode = False 
        self.is_dragging_box = False     
        self.box_start = QPoint()        
        self.box_end = QPoint()          
        
        # Almacenes de Items Gráficos
        self.node_text_items = [] 
        self.frame_text_items = [] 
        self.axes_items = []

        # Grid
        self.grid = gl.GLGridItem()
        self.grid.setSize(2000, 2000, 0)
        self.grid.setSpacing(50, 50, 0)
        self.grid.setColor((50, 50, 50, 40))
        self.grid.setGLOptions('translucent')
        self.addItem(self.grid)
        self.axes_items.append(self.grid)

        # Dibujar Ejes X,Y,Z
        self._draw_vector_axes()

        # Item para Frames (Líneas)
        self.frames_item = gl.GLLinePlotItem(pos=np.zeros((0,3)), color=(0.4, 0.4, 0.4, 1), width=2, mode='lines', antialias=True)
        self.addItem(self.frames_item)

        # Item para Frames Seleccionados
        self.sel_frames_item = gl.GLLinePlotItem(pos=np.zeros((0,3)), color=(1, 0, 0, 1), width=4, mode='lines', antialias=True)
        self.addItem(self.sel_frames_item)
        self.sel_frames_item.setVisible(False)

        # Item para Nodos (Puntos)
        self.scatter = gl.GLScatterPlotItem(pos=np.zeros((0, 3)), size=10, color=(0, 0, 1, 1), pxMode=True)
        self.scatter.setGLOptions('translucent')
        self.addItem(self.scatter)

        # Debug Ray
        self.debug_ray_line = gl.GLLinePlotItem(pos=np.zeros((2,3)), color=(1, 0, 1, 1), width=3, antialias=True)
        self.addItem(self.debug_ray_line)
        self.debug_ray_line.setVisible(False)

    def set_add_frame_mode(self, active: bool):
        self.add_frame_mode = active
        self.temp_first_node_id = None
        self._refresh_scatter_colors()

    def set_box_selection_mode(self, active: bool):
        self.box_selection_mode = active
        if active:
            self.add_frame_mode = False
            self.setMouseTracking(True)

    def _draw_vector_axes(self):
        L, W = 50, 1 
        xaxis = gl.GLLinePlotItem(pos=np.array([[0,0,0], [L,0,0]]), color=(1,0,0,1), width=W, antialias=True)
        yaxis = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,L,0]]), color=(0,0.6,0,1), width=W, antialias=True)
        zaxis = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,0,L]]), color=(0,0,1,1), width=W, antialias=True)
        
        self.addItem(xaxis); self.axes_items.append(xaxis)
        self.addItem(yaxis); self.axes_items.append(yaxis)
        self.addItem(zaxis); self.axes_items.append(zaxis)
        
        txt_x = generate_vector_text("X", (L+5, 0, 0), scale=2.5, color=(1,0,0,1))
        if txt_x: self.addItem(txt_x); self.axes_items.append(txt_x)
        txt_y = generate_vector_text("Y", (0, L+5, 0), scale=2.5, color=(0,0.6,0,1))
        if txt_y: self.addItem(txt_y); self.axes_items.append(txt_y)
        txt_z = generate_vector_text("Z", (0, 0, L+5), scale=2.5, color=(0,0,1,1))
        if txt_z: self.addItem(txt_z); self.axes_items.append(txt_z)

    def auto_adjust_grid(self, bounds):
        if not bounds: return
        min_x, max_x, min_y, max_y, _, _ = bounds
        
        width = max_x - min_x
        height = max_y - min_y
        max_dim = max(width, height) 
        
        # CASO 1: Modelo vacío, puntual o muy pequeño (< 10 unidades)
        if max_dim < 10.0:
            grid_size = 100.0
            spacing = 10.0
        # CASO 2: Modelo normal o grande
        else:
            grid_size = max_dim * 3.0
            exponent = math.floor(math.log10(max_dim))
            spacing = 10 ** (exponent - 1)
            if max_dim / spacing > 20: spacing *= 5
            if grid_size < 100: grid_size = 100

        self.grid.setSize(grid_size, grid_size, 0)
        self.grid.setSpacing(spacing, spacing, 0)
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self.grid.resetTransform()
        self.grid.translate(center_x, center_y, 0)

    # --- TOGGLES DE VISIBILIDAD ---
    def toggle_axes(self, show: bool):
        self.axes_visible = show
        for item in self.axes_items: item.setVisible(show)

    def toggle_node_ids(self, show: bool):
        self.node_ids_visible = show
        self._refresh_node_labels()

    def toggle_frame_ids(self, show: bool):
        self.frame_ids_visible = show
        self._refresh_frame_labels()
    
    def _refresh_node_labels(self):
        for item in self.node_text_items:
            try: self.removeItem(item)
            except: pass
        self.node_text_items.clear()
        if not self.node_ids_visible: return
        for node in self.full_nodes_data:
            nid, x, y, z = node
            txt_item = generate_vector_text(str(nid), (x+1, y, z+1), scale=0.5, color=(0,0,0,1), width=1)
            if txt_item: self.addItem(txt_item); self.node_text_items.append(txt_item)

    def _refresh_frame_labels(self):
        for item in self.frame_text_items:
            try: self.removeItem(item)
            except: pass
        self.frame_text_items.clear()
        if not self.frame_ids_visible: return
        node_map = {n[0]: (n[1], n[2], n[3]) for n in self.full_nodes_data}
        for elem in self.full_elements_data:
            eid, n1, n2 = elem
            if n1 in node_map and n2 in node_map:
                c1 = node_map[n1]
                c2 = node_map[n2]
                mid_x = (c1[0] + c2[0]) / 2.0
                mid_y = (c1[1] + c2[1]) / 2.0
                mid_z = (c1[2] + c2[2]) / 2.0
                txt_item = generate_vector_text(f"F{eid}", (mid_x, mid_y, mid_z + 1), scale=0.5, color=(0,0,0.5,1), width=1)
                if txt_item: self.addItem(txt_item); self.frame_text_items.append(txt_item)

    def update_scene_data(self, nodes_data, elements_data):
        self.full_nodes_data = nodes_data
        self.full_elements_data = elements_data
        
        current_ids = set(n[0] for n in nodes_data)
        self.selected_node_ids = self.selected_node_ids.intersection(current_ids)
        current_f_ids = set(e[0] for e in elements_data)
        self.selected_frame_ids = self.selected_frame_ids.intersection(current_f_ids)
        
        self._refresh_scatter_colors()
        self._refresh_node_labels()
        self._refresh_frame_labels()
        
        lines_pts = []
        node_map = {n[0]: (n[1], n[2], n[3]) for n in nodes_data}
        
        norm_lines, sel_lines = [], []
        
        for elem in elements_data:
            nid1, nid2 = elem[1], elem[2]
            if nid1 in node_map and nid2 in node_map:
                pts = [list(node_map[nid1]), list(node_map[nid2])]
                if elem[0] in self.selected_frame_ids: sel_lines.extend(pts)
                else: norm_lines.extend(pts)
        
        self.frames_item.setData(pos=np.array(norm_lines, dtype=np.float32) if norm_lines else np.zeros((0,3)))
        
        if sel_lines:
            self.sel_frames_item.setData(pos=np.array(sel_lines, dtype=np.float32))
            self.sel_frames_item.setVisible(True)
        else:
            self.sel_frames_item.setVisible(False)

    def set_selection(self, node_ids=None, frame_ids=None):
        if node_ids is not None: self.selected_node_ids = set(node_ids)
        if frame_ids is not None: self.selected_frame_ids = set(frame_ids)
        self.update_scene_data(self.full_nodes_data, self.full_elements_data) # Force refresh visuals

    def _refresh_scatter_colors(self):
        if not self.full_nodes_data:
            self.scatter.setData(pos=np.zeros((0, 3)), color=(0,0,0,0))
            return
        coords = np.array([n[1:] for n in self.full_nodes_data], dtype=np.float32)
        colors = np.array([[0, 0, 1, 1] for _ in range(len(coords))], dtype=np.float32)
        
        for i, node in enumerate(self.full_nodes_data):
            nid = node[0]
            if nid in self.selected_node_ids:
                colors[i] = [1, 0, 0, 1] 
            elif nid == self.temp_first_node_id:
                colors[i] = [0, 1, 0, 1] 
        self.scatter.setData(pos=coords, size=10, color=colors, pxMode=True)
        self.update()

    # --- DIBUJADO DE CAJA 2D ---
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_dragging_box:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRect(self.box_start, self.box_end).normalized()
            fill_color = QColor(0, 120, 215, 50)  
            border_color = QColor(0, 120, 215, 255) 
            painter.setPen(QPen(border_color, 1))
            painter.setBrush(QBrush(fill_color))
            painter.drawRect(rect)
            painter.end()

    # --- EVENTOS DE MOUSE ---

    def mousePressEvent(self, ev):
        # 1. Box Selection Start
        if self.box_selection_mode and ev.button() == Qt.MouseButton.LeftButton:
            self.is_dragging_box = True
            self.box_start = ev.pos()
            self.box_end = ev.pos()
            ev.accept()
            return

        super().mousePressEvent(ev)
        
        # 2. Clic Normal (Si no es movimiento de cámara)
        if ev.button() == Qt.MouseButton.LeftButton:
            self._handle_single_click(ev)

    def mouseMoveEvent(self, ev):
        # 1. Box Dragging
        if self.is_dragging_box:
            self.box_end = ev.pos()
            self.update() 
            ev.accept()
            return

        super().mouseMoveEvent(ev)
        self._handle_mouse_hover(ev)

    def mouseReleaseEvent(self, ev):
        # 1. Box Selection End
        if self.is_dragging_box and ev.button() == Qt.MouseButton.LeftButton:
            self.is_dragging_box = False
            self.box_end = ev.pos()
            self.update() 
            self._perform_box_selection(ev.modifiers())
            ev.accept()
            return

        super().mouseReleaseEvent(ev)

    # --- LÓGICA DE SELECCIÓN (CLICK & BOX) ---

    def _handle_single_click(self, ev):
        item_type, item_id = self._get_clicked_item(ev.position().x(), ev.position().y())
        
        if self.add_frame_mode:
            if item_type == 'node':
                if self.temp_first_node_id is None:
                    self.temp_first_node_id = item_id
                else:
                    if item_id != self.temp_first_node_id:
                        self.createFrameSignal.emit(self.temp_first_node_id, item_id)
                    self.temp_first_node_id = None
                self._refresh_scatter_colors()
            else:
                self.temp_first_node_id = None
                self._refresh_scatter_colors()
        else:
            # Selección Normal
            modifiers = ev.modifiers()
            is_ctrl = modifiers & Qt.KeyboardModifier.ControlModifier
            
            if item_type:
                if item_type == 'node':
                    if is_ctrl:
                        if item_id in self.selected_node_ids: self.selected_node_ids.remove(item_id)
                        else: self.selected_node_ids.add(item_id)
                    else:
                        self.selected_node_ids = {item_id}
                        self.selected_frame_ids.clear()
                elif item_type == 'frame':
                    if is_ctrl:
                        if item_id in self.selected_frame_ids: self.selected_frame_ids.remove(item_id)
                        else: self.selected_frame_ids.add(item_id)
                    else:
                        self.selected_frame_ids = {item_id}
                        self.selected_node_ids.clear()
            else:
                if not is_ctrl:
                    self.selected_node_ids.clear()
                    self.selected_frame_ids.clear()
            
            self.update_scene_data(self.full_nodes_data, self.full_elements_data)
            self.nodeSelectionChanged.emit(self.selected_node_ids)
            self.frameSelectionChanged.emit(self.selected_frame_ids)

    def _perform_box_selection(self, modifiers):
        rect = QRect(self.box_start, self.box_end).normalized()
        if rect.width() < 5 and rect.height() < 5: return

        # Preparar Matrices
        w, h = self.width(), self.height()
        m_view = self.viewMatrix()
        m_proj = None
        try: m_proj = self.projectionMatrix()
        except: pass
        if m_proj is None:
             try: r=(0,0,w,h); m_proj = self.projectionMatrix(region=r, viewport=r)
             except: pass
        if m_proj is None:
             m_proj = QMatrix4x4(); m_proj.perspective(60.0, w/h, 0.1, 5000.0)
        
        mvp = m_proj * m_view
        
        def to_screen(x, y, z):
            vec = mvp.map(QVector3D(float(x), float(y), float(z)))
            sx = (vec.x() + 1.0) * w / 2.0
            sy = (1.0 - vec.y()) * h / 2.0
            return QPoint(int(sx), int(sy)), vec.z()

        new_nodes = set()
        new_frames = set()
        node_screen_map = {}

        # 1. Nodos en caja
        for n in self.full_nodes_data:
            nid, nx, ny, nz = n
            pt, depth = to_screen(nx, ny, nz)
            if depth < 1.0: # Visible
                node_screen_map[nid] = pt
                if rect.contains(pt): new_nodes.add(nid)
        
        # 2. Frames en caja (si algún extremo está dentro)
        for e in self.full_elements_data:
            eid, n1, n2 = e
            if n1 in node_screen_map and n2 in node_screen_map:
                p1 = node_screen_map[n1]
                p2 = node_screen_map[n2]
                if rect.contains(p1) or rect.contains(p2):
                    new_frames.add(eid)
        
        is_ctrl = modifiers & Qt.KeyboardModifier.ControlModifier
        if is_ctrl:
            self.selected_node_ids.update(new_nodes)
            self.selected_frame_ids.update(new_frames)
        else:
            self.selected_node_ids = new_nodes
            self.selected_frame_ids = new_frames
            
        self.update_scene_data(self.full_nodes_data, self.full_elements_data)
        self.nodeSelectionChanged.emit(self.selected_node_ids)
        self.frameSelectionChanged.emit(self.selected_frame_ids)

    def _get_clicked_item(self, x, y, node_thresh=15.0, frame_pixel_thresh=10.0):
        w, h = self.width(), self.height()
        m_view = self.viewMatrix()
        m_proj = None
        try: m_proj = self.projectionMatrix()
        except: pass
        if m_proj is None:
             try: r=(0,0,w,h); m_proj = self.projectionMatrix(region=r, viewport=r)
             except: pass
        if m_proj is None:
             m_proj = QMatrix4x4(); m_proj.perspective(60.0, w/h, 0.1, 5000.0)
        
        mvp = m_proj * m_view
        
        def project(bx, by, bz):
            v = mvp.map(QVector3D(float(bx), float(by), float(bz)))
            return (v.x()+1.0)*w/2.0, (1.0-v.y())*h/2.0, v.z()

        # Debug Visual
        # (Opcional: podrías dibujar aquí la línea de rayo, pero en modo screen-space es menos útil)
        print(f"\n--- CLICK SCREEN ({x}, {y}) ---")

        # Nodos (Prioridad)
        closest_n, min_n = None, float('inf')
        sq_n_th = node_thresh**2
        s_map = {}
        
        for n in self.full_nodes_data:
            nid, nx, ny, nz = n
            sx, sy, sz = project(nx, ny, nz)
            if sz < 1.0: s_map[nid] = (sx, sy)
            d2 = (x-sx)**2 + (y-sy)**2
            if d2 < sq_n_th and d2 < min_n:
                min_n = d2; closest_n = nid
        
        if closest_n: 
            print(f">> Node {closest_n} hit"); return 'node', closest_n

        # Frames (2D)
        closest_f, min_f = None, float('inf')
        sq_f_th = frame_pixel_thresh**2
        
        for e in self.full_elements_data:
            eid, n1, n2 = e
            if n1 in s_map and n2 in s_map:
                s1, s2 = s_map[n1], s_map[n2]
                d2 = dist_sq_point_to_segment_2d(x, y, s1[0], s1[1], s2[0], s2[1])
                if d2 < sq_f_th and d2 < min_f:
                    min_f = d2; closest_f = eid
        
        if closest_f:
            print(f">> Frame {closest_f} hit"); return 'frame', closest_f
            
        return None, None

    def _handle_mouse_hover(self, ev):
        pass # Implementar hover si deseas (snap visual)

    # ... Resto de métodos (set_view_direction, etc.) se mantienen igual ...
    def set_view_direction(self, view_name: str):
        center = self.opts['center']
        dist = self.cameraParams()['distance']
        if view_name == "ISO": self.setCameraPosition(pos=center, distance=dist, elevation=30, azimuth=45)
        elif view_name == "TOP": self.setCameraPosition(pos=center, distance=dist, elevation=90, azimuth=-90)
        elif view_name == "FRONT": self.setCameraPosition(pos=center, distance=dist, elevation=0, azimuth=-90)
        elif view_name == "RIGHT": self.setCameraPosition(pos=center, distance=dist, elevation=0, azimuth=0)

# --- FIN DE COMPONENTES ---
# (Las clases ViewCubeToolbar y CentralViewContainer deben estar aquí también, copiadas de tu versión anterior)
class ViewCubeToolbar(QFrame):
    viewChanged = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background-color: rgba(255, 255, 255, 230); border-radius: 4px; } QPushButton { border: none; padding: 4px; } QPushButton:hover { background-color: #DDD; }")
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        for name, color_hex in [("ISO", "#999"), ("TOP", "#2196F3"), ("FRONT", "#F44336"), ("RIGHT", "#4CAF50")]:
            btn = QPushButton()
            btn.setIcon(create_color_icon(QColor(color_hex), name[0]))
            btn.clicked.connect(lambda _, v=name: self.viewChanged.emit(v))
            layout.addWidget(btn)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

class CentralViewContainer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.viewport = Viewport3DWidget()
        self.main_layout.addWidget(self.viewport)
        self.view_toolbar = ViewCubeToolbar(self)
        self.coord_status = CoordStatusWidget(self)
        self.view_toolbar.viewChanged.connect(self.viewport.set_view_direction)
        self.viewport.mouseMovedSignal.connect(self.coord_status.update_coords)
        self.view_toolbar.raise_()
        self.coord_status.raise_()
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.view_toolbar.move(self.width() - self.view_toolbar.width() - 10, 10)
        self.view_toolbar.raise_()
        cw, ch = self.coord_status.width(), self.coord_status.height()
        self.coord_status.move(int((self.width() - cw)/2), self.height() - ch - 20)
        self.coord_status.raise_()