import numpy as np

class DocumentModel:
    def __init__(self):
        self.nodes = [] 
        self.elements = []
        self.materials = [] # Lista de materiales
        
        self.next_node_id = 1
        self.next_element_id = 1
        self.next_material_id = 1 

    def add_node(self, x, y, z):
        node_id = self.next_node_id
        self.nodes.append((node_id, x, y, z))
        self.next_node_id += 1
        return node_id

    def add_element(self, n_start_id, n_end_id):
        if n_start_id == n_end_id:
            return None
        
        # Verificar duplicados (A-B o B-A)
        for e in self.elements:
            if (e[1] == n_start_id and e[2] == n_end_id) or (e[1] == n_end_id and e[2] == n_start_id):
                return None 

        elem_id = self.next_element_id
        self.elements.append((elem_id, n_start_id, n_end_id))
        self.next_element_id += 1
        return elem_id
    
    def add_material(self, name, E, nu, rho):
        mat_id = self.next_material_id
        # Estructura: (ID, Name, E, Nu, Density)
        self.materials.append((mat_id, name, E, nu, rho))
        self.next_material_id += 1
        return mat_id

    def delete_node(self, node_id):
        self.nodes = [n for n in self.nodes if n[0] != node_id]
        # Eliminar elementos conectados al nodo borrado
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

    # --- NUEVO: Cálculo de la "Caja" del modelo para escalar el Grid ---
    def get_model_bounds(self):
        """Devuelve (min_x, max_x, min_y, max_y, min_z, max_z)"""
        if not self.nodes:
            # Valores por defecto si está vacío para mantener un grid visible
            return (-10, 10, -10, 10, 0, 0)
            
        coords = np.array([n[1:] for n in self.nodes])
        
        min_x, min_y, min_z = np.min(coords, axis=0)
        max_x, max_y, max_z = np.max(coords, axis=0)
        
        return (min_x, max_x, min_y, max_y, min_z, max_z)