from PyQt6.QtWidgets import QMainWindow, QDockWidget, QToolBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

# Importamos la nueva tabla MaterialTableWidget
from .components import WorkTreeWidget, TerminalWidget, ScriptEditorWidget, CentralViewContainer, NodeTableWidget, ElementTableWidget, MaterialTableWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STKO Clone (Python + PyQt6)")
        self.resize(1280, 720)
        
        self.central_container = CentralViewContainer()
        self.setCentralWidget(self.central_container)
        
        # Acciones para el controlador
        self.view_axes_action = None
        self.view_node_ids_action = None
        self.view_frame_ids_action = None
        
        # Acciones de Definición (NUEVAS)
        self.define_material_action = None

        self._create_menu_bar()
        self._create_toolbar()
        
        # Crear Docks
        self.dock_left = QDockWidget("Work Tree", self)
        self.work_tree = WorkTreeWidget() 
        self.dock_left.setWidget(self.work_tree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_left)
        
        self.dock_right = QDockWidget("Editor", self)
        self.script_editor = ScriptEditorWidget()
        self.node_table = NodeTableWidget()
        self.element_table = ElementTableWidget() 
        self.material_table = MaterialTableWidget() # <--- NUEVO WIDGET
        
        self.dock_right.setWidget(self.script_editor) 
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_right)
        
        # Terminal
        self.dock_bottom = QDockWidget("Terminal", self)
        self.terminal = TerminalWidget() 
        self.dock_bottom.setWidget(self.terminal)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_bottom)
        
        self.statusBar().showMessage("Ready")

    def set_right_panel(self, widget_name):
        if widget_name == "Geometry":
            self.dock_right.setWindowTitle("Geometry / Nodes")
            self.dock_right.setWidget(self.node_table)
        elif widget_name == "Elements": 
            self.dock_right.setWindowTitle("Elements / Frames")
            self.dock_right.setWidget(self.element_table)
        elif widget_name == "Materials": # <--- NUEVO PANEL
            self.dock_right.setWindowTitle("Materials Definition")
            self.dock_right.setWidget(self.material_table)
        else:
            self.dock_right.setWindowTitle("Script Editor")
            self.dock_right.setWidget(self.script_editor)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        
        # File
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction("Exit", self.close)

        # View
        view_menu = menu_bar.addMenu("View")
        self.view_axes_action = QAction("Show Axes / Grid", self)
        self.view_axes_action.setCheckable(True)
        self.view_axes_action.setChecked(True) 
        view_menu.addAction(self.view_axes_action)
        view_menu.addSeparator()
        self.view_node_ids_action = QAction("Show Node IDs", self)
        self.view_node_ids_action.setCheckable(True)
        view_menu.addAction(self.view_node_ids_action)
        self.view_frame_ids_action = QAction("Show Frame IDs", self)
        self.view_frame_ids_action.setCheckable(True)
        view_menu.addAction(self.view_frame_ids_action)

        # --- NUEVO MENÚ "DEFINE" ---
        define_menu = menu_bar.addMenu("Define")
        
        # Submenú Materials
        materials_menu = define_menu.addMenu("Materials")
        self.define_material_action = QAction("Add New Material...", self)
        materials_menu.addAction(self.define_material_action)
        
        # Submenú Sections (Placeholder por ahora)
        sections_menu = define_menu.addMenu("Sections")
        sections_menu.addAction("Add New Section... (Coming Soon)")

    def _create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setObjectName("Main Toolbar")
        self.addToolBar(toolbar)