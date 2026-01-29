import sys
import sqlite3
from datetime import datetime

# PyQt6 Imports
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (QMessageBox, QTableWidgetItem, QHeaderView, 
                             QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLabel, QDateEdit, QComboBox, QDoubleSpinBox, 
                             QSpinBox, QPushButton, QTableWidget, QWidget, QGroupBox)

# Matplotlib Imports
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

class WorkoutTracker(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IronTracker - Workout Analytics")
        self.resize(1000, 700)

        # Database Init
        self.conn = sqlite3.connect("workouts.db")
        self.create_table()

        # UI Initialization
        self.init_ui()
        
        # Data Initialization
        self.refresh_table()
        self.plot_chart()

    def init_ui(self):
        # --- Main Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- LEFT PANEL (Inputs & Table) ---
        left_panel = QVBoxLayout()
        
        # 1. Input Group
        input_group = QGroupBox("Add / Edit Entry")
        input_layout = QFormLayout()

        self.input_date = QDateEdit()
        self.input_date.setDate(QDate.currentDate())
        self.input_date.setCalendarPopup(True)
        
        self.input_exercise = QComboBox()
        self.input_exercise.addItems(["Squat", "Bench Press", "Deadlift", "Running (km)", "Pull-ups", "Overhead Press"])
        self.input_exercise.setEditable(True) # Allow custom exercises

        self.input_weight = QDoubleSpinBox()
        self.input_weight.setRange(0, 500)
        self.input_weight.setSuffix(" kg")

        self.input_reps = QSpinBox()
        self.input_reps.setRange(0, 1000)

        input_layout.addRow("Date:", self.input_date)
        input_layout.addRow("Exercise:", self.input_exercise)
        input_layout.addRow("Weight/Dist:", self.input_weight)
        input_layout.addRow("Reps:", self.input_reps)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Record")
        self.btn_update = QPushButton("Update Selected")
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_clear = QPushButton("Clear Form")
        
        # Styling buttons
        self.btn_add.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_delete.setStyleSheet("background-color: #f44336; color: white;")
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_update)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_clear)

        input_layout.addRow(btn_layout)
        input_group.setLayout(input_layout)
        left_panel.addWidget(input_group)

        # 2. Table
        self.table_workouts = QTableWidget()
        headers = ["ID", "Date", "Exercise", "Weight", "Reps"]
        self.table_workouts.setColumnCount(len(headers))
        self.table_workouts.setHorizontalHeaderLabels(headers)
        self.table_workouts.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_workouts.setColumnHidden(0, True) # Hide ID
        self.table_workouts.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        left_panel.addWidget(self.table_workouts)

        # --- RIGHT PANEL (Charts) ---
        right_panel = QVBoxLayout()
        chart_group = QGroupBox("Analytics")
        chart_layout = QVBoxLayout()

        # Chart Controls
        ctrl_layout = QHBoxLayout()
        self.combo_chart_exercise = QComboBox()
        self.combo_chart_type = QComboBox()
        self.combo_chart_type.addItems(["Line Chart", "Bar Chart"])
        self.combo_chart_color = QComboBox()
        self.combo_chart_color.addItems(["blue", "red", "green", "orange"])
        self.btn_refresh_chart = QPushButton("Refresh Chart")

        ctrl_layout.addWidget(QLabel("Exercise:"))
        ctrl_layout.addWidget(self.combo_chart_exercise)
        ctrl_layout.addWidget(self.combo_chart_type)
        ctrl_layout.addWidget(self.combo_chart_color)
        ctrl_layout.addWidget(self.btn_refresh_chart)
        chart_layout.addLayout(ctrl_layout)

        # Matplotlib Figure
        self.figure = plt.figure(facecolor='#f0f0f0')
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        chart_layout.addWidget(self.toolbar)
        chart_layout.addWidget(self.canvas)
        chart_group.setLayout(chart_layout)
        right_panel.addWidget(chart_group)

        # Add panels to main layout
        main_layout.addLayout(left_panel, 35)
        main_layout.addLayout(right_panel, 65)

        # --- Logic Connections ---
        self.btn_add.clicked.connect(self.add_record)
        self.btn_delete.clicked.connect(self.delete_record)
        self.btn_update.clicked.connect(self.update_record)
        self.btn_clear.clicked.connect(self.clear_form)
        self.table_workouts.itemClicked.connect(self.fill_form_from_table)
        self.btn_refresh_chart.clicked.connect(self.plot_chart)
        self.combo_chart_exercise.currentIndexChanged.connect(self.plot_chart)

    # --- Database Methods ---
    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                exercise TEXT,
                weight REAL,
                reps INTEGER
            )
        """)
        self.conn.commit()

    def refresh_table(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM workouts ORDER BY date DESC")
        rows = cursor.fetchall()

        self.table_workouts.setRowCount(0)
        for row_idx, row_data in enumerate(rows):
            self.table_workouts.insertRow(row_idx)
            for col_idx, data in enumerate(row_data):
                self.table_workouts.setItem(row_idx, col_idx, QTableWidgetItem(str(data)))
        
        self.refresh_chart_options()

    # --- CRUD Operations ---
    def add_record(self):
        date = self.input_date.date().toString("yyyy-MM-dd")
        exercise = self.input_exercise.currentText()
        weight = self.input_weight.value()
        reps = self.input_reps.value()

        if weight <= 0 and reps <= 0:
             QMessageBox.warning(self, "Error", "Please enter valid values.")
             return

        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO workouts (date, exercise, weight, reps) VALUES (?, ?, ?, ?)",
                       (date, exercise, weight, reps))
        self.conn.commit()
        self.refresh_table()
        self.clear_form()
        self.plot_chart()

    def delete_record(self):
        selected_rows = self.table_workouts.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Select a row to delete.")
            return

        row_idx = selected_rows[0].row()
        item_id = self.table_workouts.item(row_idx, 0).text()

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM workouts WHERE id = ?", (item_id,))
        self.conn.commit()
        self.refresh_table()
        self.clear_form()
        self.plot_chart()

    def update_record(self):
        selected_rows = self.table_workouts.selectionModel().selectedRows()
        if not selected_rows:
            return

        row_idx = selected_rows[0].row()
        item_id = self.table_workouts.item(row_idx, 0).text()

        date = self.input_date.date().toString("yyyy-MM-dd")
        exercise = self.input_exercise.currentText()
        weight = self.input_weight.value()
        reps = self.input_reps.value()

        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE workouts SET date=?, exercise=?, weight=?, reps=? WHERE id=?
        """, (date, exercise, weight, reps, item_id))
        self.conn.commit()
        self.refresh_table()
        self.plot_chart()

    def fill_form_from_table(self):
        selected_rows = self.table_workouts.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row_idx = selected_rows[0].row()
        date_str = self.table_workouts.item(row_idx, 1).text()
        exercise = self.table_workouts.item(row_idx, 2).text()
        weight = float(self.table_workouts.item(row_idx, 3).text())
        reps = int(self.table_workouts.item(row_idx, 4).text())

        self.input_date.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))
        self.input_exercise.setCurrentText(exercise)
        self.input_weight.setValue(weight)
        self.input_reps.setValue(reps)

    def clear_form(self):
        self.input_weight.setValue(0)
        self.input_reps.setValue(0)
        self.table_workouts.clearSelection()

    # --- Analytics & Charts ---
    def refresh_chart_options(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT exercise FROM workouts")
        exercises = [row[0] for row in cursor.fetchall()]
        
        current = self.combo_chart_exercise.currentText()
        self.combo_chart_exercise.clear()
        self.combo_chart_exercise.addItems(exercises)
        
        # Keep selection if still valid, otherwise default to first
        if current in exercises:
            self.combo_chart_exercise.setCurrentText(current)
        elif exercises:
            self.combo_chart_exercise.setCurrentIndex(0)

    def plot_chart(self):
        exercise = self.combo_chart_exercise.currentText()
        chart_type = self.combo_chart_type.currentText()
        color = self.combo_chart_color.currentText()

        self.figure.clear()
        
        if not exercise:
            self.canvas.draw()
            return

        cursor = self.conn.cursor()
        cursor.execute("SELECT date, weight FROM workouts WHERE exercise = ? ORDER BY date ASC", (exercise,))
        data = cursor.fetchall()

        if not data:
            self.canvas.draw()
            return

        dates = [datetime.strptime(row[0], "%Y-%m-%d") for row in data]
        weights = [row[1] for row in data]

        ax = self.figure.add_subplot(111)

        if chart_type == "Line Chart":
            ax.plot(dates, weights, marker='o', linestyle='-', color=color, label='Weight (kg)', linewidth=2)
            if len(weights) > 0:
                avg_weight = sum(weights) / len(weights)
                ax.axhline(avg_weight, color='gray', linestyle='--', alpha=0.7, label=f'Avg: {avg_weight:.1f}')
        elif chart_type == "Bar Chart":
            ax.bar(dates, weights, color=color, label='Weight (kg)', alpha=0.7)

        # Formatting
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.figure.autofmt_xdate()

        ax.set_title(f"Progress: {exercise}", fontsize=12, fontweight='bold')
        ax.set_ylabel("Weight (kg)")
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.5)

        self.canvas.draw()

    def closeEvent(self, event):
        self.conn.close()
        event.accept()

if __name__ == "__main__": 
    app = QtWidgets.QApplication(sys.argv)
    
    # Set Fusion Style for better look on Linux/Windows
    app.setStyle("Fusion")
    
    window = WorkoutTracker()
    window.show()
    sys.exit(app.exec())