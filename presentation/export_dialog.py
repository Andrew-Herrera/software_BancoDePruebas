# presentation/export_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QTextEdit, QComboBox, QPushButton, 
    QFileDialog, QMessageBox, QLabel, QGroupBox, QCompleter
)
from PySide6.QtCore import Qt

class ExportDialog(QDialog):
    def __init__(self, parent, curve_metadata: dict, config: dict, texts: dict, controller=None):
        super().__init__(parent)
        self.curve_metadata = curve_metadata
        self.config = config
        self.t = texts
        self.controller = controller
        self.parent_win = parent
        
        self.visible_keys = [k for k, m in self.curve_metadata.items() if m['line'].isVisible()]
        visible_ints = {self.curve_metadata[k].get('idx_real', 1) for k in self.visible_keys}
        self.visible_reals = sorted(list(visible_ints))
        
        self.is_historical = any(self.curve_metadata[k].get('hist', False) for k in self.visible_keys)
        
        self.setWindowTitle(self.t.get("btn_export", "Exportar Datos y Reportes"))
        self.setFixedSize(500, 560)
        
        if parent and hasattr(parent, 'styleSheet'):
            self.setStyleSheet(parent.styleSheet())
            
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        self.grp_1 = QGroupBox(self.t.get("exp_grp1", "Trazos a Exportar (Visibles en Gráfica)"))
        ly_1 = QVBoxLayout(self.grp_1)
        lbl_ranges = QLabel(self._format_ranges(self.visible_reals))
        lbl_ranges.setStyleSheet("font-weight: bold; color: #1E88E5; font-size: 14px;")
        lbl_ranges.setWordWrap(True)
        ly_1.addWidget(lbl_ranges)
        main_layout.addWidget(self.grp_1)
        
        self.grp_2 = QGroupBox(self.t.get("exp_grp2", "Datos de la Celda Orgánica"))
        ly_2 = QFormLayout(self.grp_2)
        
        self.txt_holder = QLineEdit()
        self.txt_holder.setPlaceholderText("Ej. LOTE-01-A")
        
        # Autocompletado de base de datos
        if self.controller:
            holders_list = self.controller.db.get_all_holders()
            completer = QCompleter(holders_list, self)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.txt_holder.setCompleter(completer)
            
        self.cb_cell = QComboBox()
        self.cb_cell.addItems([str(i) for i in range(1, 17)])
        self.txt_area = QLineEdit("0.09")
        self.txt_author = QLineEdit(self.config.get("last_author", ""))
        self.txt_notes = QTextEdit()
        self.txt_notes.setFixedHeight(60)
        
        # Conectar teclado táctil a los campos (Adaptado para QTextEdit también)
        if hasattr(self.parent_win, 'evaluar_despliegue_teclado'):
            self.txt_holder.mousePressEvent = lambda e: self.parent_win.evaluar_despliegue_teclado(self.txt_holder, "alpha")
            self.txt_area.mousePressEvent = lambda e: self.parent_win.evaluar_despliegue_teclado(self.txt_area, "numeric")
            self.txt_author.mousePressEvent = lambda e: self.parent_win.evaluar_despliegue_teclado(self.txt_author, "alpha")
            self.txt_notes.mousePressEvent = lambda e: self.parent_win.evaluar_despliegue_teclado(self.txt_notes, "alpha")

        ly_2.addRow("ID del Holder / Muestra:", self.txt_holder)
        ly_2.addRow("Celda número:", self.cb_cell)
        ly_2.addRow("Área Activa [cm²]:", self.txt_area)
        ly_2.addRow("Autor / Operador:", self.txt_author)
        ly_2.addRow("Notas del Experimento:", self.txt_notes)
        main_layout.addWidget(self.grp_2)
        
        self.grp_3 = QGroupBox(self.t.get("exp_grp3", "Opciones de Destino y Formato"))
        ly_3 = QVBoxLayout(self.grp_3)
        self.cb_format = QComboBox()
        
        if self.is_historical:
            self.cb_format.addItems(["Exportar a CSV", "Exportar a Excel"])
            self.grp_1.hide()
            self.grp_2.hide()
            self.setFixedSize(400, 180)
        else:
            self.cb_format.addItems([
                "1) Guardar unicamente en Base de Datos Local",
                "2) Guardar en BD y exportar a CSV",
                "3) Guardar en BD y exportar a Excel"
            ])
            
        ly_3.addWidget(self.cb_format)
        main_layout.addWidget(self.grp_3)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_export = QPushButton("Procesar y Exportar")
        self.btn_export.setFixedSize(180, 40)
        self.btn_export.setStyleSheet("background-color: #1565C0; color: white; font-weight: bold; border-radius: 4px;")
        self.btn_export.clicked.connect(self._handle_export)
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setFixedSize(110, 40)
        self.btn_cancel.setStyleSheet("background-color: #C62828; color: white; font-weight: bold; border-radius: 4px;")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

    def _format_ranges(self, indices: list) -> str:
        if not indices: return "Ninguna"
        sorted_idx = sorted(indices)
        ranges = []
        start = prev = sorted_idx[0]
        for idx in sorted_idx[1:]:
            if idx == prev + 1:
                prev = idx
            else:
                ranges.append(f"[{start}-{prev}]" if start != prev else str(start))
                start = prev = idx
        ranges.append(f"[{start}-{prev}]" if start != prev else str(start))
        return "Lotes Seleccionados: " + ", ".join(ranges)

    def _handle_export(self):
        if not self.controller: return
        opt_idx = self.cb_format.currentIndex()
        opt_text = self.cb_format.currentText()
        is_db_only = (not self.is_historical) and (opt_idx == 0)
        is_csv = "CSV" in opt_text
        is_excel = "Excel" in opt_text
        needs_file = is_csv or is_excel
        
        filepath = ""
        if needs_file:
            file_filter = "Excel Files (*.xlsx)" if is_excel else "CSV Files (*.csv)"
            filepath, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte", "", file_filter)
            if not filepath: return
            
        holder = self.txt_holder.text().strip()
        celda = int(self.cb_cell.currentText())
        autor = self.txt_author.text().strip()
        notas = self.txt_notes.toPlainText().strip()
        try: area = float(self.txt_area.text())
        except ValueError: area = 0.09
        
        if not self.is_historical and (is_db_only or needs_file):
            self.controller.db.create_or_get_holder(holder, autor)
            celda_id = self.controller.db.create_or_get_celda(holder, celda, area)
            irr = self.config.get("last_irr", 1000.0)
            
            for key in self.visible_keys:
                meta = self.curve_metadata[key]
                if meta.get('hist', False) or meta.get('saved_to_db', False): continue
                
                v_list = meta['x']
                i_list = meta['y']
                points = list(zip(v_list, i_list))
                
                # EJECUCIÓN MATEMÁTICA ANTES DE GUARDAR
                metrics = self.controller.calculate_metrics(v_list, i_list, area, irr)
                
                is_hys = "Rev" in key
                tipo_prueba = "Histéresis (Vuelta)" if is_hys else "Curva J-V (Ida)"
                
                exp_id = self.controller.db.save_experiment_sweep(
                    celda_id=celda_id, tipo_prueba=tipo_prueba, irradiancia=irr, 
                    metrics=metrics, points=points, notas=notas
                )
                meta['saved_to_db'] = True
                meta['exp_id'] = exp_id
                meta['metrics'] = metrics
                
        if needs_file:
            curves_points = {}
            curves_metrics = {}
            for key in self.visible_keys:
                meta = self.curve_metadata[key]
                sweep_name = meta.get('name', key)
                if meta.get('hist', False):
                    exp_id = meta.get('exp_id')
                    curves_points[sweep_name] = self.controller.db.get_sweep_points(exp_id)
                    if is_excel: curves_metrics[sweep_name] = self.controller.get_historical_metrics(exp_id)
                else:
                    curves_points[sweep_name] = list(zip(meta['x'], meta['y']))
                    if is_excel: curves_metrics[sweep_name] = meta.get('metrics', {})
                    
            meta_file = {"holder_id": holder, "posicion": celda, "area_celda": area, "autor": autor, "notas": notas, "fecha": "Actual" if not self.is_historical else "Histórico"}
            success = self.controller.export_report(filepath, meta_file, curves_points, curves_metrics)
            if not success:
                QMessageBox.critical(self, "Error", "Fallo al crear el archivo físico.")
                return

        self.config["last_author"] = autor
        self.controller.save_settings(self.config)
        QMessageBox.information(self, "Operación Exitosa", "Los datos fueron procesados.")
        self.accept()