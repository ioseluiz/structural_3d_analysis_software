#
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
                             QTextEdit, QLabel, QPushButton, QFrame, QSizePolicy, 
                             QTabWidget, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QVector3D, QMatrix4x4, QTextCursor
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
    item = gl.GLLinePlotItem(pos=pos, color=color, width=1, antialias=True, mode='lines') 
    return item

def create_color_icon(color: QColor, text: str = "") -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(color)
    if text:
        painter = QPainter(pixmap)
        painter.setPen(Qt.GlobalColor.white if color.lightness() < 128 else Qt.GlobalColor.black)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
    return QIcon(pixmap)

# --- FUNCIONES MATEMÁTICAS ---
#--- Función Matemática con Debug (ponla al inicio o antes de Viewport3DWidget) ---
def dist_sq_segment_to_ray(ray_origin, ray_dir, p1, p2):
    """
    Calcula distancia al cuadrado entre Segmento(p1,p2) y Rayo(origin,dir).
    """
    u = p2 - p1
    v = ray_dir
    w = ray_origin - p1
    
    a = QVector3D.dotProduct(u, u)
    b = QVector3D.dotProduct(u, v)
    c = QVector3D.dotProduct(v, v)
    d = QVector3D.dotProduct(u, w)
    e = QVector3D.dotProduct(v, w)
    
    det = a*c - b*b
    
    # Si son paralelos, la distancia es la del punto inicial al rayo
    if det < 1e-6: 
        s_closest = 0.0
    else:
        s_closest = (b*e - c*d) / det
    
    # Restringir al segmento finito [0, 1]
    # Si el punto más cercano está fuera del segmento, clamp a los extremos
    if s_closest < 0.0: s_closest = 0.0
    elif s_closest > 1.0: s_closest = 1.0
    
    # Punto exacto en el segmento 3D
    pt_on_segment = p1 + u * s_closest
    
    # Ahora buscamos el punto más cercano en el Rayo (proyección)
    # (PuntoSeg - OrigenRayo) . DireccionRayo
    t_closest = QVector3D.dotProduct(pt_on_segment - ray_origin, v)
    
    # Punto en el rayo
    pt_on_ray = ray_origin + v * t_closest
    
    dist_sq = (pt_on_segment - pt_on_ray).lengthSquared()
    return dist_sq

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
    selectionChanged = pyqtSignal(list) # Señal de selección

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
    frameSelectionChanged = pyqtSignal(set) # Señal de Frames
    createFrameSignal = pyqtSignal(int, int) 

    def __init__(self):
        super().__init__()
        self.setCameraPosition(distance=150, elevation=30, azimuth=45)
        self.setBackgroundColor('w')
        self.setMouseTracking(True)

        self.full_nodes_data = [] 
        self.full_elements_data = []
        
        # Sets de selección separados
        self.selected_node_ids = set()
        self.selected_frame_ids = set()
        
        # FLAGS
        self.node_ids_visible = False
        self.frame_ids_visible = False
        self.axes_visible = True
        self.add_frame_mode = False 
        self.temp_first_node_id = None 
        
        self.node_text_items = [] 
        self.frame_text_items = [] 
        self.axes_items = []

        # --- GRID DINÁMICO ---
        self.grid = gl.GLGridItem()
        self.grid.setSize(100, 100, 0)
        self.grid.setSpacing(10, 10, 0)
        self.grid.setColor((50, 50, 50, 40))
        self.grid.setGLOptions('translucent')
        self.addItem(self.grid)
        self.axes_items.append(self.grid)

        self._draw_vector_axes()

        # Item para Frames Normales (Gris)
        self.frames_item = gl.GLLinePlotItem(pos=np.zeros((0,3)), color=(0.4, 0.4, 0.4, 1), width=2, mode='lines', antialias=True)
        self.addItem(self.frames_item)

        # Item para Frames Seleccionados (Rojo, más grueso)
        self.sel_frames_item = gl.GLLinePlotItem(pos=np.zeros((0,3)), color=(1, 0, 0, 1), width=4, mode='lines', antialias=True)
        self.addItem(self.sel_frames_item)
        self.sel_frames_item.setVisible(False)

        # Item para Nodos
        self.scatter = gl.GLScatterPlotItem(pos=np.zeros((0, 3)), size=12, color=(0, 0, 1, 1), pxMode=True)
        self.scatter.setGLOptions('translucent')
        self.addItem(self.scatter)
        
        # --- DEBUG VISUAL (Línea Magenta) ---
        self.debug_ray_line = gl.GLLinePlotItem(pos=np.zeros((2,3)), color=(1, 0, 1, 1), width=3, antialias=True)
        self.addItem(self.debug_ray_line)
        self.debug_ray_line.setVisible(False)

    def set_add_frame_mode(self, active: bool):
        self.add_frame_mode = active
        self.temp_first_node_id = None
        self._refresh_scene_graphics()

    def _draw_vector_axes(self):
        L, W = 50, 1 
        xaxis = gl.GLLinePlotItem(pos=np.array([[0,0,0], [L,0,0]]), color=(1,0,0,1), width=W, antialias=True)
        yaxis = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,L,0]]), color=(0,0.6,0,1), width=W, antialias=True)
        zaxis = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,0,L]]), color=(0,0,1,1), width=W, antialias=True)
        self.addItem(xaxis); self.axes_items.append(xaxis)
        self.addItem(yaxis); self.axes_items.append(yaxis)
        self.addItem(zaxis); self.axes_items.append(zaxis)
        
        for t, o, c in [("X", (L+5,0,0), (1,0,0,1)), ("Y", (0,L+5,0), (0,0.6,0,1)), ("Z", (0,0,L+5), (0,0,1,1))]:
            it = generate_vector_text(t, o, scale=2.5, color=c)
            if it: self.addItem(it); self.axes_items.append(it)

    def auto_adjust_grid(self, bounds):
        if not bounds: return
        min_x, max_x, min_y, max_y, _, _ = bounds
        
        # Calcular dimensiones del modelo
        width = max_x - min_x
        height = max_y - min_y
        max_dim = max(width, height) # Dimensión real sin forzar 1.0 todavía
        
        # CASO 1: Modelo vacío, puntual o muy pequeño (< 10 unidades)
        # Usamos un Grid "Estándar" de 100x100 con cuadros de 10
        if max_dim < 10.0:
            grid_size = 100.0
            spacing = 10.0
        
        # CASO 2: Modelo normal o grande
        else:
            grid_size = max_dim * 3.0
            
            # Calcular espaciado logarítmico (1, 10, 100...) basado en el tamaño real
            exponent = math.floor(math.log10(max_dim))
            spacing = 10 ** (exponent - 1)
            
            # Si salen demasiadas líneas (>20), aumentamos el espaciado
            if max_dim / spacing > 20:
                spacing *= 5
                
            # Limpieza final: Evitar que el grid sea más pequeño que 100 visualmente
            if grid_size < 100: grid_size = 100

        self.grid.setSize(grid_size, grid_size, 0)
        self.grid.setSpacing(spacing, spacing, 0)
        
        # Centrar el grid en el modelo
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self.grid.resetTransform()
        self.grid.translate(center_x, center_y, 0)

    # --- TOGGLES ---
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
            txt_item = generate_vector_text(str(node[0]), (node[1]+1, node[2], node[3]+1), scale=0.5, color=(0,0,0,1))
            if txt_item: self.addItem(txt_item); self.node_text_items.append(txt_item)

    def _refresh_frame_labels(self):
        for item in self.frame_text_items:
            try: self.removeItem(item)
            except: pass
        self.frame_text_items.clear()
        if not self.frame_ids_visible: return
        node_map = {n[0]: (n[1], n[2], n[3]) for n in self.full_nodes_data}
        for elem in self.full_elements_data:
            if elem[1] in node_map and elem[2] in node_map:
                c1, c2 = node_map[elem[1]], node_map[elem[2]]
                mid = ((c1[0]+c2[0])/2, (c1[1]+c2[1])/2, (c1[2]+c2[2])/2)
                txt = generate_vector_text(f"F{elem[0]}", (mid[0], mid[1], mid[2]+1), scale=0.5, color=(0,0,0.5,1))
                if txt: self.addItem(txt); self.frame_text_items.append(txt)

    def update_scene_data(self, nodes_data, elements_data):
        self.full_nodes_data = nodes_data
        self.full_elements_data = elements_data
        
        # Limpiar IDs huérfanos
        curr_n = set(n[0] for n in nodes_data)
        self.selected_node_ids = self.selected_node_ids.intersection(curr_n)
        curr_f = set(e[0] for e in elements_data)
        self.selected_frame_ids = self.selected_frame_ids.intersection(curr_f)
        
        self._refresh_scene_graphics()
        self._refresh_node_labels()
        self._refresh_frame_labels()

    def set_selection(self, node_ids=None, frame_ids=None):
        if node_ids is not None: self.selected_node_ids = set(node_ids)
        if frame_ids is not None: self.selected_frame_ids = set(frame_ids)
        self._refresh_scene_graphics()

    def _refresh_scene_graphics(self):
        # Nodos
        if not self.full_nodes_data:
            self.scatter.setData(pos=np.zeros((0,3)), color=(0,0,0,0))
        else:
            coords = np.array([n[1:] for n in self.full_nodes_data], dtype=np.float32)
            colors = np.array([[0,0,1,1] for _ in range(len(coords))], dtype=np.float32)
            for i, n in enumerate(self.full_nodes_data):
                if n[0] in self.selected_node_ids: colors[i] = [1,0,0,1]
                elif n[0] == self.temp_first_node_id: colors[i] = [0,1,0,1]
            self.scatter.setData(pos=coords, size=12, color=colors, pxMode=True)
            
        # Frames
        node_map = {n[0]: (n[1],n[2],n[3]) for n in self.full_nodes_data}
        norm_lines, sel_lines = [], []
        
        for e in self.full_elements_data:
            if e[1] in node_map and e[2] in node_map:
                pts = [list(node_map[e[1]]), list(node_map[e[2]])]
                if e[0] in self.selected_frame_ids: sel_lines.extend(pts)
                else: norm_lines.extend(pts)
                
        self.frames_item.setData(pos=np.array(norm_lines, dtype=np.float32) if norm_lines else np.zeros((0,3)))
        
        if sel_lines:
            self.sel_frames_item.setData(pos=np.array(sel_lines, dtype=np.float32))
            self.sel_frames_item.setVisible(True)
        else:
            self.sel_frames_item.setVisible(False)
        self.update()

    # --- RAY CASTING ---

    def _get_mouse_ray(self, x, y):
        """
        Calcula el rayo usando 'Unproject' puro en ambos planos (Near y Far).
        Es más robusto que usar cameraPosition().
        """
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0: return QVector3D(0,0,0), QVector3D(0,0,1)

        # 1. Obtener matrices
        m_view = self.viewMatrix()
        
        # Intentar obtener la matriz de proyección exacta del widget
        m_proj = None
        try:
            m_proj = self.projectionMatrix()
        except TypeError:
            try:
                r = (0, 0, w, h)
                m_proj = self.projectionMatrix(region=r, viewport=r)
            except Exception: pass
        
        if m_proj is None:
            m_proj = QMatrix4x4()
            m_proj.perspective(self.opts['fov'], w / h, 0.1, 5000.0)
            
        # 2. Invertir MVP
        mvp = m_proj * m_view
        inv_mvp, ok = mvp.inverted()
        if not ok: return QVector3D(0,0,0), QVector3D(0,0,1)
        
        # 3. Coordenadas Normalizadas
        x_ndc = (2.0 * x) / w - 1.0
        y_ndc = 1.0 - (2.0 * y) / h 
        
        # 4. Unproject de ambos extremos del frustum
        # Plano Cercano (Near Plane, z = -1.0 en NDC) -> Aquí empieza el rayo realmente
        pt_near_ndc = QVector3D(x_ndc, y_ndc, -1.0)
        pt_near_world = inv_mvp.map(pt_near_ndc)
        
        # Plano Lejano (Far Plane, z = 1.0 en NDC)
        pt_far_ndc = QVector3D(x_ndc, y_ndc, 1.0)
        pt_far_world = inv_mvp.map(pt_far_ndc)
        
        # 5. Definir Rayo
        ray_origin = pt_near_world
        ray_dir = (pt_far_world - pt_near_world).normalized()
        
        return ray_origin, ray_dir

    def _get_clicked_item(self, x, y, node_thresh=15.0, frame_pixel_thresh=10.0):
        """
        x, y: Coordenadas del mouse en el widget.
        node_thresh: Radio de clic para nodos (en píxeles aprox, si usamos proyección).
        frame_pixel_thresh: Tolerancia en PÍXELES para seleccionar líneas.
        """
        w = self.width()
        h = self.height()
        
        # 1. Preparar Matrices para Proyección (Mundo -> Pantalla)
        m_view = self.viewMatrix()
        m_proj = None
        try:
            m_proj = self.projectionMatrix()
        except TypeError:
            try:
                r = (0, 0, w, h)
                m_proj = self.projectionMatrix(region=r, viewport=r)
            except Exception: pass
        
        if m_proj is None:
            m_proj = QMatrix4x4()
            m_proj.perspective(self.opts['fov'], w / h, 0.1, 5000.0)
            
        mvp = m_proj * m_view
        
        # Función auxiliar para proyectar 3D -> 2D (Pantalla)
        def project_to_screen(bx, by, bz):
            vec = QVector3D(float(bx), float(by), float(bz))
            # map() aplica la matriz completa
            screen_vec = mvp.map(vec)
            # Convertir NDC (-1 a 1) a Coordenadas de Widget (0 a w, h a 0)
            sx = (screen_vec.x() + 1.0) * w / 2.0
            sy = (1.0 - screen_vec.y()) * h / 2.0 # Invertir Y
            return sx, sy, screen_vec.z() # Z se usa para saber si está detrás de la cámara

        print(f"\n--- CLICK SCREEN SPACE ({x}, {y}) ---")

        # ---------------------------------------------------------
        # 1. DETECCIÓN DE NODOS (Usando distancia en pantalla)
        # ---------------------------------------------------------
        closest_n = None
        min_n_dist = float('inf')
        sq_n_thresh = node_thresh**2 # Píxeles al cuadrado
        
        # Cacheamos posiciones de pantalla para usarlas en los frames luego
        screen_coords_map = {} 

        for n in self.full_nodes_data:
            nid, nx, ny, nz = n
            sx, sy, sz = project_to_screen(nx, ny, nz)
            
            # Guardamos para frames (si está delante de la cámara)
            if sz < 1.0: # 1.0 es el plano lejano en NDC habitual
                screen_coords_map[nid] = (sx, sy)

            # Distancia 2D simple (Pitágoras)
            dist_sq = (x - sx)**2 + (y - sy)**2
            
            if dist_sq < sq_n_thresh and dist_sq < min_n_dist:
                min_n_dist = dist_sq
                closest_n = nid
        
        # Si le dimos a un nodo, retornamos (prioridad sobre frames)
        if closest_n is not None:
            print(f">> Nodo {closest_n} seleccionado (Dist: {min_n_dist**.5:.1f} px)")
            return 'node', closest_n

        # ---------------------------------------------------------
        # 2. DETECCIÓN DE FRAMES (Proyección 2D Línea)
        # ---------------------------------------------------------
        closest_f = None
        min_f_dist = float('inf')
        sq_f_thresh = frame_pixel_thresh**2 # 10 px de tolerancia -> 100 sq
        
        print(f"Buscando en {len(self.full_elements_data)} frames (Screen Space)...")

        for e in self.full_elements_data:
            eid, n1, n2 = e
            
            # Solo procesar si ambos nodos son visibles y están mapeados
            if n1 in screen_coords_map and n2 in screen_coords_map:
                s1 = screen_coords_map[n1] # (x, y)
                s2 = screen_coords_map[n2] # (x, y)
                
                # Distancia punto (mouse) a segmento (frame proyectado)
                d_sq = dist_sq_point_to_segment_2d(x, y, s1[0], s1[1], s2[0], s2[1])
                
                if d_sq < 2500: # Debug solo cercanos (<50px)
                    status = "HIT" if d_sq < sq_f_thresh else "MISS"
                    print(f"Frame {eid}: {d_sq:.1f} px_sq (Req: {sq_f_thresh}) -> {status}")

                if d_sq < sq_f_thresh and d_sq < min_f_dist:
                    min_f_dist = d_sq
                    closest_f = eid
        
        if closest_f is not None:
            print(f">> Frame {closest_f} SELECCIONADO")
            return 'frame', closest_f

        return None, None

    def mousePressEvent(self, ev):
        itype, iid = self._get_clicked_item(ev.position().x(), ev.position().y())
        mod = ev.modifiers()
        is_ctrl = mod & Qt.KeyboardModifier.ControlModifier

        if self.add_frame_mode:
            if itype == 'node':
                if self.temp_first_node_id is None:
                    self.temp_first_node_id = iid
                elif iid != self.temp_first_node_id:
                    self.createFrameSignal.emit(self.temp_first_node_id, iid)
                    self.temp_first_node_id = None
                self._refresh_scene_graphics()
                ev.accept()
            else:
                if self.temp_first_node_id: 
                    self.temp_first_node_id = None
                    self._refresh_scene_graphics()
                super().mousePressEvent(ev)
        else:
            if itype:
                if itype == 'node':
                    if is_ctrl: 
                        if iid in self.selected_node_ids: self.selected_node_ids.remove(iid)
                        else: self.selected_node_ids.add(iid)
                    else:
                        self.selected_node_ids = {iid}
                        self.selected_frame_ids.clear()
                elif itype == 'frame':
                    if is_ctrl:
                        if iid in self.selected_frame_ids: self.selected_frame_ids.remove(iid)
                        else: self.selected_frame_ids.add(iid)
                    else:
                        self.selected_frame_ids = {iid}
                        self.selected_node_ids.clear()
                
                self._refresh_scene_graphics()
                self.nodeSelectionChanged.emit(self.selected_node_ids)
                self.frameSelectionChanged.emit(self.selected_frame_ids)
                ev.accept()
            else:
                if not is_ctrl:
                    self.selected_node_ids.clear()
                    self.selected_frame_ids.clear()
                    self._refresh_scene_graphics()
                    self.nodeSelectionChanged.emit(self.selected_node_ids)
                    self.frameSelectionChanged.emit(self.selected_frame_ids)
                super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        super().mouseMoveEvent(ev)
        w, h = self.width(), self.height()
        if w <= 0: return
        
        orig, direction = self._get_mouse_ray(ev.position().x(), ev.position().y())
        closest, snap_node = 9999, None
        
        for n in self.full_nodes_data:
            P = QVector3D(float(n[1]), float(n[2]), float(n[3]))
            proj = QVector3D.dotProduct(P - orig, direction)
            if proj < 0: continue
            dist = (P - (orig + direction*proj)).length()
            if dist < 5.0 and dist < closest: # Snap visual radius
                closest = dist; snap_node = n
        
        if snap_node:
            self.mouseMovedSignal.emit(snap_node[1], snap_node[2], snap_node[3], True)
        elif abs(direction.z()) > 1e-6:
            t = -orig.z() / direction.z()
            inte = orig + direction * t
            self.mouseMovedSignal.emit(inte.x(), inte.y(), inte.z(), False)

    def set_view_direction(self, view_name: str):
        center = self.opts['center']
        dist = self.cameraParams()['distance']
        if view_name == "ISO": self.setCameraPosition(pos=center, distance=dist, elevation=30, azimuth=45)
        elif view_name == "TOP": self.setCameraPosition(pos=center, distance=dist, elevation=90, azimuth=-90)
        elif view_name == "FRONT": self.setCameraPosition(pos=center, distance=dist, elevation=0, azimuth=-90)
        elif view_name == "RIGHT": self.setCameraPosition(pos=center, distance=dist, elevation=0, azimuth=0)

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