"""
Game Data Scraper Suite - Main Application
Aplicación principal con GUI unificada para todas las herramientas
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
from pathlib import Path
import subprocess
import json
from datetime import datetime
import threading

# Añadir el directorio al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent))

# Importar módulos core
from core import (
    OCREngine, TemplateMatcher, ScrollController, 
    ConfigManager, DataParser
)

class GameDataScraperSuite:
    """Aplicación principal del Game Data Scraper Suite"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Game Data Scraper Suite v1.0")
        self.root.geometry("1000x700")
        
        # Configurar ícono si existe
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
        
        # Variables de estado
        self.current_module = None
        self.config_manager = ConfigManager()
        
        # Configurar UI
        self.setup_ui()
        
        # Cargar estado inicial
        self.load_initial_state()
        
    def setup_ui(self):
        """Configura la interfaz de usuario principal"""
        # Menú principal
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menú Archivo
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Configuración", command=self.open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exportar Configuración", command=self.export_config)
        file_menu.add_command(label="Importar Configuración", command=self.import_config)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.quit_app)
        
        # Menú Herramientas
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Herramientas", menu=tools_menu)
        tools_menu.add_command(label="Asset Extractor", command=lambda: self.launch_tool("asset_extractor"))
        tools_menu.add_command(label="Coordinate Finder", command=lambda: self.launch_tool("coord_finder"))
        tools_menu.add_command(label="Asset Manager", command=lambda: self.launch_tool("asset_manager"))
        
        # Menú Ayuda
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        help_menu.add_command(label="Documentación", command=self.show_documentation)
        help_menu.add_command(label="Acerca de", command=self.show_about)
        
        # Frame principal con pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Pestaña Dashboard
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text="Dashboard")
        self.setup_dashboard()
        
        # Pestaña Dommy Chat Scraper
        self.chat_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.chat_frame, text="Dommy Chat")
        self.setup_chat_module()
        
        # Pestaña Battle Report
        self.battle_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.battle_frame, text="Battle Report")
        self.setup_battle_module()
        
        # Pestaña Categorizer
        self.categorizer_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.categorizer_frame, text="Categorizer")
        self.setup_categorizer_module()
        
        # Status bar
        self.status_var = tk.StringVar(value="Listo")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
    def setup_dashboard(self):
        """Configura el dashboard principal"""
        # Título
        title_label = ttk.Label(self.dashboard_frame, 
                               text="Game Data Scraper Suite", 
                               font=("Arial", 20, "bold"))
        title_label.pack(pady=20)
        
        # Frame de estadísticas
        stats_frame = ttk.LabelFrame(self.dashboard_frame, text="Estadísticas", padding=15)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Grid de estadísticas
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack()
        
        # Cargar estadísticas
        stats = self.load_statistics()
        
        ttk.Label(stats_grid, text="Chats Procesados:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        ttk.Label(stats_grid, text=str(stats['chats_processed'])).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(stats_grid, text="Reportes de Batalla:").grid(row=0, column=2, sticky=tk.W, padx=10, pady=5)
        ttk.Label(stats_grid, text=str(stats['battle_reports'])).grid(row=0, column=3, sticky=tk.W, pady=5)
        
        ttk.Label(stats_grid, text="Héroes Configurados:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        ttk.Label(stats_grid, text=str(stats['heroes_configured'])).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(stats_grid, text="Capitanes Prohibidos:").grid(row=1, column=2, sticky=tk.W, padx=10, pady=5)
        ttk.Label(stats_grid, text=str(stats['forbidden_captains'])).grid(row=1, column=3, sticky=tk.W, pady=5)
        
        # Frame de acciones rápidas
        actions_frame = ttk.LabelFrame(self.dashboard_frame, text="Acciones Rápidas", padding=15)
        actions_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Botones de acción rápida
        button_frame = ttk.Frame(actions_frame)
        button_frame.pack()
        
        ttk.Button(button_frame, text="Procesar Chat", 
                  command=lambda: self.notebook.select(self.chat_frame),
                  width=20).grid(row=0, column=0, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Analizar Batalla", 
                  command=lambda: self.launch_battle_report_module(),
                  width=20).grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Generar Reporte", 
                  command=lambda: self.notebook.select(self.categorizer_frame),
                  width=20).grid(row=0, column=2, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Gestionar Assets", 
                  command=lambda: self.launch_tool("asset_manager"),
                  width=20).grid(row=1, column=0, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Capturar Coordenadas", 
                  command=lambda: self.launch_tool("coord_finder"),
                  width=20).grid(row=1, column=1, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Extraer Assets", 
                  command=lambda: self.launch_tool("asset_extractor"),
                  width=20).grid(row=1, column=2, padx=10, pady=10)
        
        # Frame de archivos recientes
        recent_frame = ttk.LabelFrame(self.dashboard_frame, text="Archivos Recientes", padding=15)
        recent_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Listbox de archivos recientes
        self.recent_listbox = tk.Listbox(recent_frame, height=8)
        self.recent_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.recent_listbox, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.recent_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.recent_listbox.yview)
        
        # Cargar archivos recientes
        self.load_recent_files()
        
        # Bind doble click
        self.recent_listbox.bind('<Double-1>', self.open_recent_file)
        
    def setup_chat_module(self):
        """Configura el módulo de Dommy Chat Scraper"""
        # Panel de configuración
        config_frame = ttk.LabelFrame(self.chat_frame, text="Configuración", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Nombre del chat
        ttk.Label(config_frame, text="Nombre del Chat:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.chat_name_var = tk.StringVar(value="Dommy Monday")
        ttk.Entry(config_frame, textvariable=self.chat_name_var, width=30).grid(row=0, column=1, pady=5)
        
        # Fecha
        ttk.Label(config_frame, text="Fecha:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.chat_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(config_frame, textvariable=self.chat_date_var, width=30).grid(row=1, column=1, pady=5)
        
        # Marcador
        ttk.Label(config_frame, text="Marcador de Inicio:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.chat_marker_var = tk.StringVar(value="*****")
        ttk.Entry(config_frame, textvariable=self.chat_marker_var, width=30).grid(row=2, column=1, pady=5)
        
        # Panel de control
        control_frame = ttk.Frame(self.chat_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(control_frame, text="Iniciar Captura", 
                  command=self.start_chat_capture,
                  width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Detener", 
                  command=self.stop_chat_capture,
                  width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Procesar Archivo", 
                  command=self.process_chat_file,
                  width=20).pack(side=tk.LEFT, padx=5)
        
        # Panel de resultados
        results_frame = ttk.LabelFrame(self.chat_frame, text="Resultados", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Text widget para mostrar resultados
        self.chat_results = tk.Text(results_frame, height=15)
        self.chat_results.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.chat_results, orient=tk.VERTICAL, command=self.chat_results.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_results.config(yscrollcommand=scrollbar.set)
        
    def setup_battle_module(self):
        """Configura el módulo de Battle Report Scraper"""
        # Panel de configuración
        config_frame = ttk.LabelFrame(self.battle_frame, text="Battle Report Scraper", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Información
        info_label = ttk.Label(config_frame, 
                              text="Use el módulo completo de Battle Report Scraper para análisis detallado de asistencia.",
                              wraplength=600)
        info_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Fecha del reporte
        ttk.Label(config_frame, text="Fecha del Reporte:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.battle_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(config_frame, textvariable=self.battle_date_var, width=30).grid(row=1, column=1, pady=5)
        
        # Panel de control principal
        main_control_frame = ttk.Frame(self.battle_frame)
        main_control_frame.pack(fill=tk.X, padx=10, pady=20)
        
        # Botón grande para abrir el módulo completo
        open_module_btn = ttk.Button(main_control_frame, 
                                     text="ABRIR BATTLE REPORT SCRAPER\n(Módulo Completo)", 
                                     command=self.open_battle_report_module,
                                     style="Success.TButton")
        open_module_btn.pack(pady=10)
        
        # Panel de control secundario (para funciones rápidas)
        control_frame = ttk.LabelFrame(self.battle_frame, text="Acciones Rápidas", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        button_frame = ttk.Frame(control_frame)
        button_frame.pack()
        
        ttk.Button(button_frame, text="Abrir Asset Creator", 
                  command=lambda: self.launch_tool("quick_asset_creator"),
                  width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Gestionar Assets", 
                  command=lambda: self.launch_tool("asset_manager"),
                  width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Cargar Reporte", 
                  command=self.load_battle_report,
                  width=20).pack(side=tk.LEFT, padx=5)
        
        # Panel de participantes
        participants_frame = ttk.LabelFrame(self.battle_frame, text="Últimos Participantes Detectados", padding=10)
        participants_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeview para participantes
        columns = ("Artefactos", "Capitán Prohibido", "Notas")
        self.participants_tree = ttk.Treeview(participants_frame, columns=columns, show="tree headings", height=10)
        
        self.participants_tree.heading("#0", text="Jugador")
        self.participants_tree.heading("Artefactos", text="Artefactos")
        self.participants_tree.heading("Capitán Prohibido", text="Capitán Prohibido")
        self.participants_tree.heading("Notas", text="Notas")
        
        self.participants_tree.column("#0", width=200)
        self.participants_tree.column("Artefactos", width=100)
        self.participants_tree.column("Capitán Prohibido", width=150)
        self.participants_tree.column("Notas", width=200)
        
        self.participants_tree.pack(fill=tk.BOTH, expand=True)
        
    def open_battle_report_module(self):
        """Abre el módulo completo de Battle Report Scraper"""
        try:
            import subprocess
            subprocess.Popen([sys.executable, "modules/battle_report_scraper.py"])
            self.status_var.set("Battle Report Scraper abierto")
        except Exception as e:
            messagebox.showerror("Error", f"Error abriendo Battle Report Scraper: {e}")
        
    def setup_categorizer_module(self):
        """Configura el módulo Categorizer Report"""
        # Panel de selección de archivos
        files_frame = ttk.LabelFrame(self.categorizer_frame, text="Archivos de Entrada", padding=10)
        files_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Archivo de chat
        ttk.Label(files_frame, text="Archivo de Chat:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.cat_chat_file_var = tk.StringVar()
        ttk.Entry(files_frame, textvariable=self.cat_chat_file_var, width=40).grid(row=0, column=1, pady=5)
        ttk.Button(files_frame, text="Buscar", 
                  command=lambda: self.browse_file("chat")).grid(row=0, column=2, padx=5)
        
        # Archivo de batalla
        ttk.Label(files_frame, text="Archivo de Batalla:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.cat_battle_file_var = tk.StringVar()
        ttk.Entry(files_frame, textvariable=self.cat_battle_file_var, width=40).grid(row=1, column=1, pady=5)
        ttk.Button(files_frame, text="Buscar", 
                  command=lambda: self.browse_file("battle")).grid(row=1, column=2, padx=5)
        
        # Panel de opciones
        options_frame = ttk.LabelFrame(self.categorizer_frame, text="Opciones de Reporte", padding=10)
        options_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(options_frame, text="Formato de Salida:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.output_format_var = tk.StringVar(value="Excel")
        format_combo = ttk.Combobox(options_frame, textvariable=self.output_format_var,
                                   values=["Excel", "CSV", "JSON"], width=20)
        format_combo.grid(row=0, column=1, pady=5)
        
        ttk.Label(options_frame, text="Nombre del Archivo:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_name_var = tk.StringVar(value=f"Reporte_{datetime.now().strftime('%Y%m%d')}")
        ttk.Entry(options_frame, textvariable=self.output_name_var, width=30).grid(row=1, column=1, pady=5)
        
        # Panel de control
        control_frame = ttk.Frame(self.categorizer_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(control_frame, text="Generar Reporte", 
                  command=self.generate_report,
                  width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Vista Previa", 
                  command=self.preview_report,
                  width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Exportar", 
                  command=self.export_report,
                  width=20).pack(side=tk.LEFT, padx=5)
        
        # Panel de vista previa
        preview_frame = ttk.LabelFrame(self.categorizer_frame, text="Vista Previa del Reporte", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Text widget para vista previa
        self.report_preview = tk.Text(preview_frame, height=10)
        self.report_preview.pack(fill=tk.BOTH, expand=True)
        
    def launch_tool(self, tool_name):
        """Lanza una herramienta externa"""
        tools_dir = Path(__file__).parent / "tools"
        tool_file = tools_dir / f"{tool_name}.py"
        
        if tool_file.exists():
            try:
                subprocess.Popen([sys.executable, str(tool_file)])
                self.status_var.set(f"Herramienta {tool_name} iniciada")
            except Exception as e:
                messagebox.showerror("Error", f"Error lanzando herramienta: {e}")
        else:
            messagebox.showwarning("Advertencia", f"Herramienta {tool_name} no encontrada")
    
    def launch_battle_report_module(self):
        """Lanza el módulo Battle Report Scraper"""
        module_file = Path(__file__).parent / "modules" / "battle_report_scraper.py"
        
        if module_file.exists():
            try:
                subprocess.Popen([sys.executable, str(module_file)])
                self.status_var.set("Battle Report Scraper iniciado")
            except Exception as e:
                messagebox.showerror("Error", f"Error lanzando Battle Report Scraper: {e}")
        else:
            messagebox.showwarning("Advertencia", "Módulo Battle Report Scraper no encontrado")
    
    def load_statistics(self):
        """Carga las estadísticas del sistema"""
        stats = {
            'chats_processed': 0,
            'battle_reports': 0,
            'heroes_configured': len(self.config_manager.get_enabled_heroes()),
            'forbidden_captains': len(self.config_manager.get_enabled_forbidden_captains())
        }
        
        # Contar archivos procesados
        data_dir = Path(self.config_manager.data_dir)
        
        if (data_dir / "chat_logs").exists():
            stats['chats_processed'] = len(list((data_dir / "chat_logs").glob("DC_*.json")))
        
        if (data_dir / "battle_reports").exists():
            stats['battle_reports'] = len(list((data_dir / "battle_reports").glob("BR_*.json")))
        
        return stats
    
    def load_recent_files(self):
        """Carga la lista de archivos recientes"""
        self.recent_listbox.delete(0, tk.END)
        
        data_dir = Path(self.config_manager.data_dir)
        recent_files = []
        
        # Buscar archivos recientes en todos los subdirectorios
        for subdir in ["chat_logs", "battle_reports", "excel_reports"]:
            dir_path = data_dir / subdir
            if dir_path.exists():
                for file in dir_path.glob("*"):
                    if file.is_file():
                        recent_files.append(file)
        
        # Ordenar por fecha de modificación
        recent_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Mostrar los últimos 10
        for file in recent_files[:10]:
            relative_path = file.relative_to(data_dir)
            self.recent_listbox.insert(tk.END, str(relative_path))
    
    def open_recent_file(self, event):
        """Abre un archivo reciente"""
        selection = self.recent_listbox.curselection()
        if selection:
            filename = self.recent_listbox.get(selection[0])
            file_path = Path(self.config_manager.data_dir) / filename
            
            if file_path.exists():
                try:
                    os.startfile(str(file_path))
                except Exception as e:
                    messagebox.showerror("Error", f"Error abriendo archivo: {e}")
    
    def start_chat_capture(self):
        """Inicia la captura del chat"""
        # TODO: Implementar la captura real del chat
        self.status_var.set("Captura de chat iniciada...")
        self.chat_results.insert(tk.END, f"Iniciando captura de chat: {self.chat_name_var.get()}\n")
        self.chat_results.insert(tk.END, f"Fecha: {self.chat_date_var.get()}\n")
        self.chat_results.insert(tk.END, f"Buscando marcador: {self.chat_marker_var.get()}\n\n")
        
        messagebox.showinfo("Info", "Módulo de captura de chat en desarrollo")
    
    def stop_chat_capture(self):
        """Detiene la captura del chat"""
        self.status_var.set("Captura detenida")
    
    def process_chat_file(self):
        """Procesa un archivo de chat existente"""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo de chat",
            filetypes=[("Todos", "*.*")]
        )
        
        if filename:
            self.status_var.set(f"Procesando: {Path(filename).name}")
            self.chat_results.insert(tk.END, f"Procesando archivo: {filename}\n")
    
    def start_battle_analysis(self):
        """Inicia el análisis de batalla"""
        self.status_var.set("Abriendo módulo de análisis de batalla...")
        
        # Lanzar el módulo Battle Report Scraper
        try:
            import subprocess
            subprocess.Popen([sys.executable, "modules/battle_report_scraper.py"])
            self.status_var.set("Módulo Battle Report Scraper iniciado")
        except Exception as e:
            messagebox.showerror("Error", f"Error abriendo Battle Report Scraper: {e}")

    
    def load_battle_report(self):
        """Carga un reporte de batalla existente"""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            title="Seleccionar reporte de batalla",
            filetypes=[("JSON files", "*.json"), ("Todos", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Limpiar árbol
                self.participants_tree.delete(*self.participants_tree.get_children())
                
                # Cargar participantes
                for participant in data.get('participants', []):
                    self.participants_tree.insert("", "end", 
                                                 text=participant['name'],
                                                 values=(
                                                     "Sí" if participant.get('artifacts_used') else "No",
                                                     ", ".join(participant.get('forbidden_captains', [])),
                                                     participant.get('notes', '')
                                                 ))
                
                self.status_var.set(f"Reporte cargado: {Path(filename).name}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error cargando reporte: {e}")
    
    def browse_file(self, file_type):
        """Busca un archivo para el categorizer"""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            title=f"Seleccionar archivo de {file_type}",
            filetypes=[("JSON files", "*.json"), ("Todos", "*.*")]
        )
        
        if filename:
            if file_type == "chat":
                self.cat_chat_file_var.set(filename)
            else:
                self.cat_battle_file_var.set(filename)
    
    def generate_report(self):
        """Genera el reporte final"""
        chat_file = self.cat_chat_file_var.get()
        battle_file = self.cat_battle_file_var.get()
        
        if not chat_file or not battle_file:
            messagebox.showwarning("Advertencia", "Por favor selecciona ambos archivos")
            return
        
        # TODO: Implementar generación real del reporte
        self.status_var.set("Generando reporte...")
        self.report_preview.insert(tk.END, "Generando reporte con los siguientes archivos:\n")
        self.report_preview.insert(tk.END, f"- Chat: {Path(chat_file).name}\n")
        self.report_preview.insert(tk.END, f"- Batalla: {Path(battle_file).name}\n\n")
        
        messagebox.showinfo("Info", "Módulo de generación de reportes en desarrollo")
    
    def preview_report(self):
        """Muestra vista previa del reporte"""
        self.report_preview.delete(1.0, tk.END)
        self.report_preview.insert(tk.END, "Vista previa del reporte:\n")
        self.report_preview.insert(tk.END, "=" * 50 + "\n\n")
        self.report_preview.insert(tk.END, "Formato: " + self.output_format_var.get() + "\n")
        self.report_preview.insert(tk.END, "Nombre: " + self.output_name_var.get() + "\n\n")
    
    def export_report(self):
        """Exporta el reporte generado"""
        from tkinter import filedialog
        
        format_ext = {
            "Excel": ".xlsx",
            "CSV": ".csv",
            "JSON": ".json"
        }
        
        ext = format_ext.get(self.output_format_var.get(), ".xlsx")
        
        filename = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(f"{self.output_format_var.get()} files", f"*{ext}"), ("Todos", "*.*")],
            initialfile=self.output_name_var.get()
        )
        
        if filename:
            # TODO: Implementar exportación real
            self.status_var.set(f"Exportado a: {Path(filename).name}")
            messagebox.showinfo("Éxito", f"Reporte exportado a:\n{filename}")
    
    def open_settings(self):
        """Abre la ventana de configuración"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Configuración")
        settings_window.geometry("600x400")
        
        # Notebook para diferentes secciones
        settings_notebook = ttk.Notebook(settings_window)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Pestaña General
        general_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(general_frame, text="General")
        
        ttk.Label(general_frame, text="Configuración General", 
                 font=("Arial", 12, "bold")).pack(pady=10)
        
        # Pestaña OCR
        ocr_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(ocr_frame, text="OCR")
        
        ttk.Label(ocr_frame, text="Configuración de OCR", 
                 font=("Arial", 12, "bold")).pack(pady=10)
        
        # Botones
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Guardar", 
                  command=lambda: self.save_settings(settings_window)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", 
                  command=settings_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def save_settings(self, window):
        """Guarda la configuración"""
        # TODO: Implementar guardado real
        self.status_var.set("Configuración guardada")
        window.destroy()
    
    def export_config(self):
        """Exporta toda la configuración"""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Todos", "*.*")],
            initialfile=f"config_export_{datetime.now().strftime('%Y%m%d')}"
        )
        
        if filename:
            self.config_manager.export_config(filename)
            messagebox.showinfo("Éxito", f"Configuración exportada a:\n{filename}")
    
    def import_config(self):
        """Importa configuración"""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("Todos", "*.*")]
        )
        
        if filename:
            self.config_manager.import_config(filename)
            self.load_initial_state()
            messagebox.showinfo("Éxito", "Configuración importada exitosamente")
    
    def show_documentation(self):
        """Muestra la documentación"""
        doc_window = tk.Toplevel(self.root)
        doc_window.title("Documentación")
        doc_window.geometry("800x600")
        
        text_widget = tk.Text(doc_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        documentation = """
        GAME DATA SCRAPER SUITE - DOCUMENTACIÓN
        ========================================
        
        MÓDULOS PRINCIPALES:
        
        1. DOMMY CHAT SCRAPER
        - Captura mensajes del chat del juego
        - Detecta marcadores de inicio/fin
        - Parsea valores de silver
        - Exporta a formato JSON
        
        2. BATTLE REPORT SCRAPER
        - Analiza reportes de batalla
        - Detecta participantes y héroes
        - Identifica capitanes prohibidos
        - Verifica uso de artefactos
        
        3. CATEGORIZER REPORT
        - Combina datos de chat y batalla
        - Genera reportes en Excel/CSV/JSON
        - Calcula estadísticas
        
        HERRAMIENTAS:
        
        - Asset Extractor: Captura y recorta imágenes del juego
        - Coordinate Finder: Encuentra coordenadas de elementos UI
        - Asset Manager: Gestiona héroes y capitanes
        
        Para más información, consulta el README del proyecto.
        """
        
        text_widget.insert(1.0, documentation)
        text_widget.config(state=tk.DISABLED)
    
    def show_about(self):
        """Muestra información sobre la aplicación"""
        about_text = """
        Game Data Scraper Suite v1.0
        
        Sistema integral para captura y análisis
        de datos del juego.
        
        Desarrollado para Total Alliance
        © 2025 Decoding
        
        Módulos Core:
        - OCR Engine (Tesseract/EasyOCR)
        - Template Matcher (OpenCV)
        - Scroll Controller
        - Config Manager
        - Data Parser
        """
        
        messagebox.showinfo("Acerca de", about_text)
    
    def load_initial_state(self):
        """Carga el estado inicial de la aplicación"""
        try:
            # Actualizar estadísticas
            stats = self.load_statistics()
            
            # Actualizar archivos recientes
            self.load_recent_files()
            
            self.status_var.set("Aplicación lista")
            
        except Exception as e:
            print(f"Error cargando estado inicial: {e}")
    
    def quit_app(self):
        """Cierra la aplicación"""
        if messagebox.askyesno("Confirmar", "¿Deseas salir de la aplicación?"):
            self.root.quit()
    
    def run(self):
        """Ejecuta la aplicación principal"""
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.root.mainloop()

if __name__ == "__main__":
    app = GameDataScraperSuite()
    app.run()
