from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
                             QTextEdit, QLabel, QPushButton, QFrame, QSizePolicy, 
                             QTabWidget, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QVector3D, QMatrix4x4, QTextCursor
import numpy as np
import pyqtgraph.opengl as gl
from pyqtgraph.opengl import GLViewWidget
import math # Necesario para el grid logarítmico

# --- SISTEMA DE TEXTO VECTORIAL (Sin cambios) ---
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

# --- PANELES Y WIDGETS AUXILIARES ---

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
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Frame ID", "Node A", "Node B"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        layout.addWidget(QLabel("Frames Table"))
        layout.addWidget(self.table)
        self.setLayout(layout)

    def update_data(self, elements_list):
        self.table.setRowCount(len(elements_list))
        for row, elem in enumerate(elements_list):
            self.table.setItem(row, 0, QTableWidgetItem(str(elem[0])))
            self.table.setItem(row, 1, QTableWidgetItem(str(elem[1])))
            self.table.setItem(row, 2, QTableWidgetItem(str(elem[2])))

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
    createFrameSignal = pyqtSignal(int, int) 

    def __init__(self):
        super().__init__()
        self.setCameraPosition(distance=150, elevation=30, azimuth=45)
        self.setBackgroundColor('w')
        # Habilitamos el tracking, pero gestionaremos el clic manualmente
        self.setMouseTracking(True)

        self.full_nodes_data = [] 
        self.full_elements_data = []
        self.selected_ids = set()
        
        # VISIBILITY FLAGS
        self.node_ids_visible = False
        self.frame_ids_visible = False
        self.axes_visible = True
        
        self.add_frame_mode = False 
        self.temp_first_node_id = None 
        
        # Almacenes de Items Gráficos
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

        # Dibujar Ejes X,Y,Z
        self._draw_vector_axes()

        # Item para Frames (Líneas)
        self.frames_item = gl.GLLinePlotItem(pos=np.zeros((0,3)), color=(0.4, 0.4, 0.4, 1), width=2, mode='lines', antialias=True)
        self.addItem(self.frames_item)

        # Item para Nodos (Puntos)
        self.scatter = gl.GLScatterPlotItem(pos=np.zeros((0, 3)), size=12, color=(0, 0, 1, 1), pxMode=True)
        self.scatter.setGLOptions('translucent')
        self.addItem(self.scatter)

        # --- DEBUG: Rayo Visual ---
        # Una línea roja brillante que nos mostrará por dónde "viaja" el clic
        self.debug_ray_line = gl.GLLinePlotItem(pos=np.zeros((2,3)), color=(1, 0, 1, 1), width=3, antialias=True)
        self.addItem(self.debug_ray_line)
        self.debug_ray_line.setVisible(False) # Oculto por defecto

    def set_add_frame_mode(self, active: bool):
        self.add_frame_mode = active
        self.temp_first_node_id = None
        self._refresh_scatter_colors()

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

    # --- NUEVA LÓGICA DE GRID DINÁMICO ---
    def auto_adjust_grid(self, bounds):
        """
        Ajusta el tamaño del Grid y su espaciado basándose en los límites del modelo.
        bounds: tupla (min_x, max_x, min_y, max_y, min_z, max_z)
        """
        if not bounds: return

        min_x, max_x, min_y, max_y, _, _ = bounds
        
        # Calcular dimensiones del modelo
        width = max_x - min_x
        height = max_y - min_y
        max_dim = max(width, height, 1.0) 
        
        # Grid size un poco más grande
        grid_size = max_dim * 3.0
        if grid_size < 100: grid_size = 100 # Mínimo 100 unidades
        
        # Calcular espaciado logarítmico (1, 10, 100, 1000...)
        exponent = math.floor(math.log10(max_dim)) if max_dim > 0 else 1
        spacing = 10 ** (exponent - 1) 
        
        # Si el espaciado es muy denso, lo aumentamos
        if max_dim / spacing > 20:
            spacing *= 5
            
        self.grid.setSize(grid_size, grid_size, 0)
        self.grid.setSpacing(spacing, spacing, 0)
        
        # Centrar el grid aproximadamente
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        # Reseteamos transformaciones y movemos
        self.grid.resetTransform()
        self.grid.translate(center_x, center_y, 0)

    # --- TOGGLES DE VISIBILIDAD ---
    def toggle_axes(self, show: bool):
        self.axes_visible = show
        for item in self.axes_items:
            item.setVisible(show)

    def toggle_node_ids(self, show: bool):
        self.node_ids_visible = show
        self._refresh_node_labels()

    def toggle_frame_ids(self, show: bool):
        self.frame_ids_visible = show
        self._refresh_frame_labels()
    
    # --- REFRESH LABELS ---
    def _refresh_node_labels(self):
        for item in self.node_text_items:
            try: self.removeItem(item)
            except: pass
        self.node_text_items.clear()

        if not self.node_ids_visible: return

        for node in self.full_nodes_data:
            nid, x, y, z = node
            txt_item = generate_vector_text(str(nid), (x+1, y, z+1), scale=0.5, color=(0,0,0,1), width=1)
            if txt_item:
                self.addItem(txt_item)
                self.node_text_items.append(txt_item)

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
                if txt_item:
                    self.addItem(txt_item)
                    self.frame_text_items.append(txt_item)

    def update_scene_data(self, nodes_data, elements_data):
        self.full_nodes_data = nodes_data
        self.full_elements_data = elements_data
        
        current_ids = set(n[0] for n in nodes_data)
        self.selected_ids = self.selected_ids.intersection(current_ids)
        
        self._refresh_scatter_colors()
        self._refresh_node_labels()
        self._refresh_frame_labels()
        
        lines_pts = []
        node_map = {n[0]: (n[1], n[2], n[3]) for n in nodes_data}
        
        for elem in elements_data:
            nid1, nid2 = elem[1], elem[2]
            if nid1 in node_map and nid2 in node_map:
                lines_pts.append(list(node_map[nid1]))
                lines_pts.append(list(node_map[nid2]))
        
        if lines_pts:
            self.frames_item.setData(pos=np.array(lines_pts, dtype=np.float32))
        else:
            self.frames_item.setData(pos=np.zeros((0,3)))

    def set_selection(self, ids_list):
        self.selected_ids = set(ids_list)
        self._refresh_scatter_colors()

    def _refresh_scatter_colors(self):
        if not self.full_nodes_data:
            self.scatter.setData(pos=np.zeros((0, 3)), color=(0,0,0,0))
            return

        coords = np.array([n[1:] for n in self.full_nodes_data], dtype=np.float32)
        # Color azul por defecto
        colors = np.array([[0, 0, 1, 1] for _ in range(len(coords))], dtype=np.float32)
        
        for i, node in enumerate(self.full_nodes_data):
            nid = node[0]
            if nid in self.selected_ids:
                colors[i] = [1, 0, 0, 1] # Rojo para selección
            elif nid == self.temp_first_node_id:
                colors[i] = [0, 1, 0, 1] # Verde para inicio de frame
        
        self.scatter.setData(pos=coords, size=12, color=colors, pxMode=True)
        self.update()

    # --- LÓGICA DE RAY-CASTING Y EVENTOS ---
    
    def _get_mouse_ray(self, x, y):
        """
        Calcula el rayo en coordenadas del mundo.
        Intenta obtener la matriz de proyección EXACTA del widget para evitar errores de Aspect Ratio.
        """
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0: 
            return QVector3D(0,0,0), QVector3D(0,0,1)

        # 1. Matriz de Vista (Siempre es estándar)
        m_view = self.viewMatrix()

        # 2. Matriz de Proyección (INTENTO ROBUSTO)
        # Intentamos llamar a projectionMatrix adaptándonos a la firma del método
        m_proj = None
        try:
            # Intento 1: Estándar (sin argumentos o por defecto)
            m_proj = self.projectionMatrix()
        except TypeError:
            try:
                # Intento 2: Firma con region y viewport (Tu caso probable)
                # region=(x, y, w, h), viewport=(x, y, w, h)
                r = (0, 0, w, h)
                m_proj = self.projectionMatrix(region=r, viewport=r)
            except Exception as e:
                print(f"Error obteniendo projectionMatrix: {e}")
        
        # 3. Fallback Manual (Solo si todo falla)
        if m_proj is None:
            print("WARNING: Usando cálculo manual de matriz (puede ser impreciso)")
            m_proj = QMatrix4x4()
            m_proj.perspective(self.opts['fov'], w / h, 0.1, 5000.0)
        
        # 4. Inversión MVP
        mvp = m_proj * m_view
        inv_mvp, invertible = mvp.inverted()
        
        if not invertible:
            return QVector3D(0,0,0), QVector3D(0,0,1)

        # 5. Cálculo del Rayo
        x_ndc = (2.0 * x) / w - 1.0
        y_ndc = 1.0 - (2.0 * y) / h 
        
        ray_origin = self.cameraPosition()
        
        point_on_far_plane_ndc = QVector3D(x_ndc, y_ndc, 1.0)
        point_on_far_plane_world = inv_mvp.map(point_on_far_plane_ndc)
        
        ray_dir = (point_on_far_plane_world - ray_origin).normalized()

        return ray_origin, ray_dir

    def _get_ray_intersection(self, x_screen, y_screen, threshold=2.0):
        if not self.full_nodes_data: return None

        # 1. Obtener Rayo
        ray_origin, ray_dir = self._get_mouse_ray(x_screen, y_screen)
        
        # --- DEBUG: DIBUJAR EL RAYO EN 3D ---
        # Dibujamos una linea desde la camara hasta 1000 unidades al fondo
        p_start = ray_origin
        p_end = ray_origin + ray_dir * 1000
        # Actualizamos la línea roja de debug
        self.debug_ray_line.setData(pos=np.array([
            [p_start.x(), p_start.y(), p_start.z()],
            [p_end.x(), p_end.y(), p_end.z()]
        ], dtype=np.float32))
        self.debug_ray_line.setVisible(True)
        # ------------------------------------

        closest_node_id = None
        closest_dist_sq = float('inf')
        threshold_sq = threshold * threshold
        
        # --- CORRECCIÓN AQUÍ: Formato manual de string ---
        print(f"\n--- DEBUG CLICK en ({x_screen}, {y_screen}) ---")
        print(f"Rayo Origen: ({ray_origin.x():.2f}, {ray_origin.y():.2f}, {ray_origin.z():.2f})")
        print(f"Rayo Dirección: ({ray_dir.x():.2f}, {ray_dir.y():.2f}, {ray_dir.z():.2f})")

        for node in self.full_nodes_data:
            nid, nx, ny, nz = node
            P = QVector3D(float(nx), float(ny), float(nz))
            
            # Vector nodo a origen
            AP = P - ray_origin
            proj = QVector3D.dotProduct(AP, ray_dir)
            
            if proj < 0: continue 

            closest_point_on_ray = ray_origin + ray_dir * proj
            dist_sq = (P - closest_point_on_ray).lengthSquared()
            
            # Calculamos distancia real para imprimir
            real_dist = dist_sq ** 0.5
            
            # IMPRIMIR SOLO NODOS CERCANOS (< 50 unidades)
            if real_dist < 50.0:
                status = "DENTRO" if dist_sq < threshold_sq else "FUERA"
                print(f"Nodo {nid}: Distancia al rayo = {real_dist:.4f} (Threshold: {threshold}) -> {status}")

            if dist_sq < threshold_sq:
                if dist_sq < closest_dist_sq:
                    closest_dist_sq = dist_sq
                    closest_node_id = nid
        
        if closest_node_id:
            print(f"SELECCIONADO FINAL: Nodo {closest_node_id}")
        else:
            print("NINGUNA SELECCIÓN")
            
        return closest_node_id

    def mousePressEvent(self, ev):
        # 1. Intentar seleccionar un nodo con Ray-Casting
        clicked_id = self._get_ray_intersection(ev.position().x(), ev.position().y())
        
        # 2. Manejo de estados
        if self.add_frame_mode:
            if clicked_id is not None:
                if self.temp_first_node_id is None:
                    # Primer clic: Inicio
                    self.temp_first_node_id = clicked_id
                    self._refresh_scatter_colors() 
                else:
                    # Segundo clic: Fin
                    if clicked_id != self.temp_first_node_id:
                        self.createFrameSignal.emit(self.temp_first_node_id, clicked_id)
                    # Resetear para permitir el siguiente frame
                    self.temp_first_node_id = None
                    self._refresh_scatter_colors()
                ev.accept()
            else:
                # Clic en el vacío: Deseleccionar temporal, pero mantener modo Add Frame
                # Pasar evento al padre para permitir rotar la cámara
                if self.temp_first_node_id is not None:
                    self.temp_first_node_id = None
                    self._refresh_scatter_colors()
                super().mousePressEvent(ev)
                
        else:
            # Modo Selección Normal
            if clicked_id is not None:
                modifiers = ev.modifiers()
                is_ctrl = modifiers & Qt.KeyboardModifier.ControlModifier
                
                if is_ctrl:
                    if clicked_id in self.selected_ids: self.selected_ids.remove(clicked_id)
                    else: self.selected_ids.add(clicked_id)
                else:
                    self.selected_ids = {clicked_id}
                
                self._refresh_scatter_colors()
                self.nodeSelectionChanged.emit(self.selected_ids)
                ev.accept()
            else:
                # Clic en el vacío (sin Ctrl) limpia selección
                modifiers = ev.modifiers()
                if not (modifiers & Qt.KeyboardModifier.ControlModifier):
                    if self.selected_ids:
                        self.selected_ids.clear()
                        self.nodeSelectionChanged.emit(self.selected_ids)
                        self._refresh_scatter_colors()
                
                # Permitir interacción nativa (rotar cámara)
                super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        # Mantener lógica original de Snap para visualización, 
        # pero usamos el ray casting para detectar proximidad
        super().mouseMoveEvent(ev)
        
        w, h = self.width(), self.height()
        if w <= 0: return

        ray_origin, ray_dir = self._get_mouse_ray(ev.position().x(), ev.position().y())
        
        closest_node_dist = 9999
        snapped_node = None
        
        # Snap visual (más permisivo que el click)
        for node in self.full_nodes_data:
            nid, nx, ny, nz = node
            P = QVector3D(float(nx), float(ny), float(nz))
            AP = P - ray_origin
            proj = QVector3D.dotProduct(AP, ray_dir)
            if proj < 0: continue
            closest_point_on_ray = ray_origin + ray_dir * proj
            dist_3d = (P - closest_point_on_ray).length()
            
            if dist_3d < 2.0 and dist_3d < closest_node_dist:
                closest_node_dist = dist_3d
                snapped_node = node
        
        if snapped_node:
            self.mouseMovedSignal.emit(snapped_node[1], snapped_node[2], snapped_node[3], True)
        else:
            # Proyección al plano Z=0 para referencia
            if abs(ray_dir.z()) > 1e-6:
                t = -ray_origin.z() / ray_dir.z()
                intersection = ray_origin + ray_dir * t
                self.mouseMovedSignal.emit(intersection.x(), intersection.y(), intersection.z(), False)

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