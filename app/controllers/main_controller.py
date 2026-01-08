#
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QAction

from app.models.document_model import DocumentModel
from app.views.main_window import MainWindow
from app.views.dialogs import AddNodeDialog, AddMaterialDialog

class MainController:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.model = DocumentModel()
        self.window = MainWindow()
        
        self._connect_signals()
        
    def _connect_signals(self):
        # 1. Toolbar Connections
        toolbar = self.window.findChild(object, "Main Toolbar")
        
        # Add Node
        add_node_action = QAction("Add Node", self.window)
        add_node_action.triggered.connect(self.open_add_node_dialog)
        toolbar.addAction(add_node_action)
        
        # Add Frame
        self.add_frame_action = QAction("Add Frame", self.window)
        self.add_frame_action.setCheckable(True)
        self.add_frame_action.triggered.connect(self.toggle_add_frame_mode)
        toolbar.addAction(self.add_frame_action)
        
        # Delete Action (Generic for Nodes and Frames)
        self.delete_action = QAction("Delete Selected", self.window)
        self.delete_action.setEnabled(False)
        self.delete_action.triggered.connect(self.delete_selected_items)
        toolbar.addAction(self.delete_action)

        # 2. Menu View Connections
        self.window.view_axes_action.triggered.connect(self.toggle_axes)
        self.window.view_node_ids_action.triggered.connect(self.toggle_node_ids)
        self.window.view_frame_ids_action.triggered.connect(self.toggle_frame_ids)
        
        # 3. Menu Define Connections
        self.window.define_material_action.triggered.connect(self.open_add_material_dialog)

        # 4. General Connections (Tree)
        self.window.work_tree.itemSelected.connect(self.on_tree_item_selected)
        
        # 5. Viewport Signals (Selection & Creation)
        viewport = self.window.central_container.viewport
        viewport.nodeSelectionChanged.connect(self.on_viewport_node_selection)
        viewport.frameSelectionChanged.connect(self.on_viewport_frame_selection) # Nueva conexión Frames
        viewport.createFrameSignal.connect(self.on_create_frame)
        
        # 6. Table Signals (Bi-directional selection)
        self.window.node_table.selectionChanged.connect(self.on_node_table_selection)
        self.window.element_table.selectionChanged.connect(self.on_frame_table_selection) # Nueva conexión Tabla Frames

    # --- MATERIALS ---
    def open_add_material_dialog(self):
        dialog = AddMaterialDialog(self.window)
        if dialog.exec():
            name, e, nu, rho = dialog.get_data()
            mat_id = self.model.add_material(name, e, nu, rho)
            
            msg = f">> Material Added: ID {mat_id} [{name}] E={e} v={nu}"
            self.window.terminal.print_message(msg)
            
            # Actualizar tabla si es visible
            if self.window.material_table.isVisible():
                self.window.material_table.update_data(self.model.get_materials_data())

    # --- VIEW ACTIONS ---
    def toggle_axes(self, checked):
        self.window.central_container.viewport.toggle_axes(checked)

    def toggle_node_ids(self, checked):
        self.window.central_container.viewport.toggle_node_ids(checked)

    def toggle_frame_ids(self, checked):
        self.window.central_container.viewport.toggle_frame_ids(checked)

    # --- EDITING LOGIC ---
    def toggle_add_frame_mode(self, checked):
        self.window.central_container.viewport.set_add_frame_mode(checked)
        if checked:
            self.window.statusBar().showMessage("Mode: Add Frame (Click Start Node -> Click End Node)")
        else:
            self.window.statusBar().showMessage("Ready")

    def on_create_frame(self, n1, n2):
        elem_id = self.model.add_element(n1, n2)
        if elem_id:
            msg = f">> Frame Added: ID {elem_id} (Connects Node {n1} - Node {n2})"
            self.window.terminal.print_message(msg)
            self._refresh_all_views()
        else:
            self.window.statusBar().showMessage("Invalid Frame (Exists or same node)", 3000)

    # --- PANEL SWITCHING ---
    def on_tree_item_selected(self, item_name):
        # Viewport reference
        vp = self.window.central_container.viewport
        
        if item_name == "Geometry":
            self.window.set_right_panel("Geometry")
            _, full_data = self.model.get_nodes_data()
            self.window.node_table.update_data(full_data)
            # Sincronizar selección actual
            self.window.node_table.select_rows_by_ids(vp.selected_node_ids)
        
        elif item_name == "Elements": 
            self.window.set_right_panel("Elements")
            elements = self.model.get_elements_data()
            self.window.element_table.update_data(elements)
            # Sincronizar selección actual
            self.window.element_table.select_rows_by_ids(vp.selected_frame_ids)
            
        elif item_name == "Materials": 
            self.window.set_right_panel("Materials")
            materials = self.model.get_materials_data()
            self.window.material_table.update_data(materials)
            
        else:
            self.window.set_right_panel("Editor")

    # --- SELECTION LOGIC (Unified) ---
    def on_viewport_node_selection(self, selected_ids):
        # Si la tabla de nodos está visible, sincronizarla
        if self.window.node_table.isVisible():
            self.window.node_table.select_rows_by_ids(selected_ids)
        self.update_delete_button_state()

    def on_viewport_frame_selection(self, selected_ids):
        # Si la tabla de elementos está visible, sincronizarla
        if self.window.element_table.isVisible():
            self.window.element_table.select_rows_by_ids(selected_ids)
        self.update_delete_button_state()

    def on_node_table_selection(self, selected_ids):
        # Tabla Nodos -> Viewport
        self.window.central_container.viewport.set_selection(node_ids=selected_ids)
        self.update_delete_button_state()

    def on_frame_table_selection(self, selected_ids):
        # Tabla Frames -> Viewport
        self.window.central_container.viewport.set_selection(frame_ids=selected_ids)
        self.update_delete_button_state()

    def update_delete_button_state(self):
        # Habilita el botón borrar si hay CUALQUIER cosa seleccionada (nodos o frames)
        vp = self.window.central_container.viewport
        n_count = len(vp.selected_node_ids)
        f_count = len(vp.selected_frame_ids)
        total = n_count + f_count
        
        if total > 0:
            self.delete_action.setEnabled(True)
            self.delete_action.setText(f"Delete ({total})")
        else:
            self.delete_action.setEnabled(False)
            self.delete_action.setText("Delete Selected")

    # --- DELETE LOGIC ---
    def delete_selected_items(self):
        """Elimina tanto los Nodos como los Frames seleccionados en el Viewport."""
        vp = self.window.central_container.viewport
        
        # Copiar sets para evitar errores de iteración al modificar
        nodes_to_del = vp.selected_node_ids.copy()
        frames_to_del = vp.selected_frame_ids.copy()
        
        if not nodes_to_del and not frames_to_del: return

        # 1. Eliminar Frames seleccionados primero
        for fid in frames_to_del:
            self.model.delete_element(fid)
            self.window.terminal.print_message(f">> Frame {fid} deleted.")
            
        # 2. Eliminar Nodos seleccionados
        # (El modelo debería encargarse de borrar frames conectados a estos nodos si existieran)
        for nid in nodes_to_del:
            self.model.delete_node(nid)
            self.window.terminal.print_message(f">> Node {nid} deleted.")
            
        # Limpiar selección en Viewport
        vp.set_selection(node_ids=[], frame_ids=[])
        
        # Refrescar todo
        self._refresh_all_views()
        self.update_delete_button_state()

    # --- ADD NODE LOGIC ---
    def open_add_node_dialog(self):
        dialog = AddNodeDialog(self.window)
        if dialog.exec():
            x, y, z = dialog.get_coordinates()
            node_id = self.model.add_node(x, y, z)
            
            msg = f">> Joint Added: ID {node_id} at (X: {x:.2f}, Y: {y:.2f}, Z: {z:.2f})"
            self.window.terminal.print_message(msg)
            
            self._refresh_all_views()
            
            # Ajustar Grid automáticamente al nuevo tamaño
            bounds = self.model.get_model_bounds()
            self.window.central_container.viewport.auto_adjust_grid(bounds)

    def _refresh_all_views(self):
        """Sincroniza Modelo -> Vista (Viewport y Tablas)"""
        coords, full_node_data = self.model.get_nodes_data()
        elements_data = self.model.get_elements_data()
        
        # 1. Actualizar Gráficos 3D
        self.window.central_container.viewport.update_scene_data(full_node_data, elements_data)
        
        # 2. Actualizar Grid (por si se borró algo y cambió el tamaño)
        bounds = self.model.get_model_bounds()
        self.window.central_container.viewport.auto_adjust_grid(bounds)
        
        # 3. Actualizar Tablas
        self.window.node_table.update_data(full_node_data)
        self.window.element_table.update_data(elements_data)

    def run(self):
        self.window.show()
        sys.exit(self.app.exec())