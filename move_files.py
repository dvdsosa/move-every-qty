"""Monitorización NTFS y traslado por lotes de imágenes.

Este script supervisa una carpeta de origen y, cuando supera un umbral
de imágenes, mueve de forma atómica un lote de archivos (los más antiguos)
a una subcarpeta de destino nombrada por marca temporal. Incluye una
interfaz gráfica con Tkinter para configurar rutas, intervalo, tamaño de
lote y margen seguro. El monitoreo se ejecuta en un hilo separado y los
logs se muestran en una consola integrada además de guardarse por lote.

Compilar para Windows (PyInstaller):
    pyinstaller --onefile --noconsole move_files.py
"""

import os
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from datetime import datetime

class MoveFilesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitorización NTFS")
        self.root.geometry("750x600")
        
        self.is_monitoring = False
        self.monitor_thread = None
        self.stop_event = threading.Event()
        
        self.create_widgets()
        
    def create_widgets(self):
        # Frame de configuración
        config_frame = tk.LabelFrame(self.root, text="Configuración", padx=10, pady=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # FOLDER_TO_WATCH
        tk.Label(config_frame, text="Carpeta Origen:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.folder_watch_var = tk.StringVar(value=r"D:/DinoCapture/Timelapse photo 001")
        tk.Entry(config_frame, textvariable=self.folder_watch_var, width=60).grid(row=0, column=1, padx=5, pady=2)
        tk.Button(config_frame, text="Examinar", command=self.browse_watch_folder).grid(row=0, column=2, padx=5, pady=2)
        
        # NEW_FOLDERS_TO
        tk.Label(config_frame, text="Carpeta Destino:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.folder_dest_var = tk.StringVar(value=r"D:/")
        tk.Entry(config_frame, textvariable=self.folder_dest_var, width=60).grid(row=1, column=1, padx=5, pady=2)
        tk.Button(config_frame, text="Examinar", command=self.browse_dest_folder).grid(row=1, column=2, padx=5, pady=2)
        
        # CHECK_INTERVAL
        tk.Label(config_frame, text="Intervalo (s):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.interval_var = tk.IntVar(value=60)
        tk.Entry(config_frame, textvariable=self.interval_var, width=15).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # MAX_IMAGES_PER_FOLDER
        tk.Label(config_frame, text="Máx imgs a mover:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.max_imgs_var = tk.IntVar(value=250)
        tk.Entry(config_frame, textvariable=self.max_imgs_var, width=15).grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        # SAFE_MARGIN
        tk.Label(config_frame, text="Margen Seguro:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.safe_margin_var = tk.IntVar(value=20)
        tk.Entry(config_frame, textvariable=self.safe_margin_var, width=15).grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Botón de Control
        self.control_btn = tk.Button(self.root, text="Iniciar Monitoreo", font=("Arial", 12, "bold"), bg="green", fg="white", command=self.toggle_monitoring)
        self.control_btn.pack(pady=10)
        
        # Consola Integrada
        console_frame = tk.LabelFrame(self.root, text="Consola de Registro", padx=10, pady=10)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.console = scrolledtext.ScrolledText(console_frame, state='disabled', wrap=tk.WORD, font=("Consolas", 10))
        self.console.pack(fill=tk.BOTH, expand=True)
        
    def log(self, message):
        """Añade un mensaje a la consola integrada."""
        self.console.config(state='normal')
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
        self.console.config(state='disabled')
        
    def browse_watch_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_watch_var.set(folder)
            
    def browse_dest_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_dest_var.set(folder)
            
    def toggle_monitoring(self):
        if not self.is_monitoring:
            self.start_monitoring()
        else:
            self.stop_monitoring()
            
    def start_monitoring(self):
        try:
            interval = self.interval_var.get()
            max_imgs = self.max_imgs_var.get()
            safe_margin = self.safe_margin_var.get()
        except ValueError:
            messagebox.showerror("Error", "Los valores de intervalo, máx imgs y margen deben ser enteros.")
            return
            
        watch_folder = self.folder_watch_var.get()
        dest_folder = self.folder_dest_var.get()
        
        if not watch_folder or not dest_folder:
            messagebox.showerror("Error", "Debe especificar las carpetas de origen y destino.")
            return
            
        self.is_monitoring = True
        self.stop_event.clear()
        
        self.control_btn.config(text="Detener Monitoreo", bg="red")
        
        # Iniciar el hilo de monitoreo
        self.monitor_thread = threading.Thread(
            target=self.monitor_loop,
            args=(watch_folder, dest_folder, interval, max_imgs, safe_margin),
            daemon=True
        )
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        self.is_monitoring = False
        self.stop_event.set()
        self.control_btn.config(text="Iniciar Monitoreo", bg="green")
        self.log(f"[{datetime.now().strftime('%H:%M:%S')}] Deteniendo monitoreo... (por favor espere al último ciclo)")

    def get_files_sorted_by_time(self, folder_path):
        try:
            files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                     if os.path.isfile(os.path.join(folder_path, f))]
            files.sort(key=lambda x: os.path.getmtime(x))
            return files
        except Exception as e:
            self.root.after(0, self.log, f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] Falló el listado de archivos: {e}")
            return []

    def move_files_to_new_folder(self, files_to_move, dest_folder):
        now_str = datetime.now().strftime('%Y-%m-%d-%H-%M')
        new_folder_path = os.path.join(dest_folder, now_str)
        
        counter = 1
        original_path = new_folder_path
        while os.path.exists(new_folder_path):
            new_folder_path = f"{original_path}_{counter}"
            counter += 1
            
        try:
            os.makedirs(new_folder_path)
        except Exception as e:
            self.root.after(0, self.log, f"[{datetime.now().strftime('%H:%M:%S')}] [CRÍTICO] Error creando destino '{new_folder_path}': {e}")
            return

        log_file_path = os.path.join(new_folder_path, "move_log.txt")
        successful_moves = 0
        errors = 0
        
        with open(log_file_path, "w", encoding="utf-8") as log_file:
            log_file.write(f"=== Movimiento de Bloque de Imágenes ===\n")
            log_file.write(f"Fecha de inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write(f"Archivos previstos: {len(files_to_move)}\n")
            log_file.write("-" * 40 + "\n")
            
            for file_path in files_to_move:
                filename = os.path.basename(file_path)
                dest_path = os.path.join(new_folder_path, filename)
                try:
                    os.rename(file_path, dest_path)
                    successful_moves += 1
                except PermissionError:
                    errors += 1
                    msg = f"Archivo bloqueado (en uso): {filename}"
                    log_file.write(f"[ADVERTENCIA] {msg}\n")
                except Exception as e:
                    errors += 1
                    msg = f"Error moviendo {filename}: {e}"
                    log_file.write(f"[ERROR] {msg}\n")
                    
            log_file.write("-" * 40 + "\n")
            log_file.write(f"Finalizado a las: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write(f"Éxitos: {successful_moves} | Errores: {errors}\n")
        
        self.root.after(0, self.log, f"[{datetime.now().strftime('%H:%M:%S')}] [ÉXITO] Lote de {successful_moves} imágenes movido a -> {os.path.basename(new_folder_path)} (Errores: {errors})")

    def monitor_loop(self, watch_folder, dest_folder, interval, max_imgs, safe_margin):
        os.makedirs(watch_folder, exist_ok=True)
        os.makedirs(dest_folder, exist_ok=True)
        
        self.root.after(0, self.log, "=" * 60)
        self.root.after(0, self.log, "Monitorización NTFS para Experimento Biológico Iniciada")
        self.root.after(0, self.log, "=" * 60)
        self.root.after(0, self.log, f"Ruta Origen (Live): {watch_folder}")
        self.root.after(0, self.log, f"Ruta Destino (Lotes): {dest_folder}")
        self.root.after(0, self.log, f"Intervalo: {interval} s | Límite: {max_imgs} imgs | Margen: {safe_margin} imgs")
        self.root.after(0, self.log, "=" * 60)

        while not self.stop_event.is_set():
            try:
                current_time = datetime.now().strftime('%H:%M:%S')
                all_files = self.get_files_sorted_by_time(watch_folder)
                total_files = len(all_files)
                
                self.root.after(0, self.log, f"[{current_time}] [PING] Chequeo de carpeta completado. Archivos vivos: {total_files}")
                
                if total_files >= (max_imgs + safe_margin):
                    self.root.after(0, self.log, f"[{datetime.now().strftime('%H:%M:%S')}] [ACCIÓN] Límite superado. Iniciando redirección NTFS...")
                    files_to_move = all_files[:max_imgs]
                    self.move_files_to_new_folder(files_to_move, dest_folder)
                
            except Exception as e:
                self.root.after(0, self.log, f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR CRÍTICO DEL BUCLE]: {e}")
                
            # Sleep iterativo para reaccionar rápido al evento 'stop'
            for _ in range(interval):
                if self.stop_event.is_set():
                    break
                time.sleep(1)
                
        self.root.after(0, self.log, "Monitorización completamente detenida.")

def main():
    root = tk.Tk()
    app = MoveFilesApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()