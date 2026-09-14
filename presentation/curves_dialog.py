# presentation/curves_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QTreeWidget, QTreeWidgetItem, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor

class CurvesDialog(QDialog):
    def __init__(self, parent, curve_metadata: dict, mode: int, b_per_hr: int, config: dict, texts: dict):
        super().__init__(parent)
        self.curve_metadata = curve_metadata
        self.mode = mode
        self.b_per_hr = b_per_hr
        self.config = config
        self.t = texts
        
        self.setWindowTitle(self.t.get("curves_mgr_title", "Gestor y Filtro de Curvas"))
        self.resize(400, 520)
        if parent and hasattr(parent, 'styleSheet'):
            self.setStyleSheet(parent.styleSheet())
        self._setup_ui()
        self._populate_tree()

    def _setup_ui(self):
        self.ly = QVBoxLayout(self)
        self.chk_master = QCheckBox(self.t.get("select_all", "Seleccionar / Limpiar Todas"))
        self.chk_master.setTristate(True)
        color_texto = "white" if self.config.get('dark_mode', True) else "black"
        self.chk_master.setStyleSheet(f"color: {color_texto}; font-weight: bold; font-size: 14px;") 
        self.ly.addWidget(self.chk_master)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.ly.addWidget(self.tree)
        
        self.btn_cerrar = QPushButton(self.t.get("btn_accept", "Aceptar"))
        self.btn_cerrar.setFixedHeight(45)
        self.btn_cerrar.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; border-radius: 4px;")
        self.btn_cerrar.clicked.connect(self.accept)
        self.ly.addWidget(self.btn_cerrar)
        
        self.chk_master.stateChanged.connect(self._on_master_toggled)
        self.tree.itemChanged.connect(self._on_tree_item_changed)

    def _populate_tree(self):
        items_por_grupo = 10 if self.mode == 0 else self.b_per_hr
        grupos = {}
        total_curves = len(self.curve_metadata)
        visible_curves = 0
        
        self.tree.blockSignals(True)
        for key, meta in self.curve_metadata.items():
            idx_real = meta.get('idx_real', 1)
            is_historical = meta.get('hist', False) or meta.get('is_historical', False)
            
            # 1. Definir Título y Llave del Grupo (Histórico vs Nuevo)
            if is_historical:
                g_idx = meta.get('group_id', f"hist_{meta.get('exp_id', 'X')}")
                titulo = meta.get('group_name', f"Experimento {meta.get('exp_id', 'X')}")
            else:
                g_idx = (idx_real - 1) // items_por_grupo
                # Eliminamos la palabra "Hora", unificamos todo a "Lote"
                titulo = f"Lote {g_idx + 1} (S{g_idx * items_por_grupo + 1} - S{(g_idx + 1) * items_por_grupo})"
                
            # 2. Crear el Nodo Padre (Si no existe)
            if g_idx not in grupos:
                parent = QTreeWidgetItem(self.tree)
                parent.setText(0, titulo)
                parent.setFlags(parent.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                parent.setCheckState(0, Qt.CheckState.Unchecked) 
                
                # Si es histórico, todo el grupo comparte el mismo color, se lo asignamos al padre
                if is_historical:
                    parent.setForeground(0, QBrush(QColor(meta['color'])))
                    
                grupos[g_idx] = parent
            
            # 3. Crear el Nodo Hijo (Barrido individual)
            child = QTreeWidgetItem(grupos[g_idx])
            child.setText(0, meta.get('name', key))
            child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            
            is_visible = meta['line'].isVisible()
            child.setCheckState(0, Qt.CheckState.Checked if is_visible else Qt.CheckState.Unchecked) 
            if is_visible: visible_curves += 1
                
            child.setData(0, Qt.ItemDataRole.UserRole, key) 
            child.setForeground(0, QBrush(QColor(meta['color'])))
            
            # Si son datos nuevos, el padre toma el color del primer hijo para dar una pista visual
            if grupos[g_idx].childCount() == 1 and not is_historical:
                 grupos[g_idx].setForeground(0, QBrush(QColor(meta['color'])))
            
        self.tree.collapseAll()
        self.tree.blockSignals(False)
        
        self.chk_master.blockSignals(True)
        if total_curves > 0:
            if visible_curves == total_curves: self.chk_master.setCheckState(Qt.CheckState.Checked)
            elif visible_curves == 0: self.chk_master.setCheckState(Qt.CheckState.Unchecked)
            else: self.chk_master.setCheckState(Qt.CheckState.PartiallyChecked)
        self.chk_master.blockSignals(False)
        self._sincronizar_padres_inicial()

    def _sincronizar_padres_inicial(self):
        self.tree.blockSignals(True)
        for i in range(self.tree.topLevelItemCount()):
            padre = self.tree.topLevelItem(i)
            hijos_marcados = sum(1 for j in range(padre.childCount()) if padre.child(j).checkState(0) == Qt.CheckState.Checked)
            if hijos_marcados == padre.childCount(): padre.setCheckState(0, Qt.CheckState.Checked)
            elif hijos_marcados == 0: padre.setCheckState(0, Qt.CheckState.Unchecked)
            else: padre.setCheckState(0, Qt.CheckState.PartiallyChecked)
        self.tree.blockSignals(False)

    def _actualizar_master_checkbox(self):
        self.chk_master.blockSignals(True)
        visibles = sum(1 for meta in self.curve_metadata.values() if meta['line'].isVisible())
        if len(self.curve_metadata) > 0:
            if visibles == len(self.curve_metadata): self.chk_master.setCheckState(Qt.CheckState.Checked)
            elif visibles == 0: self.chk_master.setCheckState(Qt.CheckState.Unchecked)
            else: self.chk_master.setCheckState(Qt.CheckState.PartiallyChecked)
        self.chk_master.blockSignals(False)

    def _on_master_toggled(self, estado_val):
        estado = Qt.CheckState(estado_val) if isinstance(estado_val, int) else estado_val
        if estado == Qt.CheckState.PartiallyChecked:
            self.chk_master.setCheckState(Qt.CheckState.Checked)
            estado = Qt.CheckState.Checked
            
        self.tree.blockSignals(True)
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            parent.setCheckState(0, Qt.CheckState(estado))
            for j in range(parent.childCount()):
                child = parent.child(j)
                child.setCheckState(0, estado)
                c_key = child.data(0, Qt.ItemDataRole.UserRole)
                if c_key in self.curve_metadata:
                    self.curve_metadata[c_key]['line'].setVisible(estado == Qt.CheckState.Checked)
        self.tree.blockSignals(False)

    def _on_tree_item_changed(self, item, column):
        self.tree.blockSignals(True)
        estado_val = item.checkState(0)
        estado = Qt.CheckState(estado_val) if isinstance(estado_val, int) else estado_val
        c_key = item.data(0, Qt.ItemDataRole.UserRole)
        
        if c_key is not None: 
            if c_key in self.curve_metadata:
                self.curve_metadata[c_key]['line'].setVisible(estado == Qt.CheckState.Checked)
            padre = item.parent()
            if padre:
                hijos_marcados = sum(1 for i in range(padre.childCount()) if padre.child(i).checkState(0) == Qt.CheckState.Checked)
                if hijos_marcados == padre.childCount(): padre.setCheckState(0, Qt.CheckState.Checked)
                elif hijos_marcados == 0: padre.setCheckState(0, Qt.CheckState.Unchecked)
                else: padre.setCheckState(0, Qt.CheckState.PartiallyChecked)
        else: 
            if estado == Qt.CheckState.PartiallyChecked:
                estado = Qt.CheckState.Checked
                item.setCheckState(0, Qt.CheckState(estado))
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, estado)
                c_key_child = child.data(0, Qt.ItemDataRole.UserRole)
                if c_key_child in self.curve_metadata:
                    self.curve_metadata[c_key_child]['line'].setVisible(estado == Qt.CheckState.Checked)
                
        self._actualizar_master_checkbox()
        self.tree.blockSignals(False)