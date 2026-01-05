from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QDoubleSpinBox, 
                             QDialogButtonBox, QLineEdit, QLabel)

class AddNodeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Node")
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.spin_x = QDoubleSpinBox()
        self.spin_y = QDoubleSpinBox()
        self.spin_z = QDoubleSpinBox()
        
        for spin in [self.spin_x, self.spin_y, self.spin_z]:
            spin.setRange(-10000.0, 10000.0)
            spin.setSingleStep(1.0)
            
        form.addRow("Coord X:", self.spin_x)
        form.addRow("Coord Y:", self.spin_y)
        form.addRow("Coord Z:", self.spin_z)
        
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)
        
    def get_coordinates(self):
        return self.spin_x.value(), self.spin_y.value(), self.spin_z.value()

# --- NUEVO DIÁLOGO ---
class AddMaterialDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Material")
        self.resize(300, 200)
        
        layout = QVBoxLayout()
        form = QFormLayout()
        
        # Inputs
        self.input_name = QLineEdit("Concrete")
        
        self.input_e = QDoubleSpinBox()
        self.input_e.setRange(0, 1e12) # Rango grande para Modulo Elastico
        self.input_e.setValue(30000)   # Valor por defecto
        self.input_e.setSuffix(" MPa")
        
        self.input_nu = QDoubleSpinBox()
        self.input_nu.setRange(0, 0.5)
        self.input_nu.setSingleStep(0.05)
        self.input_nu.setValue(0.2)
        
        self.input_rho = QDoubleSpinBox()
        self.input_rho.setRange(0, 100000)
        self.input_rho.setValue(25) # kN/m3 aprox
        self.input_rho.setSuffix(" kN/m³")

        form.addRow("Name:", self.input_name)
        form.addRow("Elastic Modulus (E):", self.input_e)
        form.addRow("Poisson Ratio (v):", self.input_nu)
        form.addRow("Density (ρ):", self.input_rho)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
    def get_data(self):
        return (self.input_name.text(), 
                self.input_e.value(), 
                self.input_nu.value(), 
                self.input_rho.value())