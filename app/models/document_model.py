import numpy as np

class DocumentModel:
    def __init__(self):
        self.nodes = [] 
        self.elements = []
        self.materials = [] # NUEVO: Lista de materiales
        
        self.next_node_id = 1
        self.next_element_id = 1
        self.next_material_id = 1 # NUEVO: ID autoincremental

    def add_node(self, x, y, z):
        node_id = self.next_node_id
        self.nodes.append((node_id, x, y, z))
        self.next_node_id += 1
        return node_id

    def add_element(self, n_start_id, n_end_id):
        if n_start_id == n_end_id:
            return None
        
        for e in self.elements:
            if (e[1] == n_start_id and e[2] == n_end_id) or (e[1] == n_end_id and e[2] == n_start_id):
                return None 

        elem_id = self.next_element_id
        # Por ahora el elemento solo guarda nodos, luego guardará material_id y section_id
        self.elements.append((elem_id, n_start_id, n_end_id))
        self.next_element_id += 1
        return elem_id
    
    # --- NUEVO: Gestión de Materiales ---
    def add_material(self, name, E, nu, rho):
        mat_id = self.next_material_id
        # Estructura: (ID, Name, E, Nu, Density)
        self.materials.append((mat_id, name, E, nu, rho))
        self.next_material_id += 1
        return mat_id

    def delete_node(self, node_id):
        self.nodes = [n for n in self.nodes if n[0] != node_id]
        self.elements = [e for e in self.elements if e[1] != node_id and e[2] != node_id]

    def delete_element(self, element_id):
        self.elements = [e for e in self.elements if e[0] != element_id]

    def get_nodes_data(self):
        if not self.nodes:
            return np.zeros((0, 3)), []
        coords = np.array([n[1:] for n in self.nodes], dtype=np.float32)
        return coords, self.nodes

    def get_elements_data(self):
        return self.elements
        
    def get_materials_data(self):
        return self.materials