import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QAction

from app.models.document_model import DocumentModel
from app.views.main_window import MainWindow
from app.views.dialogs import AddNodeDialog, AddMaterialDialog # Importar nuevo dialogo

class MainController:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.model = DocumentModel()
        self.window = MainWindow()
        
        self._connect_signals()
        
    def _connect_signals(self):
        # 1. Toolbar Connections
        toolbar = self.window.findChild(object, "Main Toolbar")
        
        add_node_action = QAction("Add Node", self.window)
        add_node_action.triggered.connect(self.open_add_node_dialog)
        toolbar.addAction(add_node_action)
        
        self.add_frame_action = QAction("Add Frame", self.window)
        self.add_frame_action.setCheckable(True)
        self.add_frame_action.triggered.connect(self.toggle_add_frame_mode)
        toolbar.addAction(self.add_frame_action)
        
        self.delete_action = QAction("Delete Selected", self.window)
        self.delete_action.setEnabled(False)
        self.delete_action.triggered.connect(self.delete_selected_nodes)
        toolbar.addAction(self.delete_action)

        # 2. Menu View Connections
        self.window.view_axes_action.triggered.connect(self.toggle_axes)
        self.window.view_node_ids_action.triggered.connect(self.toggle_node_ids)
        self.window.view_frame_ids_action.triggered.connect(self.toggle_frame_ids)
        
        # 3. NUEVO: Menu Define Connections
        self.window.define_material_action.triggered.connect(self.open_add_material_dialog)

        # 4. General Connections
        self.window.work_tree.itemSelected.connect(self.on_tree_item_selected)
        
        self.window.central_container.viewport.nodeSelectionChanged.connect(self.on_viewport_selection)
        self.window.central_container.viewport.createFrameSignal.connect(self.on_create_frame)
        self.window.node_table.selectionChanged.connect(self.on_table_selection)

    # --- NUEVA LÓGICA DE MATERIALES ---
    def open_add_material_dialog(self):
        dialog = AddMaterialDialog(self.window)
        if dialog.exec():
            # Obtener datos del dialogo
            name, e, nu, rho = dialog.get_data()
            
            # Guardar en modelo
            mat_id = self.model.add_material(name, e, nu, rho)
            
            # Feedback
            msg = f">> Material Added: ID {mat_id} [{name}] E={e} v={nu}"
            self.window.terminal.print_message(msg)
            
            # Si el panel de materiales está visible, actualizarlo
            if self.window.material_table.isVisible():
                self.window.material_table.update_data(self.model.get_materials_data())

    # --- View Actions ---
    def toggle_axes(self, checked):
        self.window.central_container.viewport.toggle_axes(checked)

    def toggle_node_ids(self, checked):
        self.window.central_container.viewport.toggle_node_ids(checked)

    def toggle_frame_ids(self, checked):
        self.window.central_container.viewport.toggle_frame_ids(checked)

    # --- Editing Logic ---
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

    def on_tree_item_selected(self, item_name):
        if item_name == "Geometry":
            self.window.set_right_panel("Geometry")
            _, full_data = self.model.get_nodes_data()
            self.window.node_table.update_data(full_data)
            current_selection = self.window.central_container.viewport.selected_ids
            self.window.node_table.select_rows_by_ids(current_selection)
        
        elif item_name == "Elements": 
            self.window.set_right_panel("Elements")
            elements = self.model.get_elements_data()
            self.window.element_table.update_data(elements)
            
        elif item_name == "Materials": # <--- NUEVO CASO
            self.window.set_right_panel("Materials")
            materials = self.model.get_materials_data()
            self.window.material_table.update_data(materials)
            
        else:
            self.window.set_right_panel("Editor")

    def on_viewport_selection(self, selected_ids_set):
        if self.add_frame_action.isChecked():
            return 
        count = len(selected_ids_set)
        if count > 0:
            self.delete_action.setEnabled(True)
            self.delete_action.setText(f"Delete ({count})")
        else:
            self.delete_action.setEnabled(False)
            self.delete_action.setText("Delete Selected")
            
        if self.window.node_table.isVisible():
            self.window.node_table.select_rows_by_ids(selected_ids_set)

    def on_table_selection(self, selected_ids_list):
        self.window.central_container.viewport.set_selection(selected_ids_list)
        count = len(selected_ids_list)
        if count > 0:
            self.delete_action.setEnabled(True)
            self.delete_action.setText(f"Delete ({count})")
        else:
            self.delete_action.setEnabled(False)
            self.delete_action.setText("Delete Selected")

    def delete_selected_nodes(self):
        ids_to_delete = self.window.central_container.viewport.selected_ids.copy()
        if not ids_to_delete: return

        for nid in ids_to_delete:
            self.model.delete_node(nid)
            self.window.terminal.print_message(f">> Node {nid} deleted.")
            
        self._refresh_all_views()
        self.window.central_container.viewport.set_selection([])
        self.delete_action.setEnabled(False)
        self.delete_action.setText("Delete Selected")

    def open_add_node_dialog(self):
        dialog = AddNodeDialog(self.window)
        if dialog.exec():
            x, y, z = dialog.get_coordinates()
            node_id = self.model.add_node(x, y, z)
            msg = f">> Joint Added: ID {node_id} at (X: {x:.2f}, Y: {y:.2f}, Z: {z:.2f})"
            self.window.terminal.print_message(msg)
            self._refresh_all_views()

    def _refresh_all_views(self):
        coords, full_data = self.model.get_nodes_data()
        elements = self.model.get_elements_data()
        
        self.window.central_container.viewport.update_scene_data(full_data, elements)
        self.window.node_table.update_data(full_data)
        self.window.element_table.update_data(elements)
        # No hace falta refrescar tabla materiales aqui porque no cambian desde el viewport

    def run(self):
        self.window.show()
        sys.exit(self.app.exec())