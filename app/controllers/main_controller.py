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

        # --- NUEVO: Box Selection Action ---
        self.box_select_action = QAction("Box Select", self.window)
        self.box_select_action.setCheckable(True)
        self.box_select_action.triggered.connect(self.toggle_box_selection)
        toolbar.addAction(self.box_select_action)
        
        # Delete Action
        self.delete_action = QAction("Delete Selected", self.window)
        self.delete_action.setEnabled(False)
        self.delete_action.triggered.connect(self.delete_selected_items)
        toolbar.addAction(self.delete_action)

        # 2. Menu View Connections
        self.window.view_axes_action.triggered.connect(self.toggle_axes)
        self.window.view_node_ids_action.triggered.connect(self.toggle_node_ids)
        self.window.view_frame_ids_action.triggered.connect(self.toggle_frame_ids)
        
        # 3. Define Connections
        self.window.define_material_action.triggered.connect(self.open_add_material_dialog)

        # 4. Viewport & Table Connections
        viewport = self.window.central_container.viewport
        viewport.nodeSelectionChanged.connect(self.on_viewport_node_selection)
        viewport.frameSelectionChanged.connect(self.on_viewport_frame_selection)
        viewport.createFrameSignal.connect(self.on_create_frame)
        
        self.window.node_table.selectionChanged.connect(self.on_node_table_selection)
        self.window.element_table.selectionChanged.connect(self.on_frame_table_selection)
        self.window.work_tree.itemSelected.connect(self.on_tree_item_selected)

    # --- MODOS DE INTERACCIÓN ---
    
    def toggle_add_frame_mode(self, checked):
        # Exclusividad: Si activo add frame, desactivo box select
        if checked:
            if self.box_select_action.isChecked():
                self.box_select_action.setChecked(False)
                self.window.central_container.viewport.set_box_selection_mode(False)
            self.window.statusBar().showMessage("Mode: Add Frame (Click Start Node -> Click End Node)")
        else:
            self.window.statusBar().showMessage("Ready")
            
        self.window.central_container.viewport.set_add_frame_mode(checked)

    def toggle_box_selection(self, checked):
        # Exclusividad: Si activo box select, desactivo add frame
        if checked:
            if self.add_frame_action.isChecked():
                self.add_frame_action.setChecked(False)
                self.window.central_container.viewport.set_add_frame_mode(False)
            self.window.statusBar().showMessage("Mode: Box Selection (Drag mouse to select)")
        else:
            self.window.statusBar().showMessage("Ready")
            
        self.window.central_container.viewport.set_box_selection_mode(checked)

    # --- MATERIALS ---
    def open_add_material_dialog(self):
        dialog = AddMaterialDialog(self.window)
        if dialog.exec():
            name, e, nu, rho = dialog.get_data()
            mat_id = self.model.add_material(name, e, nu, rho)
            self.window.terminal.print_message(f">> Material Added: {name}")
            if self.window.material_table.isVisible():
                self.window.material_table.update_data(self.model.get_materials_data())

    # --- VIEW ACTIONS ---
    def toggle_axes(self, checked):
        self.window.central_container.viewport.toggle_axes(checked)
    def toggle_node_ids(self, checked):
        self.window.central_container.viewport.toggle_node_ids(checked)
    def toggle_frame_ids(self, checked):
        self.window.central_container.viewport.toggle_frame_ids(checked)

    # --- CREATE FRAME ---
    def on_create_frame(self, n1, n2):
        elem_id = self.model.add_element(n1, n2)
        if elem_id:
            self.window.terminal.print_message(f">> Frame Added: ID {elem_id}")
            self._refresh_all_views()
        else:
            self.window.statusBar().showMessage("Invalid Frame", 3000)

    # --- SELECTION & DELETE ---
    def on_viewport_node_selection(self, selected_ids):
        if self.window.node_table.isVisible():
            self.window.node_table.select_rows_by_ids(selected_ids)
        self.update_delete_button_state()

    def on_viewport_frame_selection(self, selected_ids):
        if self.window.element_table.isVisible():
            self.window.element_table.select_rows_by_ids(selected_ids)
        self.update_delete_button_state()

    def on_node_table_selection(self, selected_ids):
        self.window.central_container.viewport.set_selection(node_ids=selected_ids)
        self.update_delete_button_state()

    def on_frame_table_selection(self, selected_ids):
        self.window.central_container.viewport.set_selection(frame_ids=selected_ids)
        self.update_delete_button_state()

    def update_delete_button_state(self):
        vp = self.window.central_container.viewport
        count = len(vp.selected_node_ids) + len(vp.selected_frame_ids)
        if count > 0:
            self.delete_action.setEnabled(True)
            self.delete_action.setText(f"Delete ({count})")
        else:
            self.delete_action.setEnabled(False)
            self.delete_action.setText("Delete Selected")

    def delete_selected_items(self):
        vp = self.window.central_container.viewport
        nodes = vp.selected_node_ids.copy()
        frames = vp.selected_frame_ids.copy()
        
        for fid in frames:
            self.model.delete_element(fid)
            self.window.terminal.print_message(f">> Frame {fid} deleted.")
        for nid in nodes:
            self.model.delete_node(nid)
            self.window.terminal.print_message(f">> Node {nid} deleted.")
            
        vp.set_selection([], [])
        self._refresh_all_views()
        self.update_delete_button_state()

    # --- PANELS ---
    def on_tree_item_selected(self, item_name):
        vp = self.window.central_container.viewport
        if item_name == "Geometry":
            self.window.set_right_panel("Geometry")
            _, full_data = self.model.get_nodes_data()
            self.window.node_table.update_data(full_data)
            self.window.node_table.select_rows_by_ids(vp.selected_node_ids)
        elif item_name == "Elements": 
            self.window.set_right_panel("Elements")
            elements = self.model.get_elements_data()
            self.window.element_table.update_data(elements)
            self.window.element_table.select_rows_by_ids(vp.selected_frame_ids)
        elif item_name == "Materials":
            self.window.set_right_panel("Materials")
            materials = self.model.get_materials_data()
            self.window.material_table.update_data(materials)
        else:
            self.window.set_right_panel("Editor")

    # --- ADD NODE & REFRESH ---
    def open_add_node_dialog(self):
        dialog = AddNodeDialog(self.window)
        if dialog.exec():
            x, y, z = dialog.get_coordinates()
            nid = self.model.add_node(x, y, z)
            self.window.terminal.print_message(f">> Joint Added: {nid}")
            self._refresh_all_views()
            # Ajustar grid solo si es necesario (opcional)
            self.window.central_container.viewport.auto_adjust_grid(self.model.get_model_bounds())

    def _refresh_all_views(self):
        coords, nodes = self.model.get_nodes_data()
        elems = self.model.get_elements_data()
        self.window.central_container.viewport.update_scene_data(nodes, elems)
        self.window.node_table.update_data(nodes)
        self.window.element_table.update_data(elems)
        self.window.central_container.viewport.auto_adjust_grid(self.model.get_model_bounds())

    def run(self):
        self.window.show()
        sys.exit(self.app.exec())