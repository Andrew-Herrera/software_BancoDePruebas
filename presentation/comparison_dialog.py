# presentation/comparison_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
    QTreeWidgetItem, QPushButton, QLineEdit, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor

class ComparisonDialog(QDialog):
    def __init__(self, parent, config: dict, texts: dict, controller=None):
        super().__init__(parent)
        self.config = config
        self.t = texts
        self.controller = controller
        self.selected_experiments = []
        
        self.setWindowTitle(self.t.get("compare_btn", "Historial SQL y Comparador"))
        self.resize(980, 500)
        
        if parent and hasattr(parent, 'styleSheet'):
            self.setStyleSheet(parent.styleSheet())
            
        self._setup_ui()
        self._populate_tree()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        filter_layout = QHBoxLayout()
        self.txt_filter_holder = QLineEdit()
        self.txt_filter_holder.setPlaceholderText("Filtrar por Sustrato (Holder)...")
        self.txt_filter_holder.textChanged.connect(self._filter_tree)
        
        self.txt_filter_cell = QLineEdit()
        self.txt_filter_cell.setPlaceholderText("Filtrar por Celda...")
        self.txt_filter_cell.textChanged.connect(self._filter_tree)
        
        # Conectar teclado táctil a los filtros
        if self.parent() and hasattr(self.parent(), 'evaluar_despliegue_teclado'):
            self.txt_filter_holder.mousePressEvent = lambda e: self.parent().evaluar_despliegue_teclado(self.txt_filter_holder, "alpha")
            self.txt_filter_cell.mousePressEvent = lambda e: self.parent().evaluar_despliegue_teclado(self.txt_filter_cell, "alpha")
            
        filter_layout.addWidget(self.txt_filter_holder)
        filter_layout.addWidget(self.txt_filter_cell)
        main_layout.addLayout(filter_layout)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Sustrato / Celda", "Voc[V]", "Isc[mA]", "Jsc[mA/cm²]", "FF[%]", "η[%]", "Fecha"])
        
        self.tree.setColumnWidth(0, 400)
        self.tree.setColumnWidth(1, 75)
        self.tree.setColumnWidth(2, 75)
        self.tree.setColumnWidth(3, 85)
        self.tree.setColumnWidth(4, 75)
        self.tree.setColumnWidth(5, 75)
        self.tree.header().setStretchLastSection(True)
        
        self.tree.itemChanged.connect(self._on_item_changed)
        main_layout.addWidget(self.tree)
        
        btn_layout = QHBoxLayout()
        self.btn_delete = QPushButton("Eliminar Selección")
        self.btn_delete.setStyleSheet("background-color: #C62828; color: white; font-weight: bold;")
        self.btn_delete.clicked.connect(self._delete_selected)
        btn_layout.addWidget(self.btn_delete)
        
        btn_layout.addStretch()
        self.btn_plot = QPushButton("Graficar Selección")
        self.btn_plot.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold;")
        self.btn_plot.clicked.connect(self._accept_selection)
        btn_layout.addWidget(self.btn_plot)
        
        main_layout.addLayout(btn_layout)

    def _format_metric(self, value, decimals=2, multiplier=1.0) -> str:
        if value is None or value == "":
            return "NaN"
        try:
            return f"{(float(value) * multiplier):.{decimals}f}"
        except (ValueError, TypeError):
            return "NaN"

    def _populate_tree(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        if not self.controller:
            self.tree.blockSignals(False)
            return
            
        history = self.controller.get_full_history()
        
        # Oredenamos para que lo más reciente quede al principio
        history.sort(key=lambda x: str(x.get("fecha_hora", "")), reverse=True)
        
        groups = {}
        sweep_collector = {}

        for row in history:
            holder = row.get("holder_id", "Desconocido")
            celda = row.get("cell_num", 0)
            irr = row.get("irradiancia_objetivo", 1000.0)
            t_amb = row.get("temperatura_amb", 25.0)
            t_obj = row.get("temperatura_obj", 25.0)
            notas = row.get("notas", "Sin notas")
            fecha_minuto = str(row.get("fecha_hora", ""))
            
            fecha_minuto = str(row.get("fecha_hora", ""))[:16] 
            group_key = f"{holder}_C{celda}_{fecha_minuto}"

            if group_key not in groups:
                parent_item = QTreeWidgetItem()
                # TÍTULO LIMPIO (Sin fecha aquí)
                parent_item.setText(0, f"{holder} Celda {celda} | ({irr} W/m² - T.Amb: {t_amb}°C - T.Sup: {t_obj}°C)")
                parent_item.setFlags(parent_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                parent_item.setCheckState(0, Qt.CheckState.Unchecked)
                
                if notas and notas.strip() != "Sin notas" and notas.strip() != "":
                    note_item = QTreeWidgetItem(parent_item)
                    note_item.setText(0, f"Nota: {notas}")
                    note_item.setForeground(0, QBrush(QColor("#64B5F6")))
                    note_item.setFlags(Qt.ItemFlag.NoItemFlags)
                
                self.tree.addTopLevelItem(parent_item)
                groups[group_key] = parent_item
                sweep_collector[group_key] = []

            sweep_collector[group_key].append(row)

        for group_key, parent_item in groups.items():
            sweeps = sweep_collector[group_key]
            sweeps.sort(key=lambda x: str(x.get("fecha_hora", ""))) 
            
            for local_idx, row in enumerate(sweeps, start=1):
                exp_id = row.get("exp_id")
                child = QTreeWidgetItem(parent_item)
                
                sentido_db = row.get("tipo_prueba", "Ida")
                dir_short = "Rev" if "Vuelta" in sentido_db or "Histéresis" in sentido_db else "Fwd"
                child.setText(0, f"Barrido {local_idx} ({dir_short})")
                
                child.setText(1, self._format_metric(row.get('voc'), 3))
                child.setText(2, self._format_metric(row.get('isc'), 2, 1000.0))
                child.setText(3, self._format_metric(row.get('jsc'), 2))
                child.setText(4, self._format_metric(row.get('ff'), 1))
                child.setText(5, self._format_metric(row.get('eficiencia'), 2))
                child.setText(6, str(row.get("fecha_hora", ""))[:16])

                for col in range(1, 6):
                    child.setTextAlignment(col, Qt.AlignmentFlag.AlignCenter)

                child.setData(0, Qt.ItemDataRole.UserRole, exp_id)
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Unchecked)

        self.tree.collapseAll()
        self.tree.blockSignals(False)

    def _on_item_changed(self, item, column):
        self.tree.blockSignals(True)
        state = item.checkState(0)
        if item.childCount() > 0:
            for i in range(item.childCount()): item.child(i).setCheckState(0, state)
        else:
            parent = item.parent()
            if parent:
                checked = sum(1 for i in range(parent.childCount()) if parent.child(i).checkState(0) == Qt.CheckState.Checked)
                if checked == 0: parent.setCheckState(0, Qt.CheckState.Unchecked)
                elif checked == parent.childCount(): parent.setCheckState(0, Qt.CheckState.Checked)
                else: parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
        self.tree.blockSignals(False)

    def _filter_tree(self):
        f_holder = self.txt_filter_holder.text().lower()
        f_cell = self.txt_filter_cell.text().lower()
        for i in range(self.tree.topLevelItemCount()):
            parent_item = self.tree.topLevelItem(i)
            p_text = parent_item.text(0).lower()
            parts = p_text.split("|")
            h_str = parts[0] if len(parts) > 0 else ""
            c_str = parts[1] if len(parts) > 1 else ""
            
            match_holder = f_holder in h_str
            match_cell = f_cell in c_str
            parent_item.setHidden(not (match_holder and match_cell))

    def _delete_selected(self):
        ids = self._get_checked_experiment_ids()
        if not ids: return
        reply = QMessageBox.question(self, "Eliminar", "¿Borrar registros?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes and self.controller:
            if self.controller.delete_experiments(ids): self._populate_tree()

    def _accept_selection(self):
        self.selected_experiments = self._get_checked_experiment_ids()
        self.accept()

    def _get_checked_experiment_ids(self) -> list:
        checked_ids = []
        for i in range(self.tree.topLevelItemCount()):
            parent_item = self.tree.topLevelItem(i)
            for j in range(parent_item.childCount()):
                child = parent_item.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    exp_id = child.data(0, Qt.ItemDataRole.UserRole)
                    if exp_id is not None: checked_ids.append(exp_id)
        return checked_ids