import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import ctypes
import sys
import os
import webbrowser
import time
import threading

# Nombre del servicio por defecto
DEFAULT_SERVICES = ["HidromiraService", "Monitor Streamlit", "API REST", "Hidromira"]

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# Si no es administrador, reiniciar solicitando permisos elevados
if not is_admin():
    try:
        # Asegurarse de pasar la ruta completa del script
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
    except Exception as e:
        pass
    sys.exit()

class ServiceControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Control de Servicio - Hidromira")
        self.root.geometry("460x470")
        self.root.resizable(False, False)
        
        # Paleta de colores Premium Oscura
        self.bg_color = "#121214"
        self.card_color = "#1a1a1e"
        self.text_color = "#ffffff"
        self.accent_blue = "#0091ff"
        self.accent_green = "#00c853"
        self.accent_red = "#d50000"
        self.accent_gray = "#8e8e93"
        self.accent_orange = "#ff9100"
        
        self.root.configure(bg=self.bg_color)
        
        # Estilos TTK
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=("Segoe UI", 10))
        style.configure("TCombobox", fieldbackground=self.card_color, background=self.bg_color, foreground=self.text_color)
        
        # Encabezado Principal
        header_frame = tk.Frame(self.root, bg=self.bg_color, pady=12)
        header_frame.pack(fill="x")
        
        lbl_title = tk.Label(
            header_frame, 
            text="Sistema de Monitoreo de Vibraciones", 
            font=("Segoe UI", 15, "bold"), 
            bg=self.bg_color, 
            fg=self.accent_blue
        )
        lbl_title.pack()
        
        lbl_subtitle = tk.Label(
            header_frame, 
            text="Administración de Servicios Windows (NSSM)", 
            font=("Segoe UI", 9), 
            bg=self.bg_color, 
            fg=self.accent_gray
        )
        lbl_subtitle.pack()
        
        # Separador
        separator = tk.Frame(self.root, height=2, bd=0, bg=self.card_color)
        separator.pack(fill="x", padx=20, pady=2)
        
        # Panel de Control
        control_frame = tk.Frame(self.root, bg=self.bg_color, padx=30, pady=10)
        control_frame.pack(fill="both", expand=True)
        
        # Selector de Servicio
        lbl_service = tk.Label(control_frame, text="Seleccionar Servicio:", font=("Segoe UI", 10, "bold"), bg=self.bg_color, fg=self.text_color)
        lbl_service.grid(row=0, column=0, sticky="w", pady=5)
        
        self.service_var = tk.StringVar(value=DEFAULT_SERVICES[0])
        self.service_combo = ttk.Combobox(control_frame, textvariable=self.service_var, values=DEFAULT_SERVICES, font=("Segoe UI", 10), state="normal")
        self.service_combo.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5, padx=10)
        self.service_combo.bind("<<ComboboxSelected>>", lambda e: self.update_status())
        self.service_combo.bind("<KeyRelease>", lambda e: self.update_status())
        
        # Indicador de Estado
        lbl_status_title = tk.Label(control_frame, text="Estado Actual:", font=("Segoe UI", 10, "bold"), bg=self.bg_color, fg=self.text_color)
        lbl_status_title.grid(row=1, column=0, sticky="w", pady=5)
        
        self.lbl_status = tk.Label(control_frame, text="Consultando...", font=("Segoe UI", 11, "bold"), bg=self.bg_color, fg=self.accent_gray)
        self.lbl_status.grid(row=1, column=1, sticky="w", pady=5, padx=10)
        
        # Mensaje de advertencia
        self.lbl_warning = tk.Label(
            control_frame, 
            text="⚠️ Nota: Para encender el monitoreo debe cerrar el software WitMotion.",
            font=("Segoe UI", 9, "bold"),
            bg=self.bg_color,
            fg=self.accent_orange,
            wraplength=380,
            justify="center"
        )
        self.lbl_warning.grid(row=2, column=0, columnspan=3, pady=10, sticky="ew")

        # Panel de Opciones (Checkboxes)
        options_frame = tk.Frame(control_frame, bg=self.bg_color)
        options_frame.grid(row=3, column=0, columnspan=3, pady=5, sticky="ew")

        self.open_browser_var = tk.BooleanVar(value=True)
        self.chk_browser = tk.Checkbutton(
            options_frame, 
            text="Abrir navegador (http://localhost:8501/) al arrancar",
            variable=self.open_browser_var,
            bg=self.bg_color,
            fg=self.text_color,
            selectcolor=self.bg_color,
            activebackground=self.bg_color,
            activeforeground=self.text_color,
            font=("Segoe UI", 9)
        )
        self.chk_browser.pack(anchor="w", pady=2)

        self.open_witmotion_var = tk.BooleanVar(value=True)
        self.chk_witmotion = tk.Checkbutton(
            options_frame, 
            text="Abrir software WitMotion al detener",
            variable=self.open_witmotion_var,
            bg=self.bg_color,
            fg=self.text_color,
            selectcolor=self.bg_color,
            activebackground=self.bg_color,
            activeforeground=self.text_color,
            font=("Segoe UI", 9)
        )
        self.chk_witmotion.pack(anchor="w", pady=2)

        # Botones de Acción
        self.btn_start = tk.Button(
            control_frame, 
            text="▶ Arrancar Servicio", 
            command=self.start_service,
            bg=self.accent_green, 
            fg=self.text_color, 
            font=("Segoe UI", 10, "bold"),
            activebackground="#00a844", 
            activeforeground=self.text_color,
            bd=0, 
            height=2,
            cursor="hand2"
        )
        self.btn_start.grid(row=4, column=0, columnspan=3, sticky="ew", pady=5)
        
        self.btn_stop = tk.Button(
            control_frame, 
            text="■ Detener Servicio", 
            command=self.stop_service,
            bg=self.accent_red, 
            fg=self.text_color, 
            font=("Segoe UI", 10, "bold"),
            activebackground="#b30000", 
            activeforeground=self.text_color,
            bd=0, 
            height=2,
            cursor="hand2"
        )
        self.btn_stop.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        
        # Barra de estado inferior
        self.lbl_info = tk.Label(
            self.root, 
            text="Ejecutando con permisos de Administrador", 
            font=("Segoe UI", 8), 
            bg=self.card_color, 
            fg=self.accent_green,
            pady=4
        )
        self.lbl_info.pack(fill="x", side="bottom")
        
        # Iniciar monitoreo del estado
        self.update_status()
        self.auto_refresh()

    def get_service_status(self):
        service_name = self.service_var.get().strip()
        if not service_name:
            return "Nombre Vacío", self.accent_gray
            
        try:
            # Consultar estado con el comando 'sc' de Windows
            result = subprocess.run(
                ["sc", "query", service_name], 
                capture_output=True, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            output = result.stdout
            if "RUNNING" in output:
                return "CORRIENDO", self.accent_green
            elif "STOPPED" in output:
                return "DETENIDO", self.accent_red
            elif "PENDING" in output:
                return "CAMBIANDO...", self.accent_blue
            elif "does not exist" in result.stderr or "no existe" in result.stderr or "1060" in output:
                return "NO INSTALADO", self.accent_gray
            else:
                return "DESCONOCIDO", self.accent_gray
        except Exception:
            return "ERROR AL CONSULTAR", self.accent_red

    def update_status(self):
        status_text, color = self.get_service_status()
        self.lbl_status.config(text=status_text, fg=color)
        
        # Deshabilitar/habilitar botones correspondientes
        if status_text == "CORRIENDO":
            self.btn_start.config(state="disabled", bg="#1b3f27")
            self.btn_stop.config(state="normal", bg=self.accent_red)
        elif status_text == "DETENIDO":
            self.btn_start.config(state="normal", bg=self.accent_green)
            self.btn_stop.config(state="disabled", bg="#4a1515")
        elif status_text == "NO INSTALADO":
            self.btn_start.config(state="disabled", bg="#2a2a2e")
            self.btn_stop.config(state="disabled", bg="#2a2a2e")
        else:
            self.btn_start.config(state="normal", bg=self.accent_green)
            self.btn_stop.config(state="normal", bg=self.accent_red)

    def start_service(self):
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="disabled")
        self.lbl_status.config(text="INICIANDO...", fg=self.accent_blue)
        self.lbl_info.config(text="Solicitando inicio de servicio...", fg=self.accent_blue)
        self.root.update_idletasks()
        
        # Lanzar la operación en un hilo separado para que no se congele la ventana
        threading.Thread(target=self._start_service_thread, daemon=True).start()

    def _start_service_thread(self):
        service_name = self.service_var.get().strip()
        try:
            # Ejecutar inicio de servicio
            res = subprocess.run(
                ["sc", "start", service_name], 
                capture_output=True, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if res.returncode == 0 or "already running" in res.stderr:
                self.lbl_info.config(text=f"Servicio '{service_name}' iniciado correctamente.", fg=self.accent_green)
                # Abrir el navegador si está seleccionado en un subproceso
                if self.open_browser_var.get():
                    time.sleep(2.0)
                    try:
                        webbrowser.open("http://localhost:8501/")
                    except Exception:
                        pass
            else:
                self.lbl_info.config(text=f"Detalle: {res.stderr.strip()}", fg=self.accent_red)
        except Exception as e:
            self.lbl_info.config(text=f"Error: {str(e)}", fg=self.accent_red)
            
        self.root.after(0, self.update_status)

    def stop_service(self):
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="disabled")
        self.lbl_status.config(text="DETENIENDO...", fg=self.accent_blue)
        self.lbl_info.config(text="Solicitando detención de servicio...", fg=self.accent_blue)
        self.root.update_idletasks()
        
        # Lanzar la operación en un hilo separado
        threading.Thread(target=self._stop_service_thread, daemon=True).start()

    def _stop_service_thread(self):
        service_name = self.service_var.get().strip()
        try:
            # Ejecutar detención de servicio
            res = subprocess.run(
                ["sc", "stop", service_name], 
                capture_output=True, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if res.returncode == 0 or "not running" in res.stderr:
                self.lbl_info.config(text=f"Servicio '{service_name}' detenido correctamente.", fg=self.accent_green)
                # Abrir WitMotion si está seleccionado
                if self.open_witmotion_var.get():
                    self.launch_witmotion()
            else:
                self.lbl_info.config(text=f"Detalle: {res.stderr.strip()}", fg=self.accent_red)
        except Exception as e:
            self.lbl_info.config(text=f"Error: {str(e)}", fg=self.accent_red)
            
        self.root.after(0, self.update_status)

    def launch_witmotion(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        witmotion_path = os.path.join(
            script_dir, 
            "Download the WitMotion Software", 
            "Witmotion(V2025.11.26.0) (1)", 
            "WitMotion.exe"
        )
        if os.path.exists(witmotion_path):
            try:
                # Ejecutar WitMotion en segundo plano de manera asíncrona
                subprocess.Popen([witmotion_path], cwd=os.path.dirname(witmotion_path))
                self.lbl_info.config(text="Software WitMotion iniciado.", fg=self.accent_green)
            except Exception as e:
                self.lbl_info.config(text=f"Error al iniciar WitMotion: {str(e)}", fg=self.accent_red)
        else:
            self.lbl_info.config(text="No se encontró WitMotion.exe en la ruta de descargas.", fg=self.accent_red)

    def auto_refresh(self):
        self.update_status()
        # Refrescar cada 2000 milisegundos (2 segundos)
        self.root.after(2000, self.auto_refresh)

if __name__ == "__main__":
    root = tk.Tk()
    app = ServiceControlApp(root)
    root.mainloop()
