import os
import time
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN MEDIANTE VARIABLES GLOBALES
# ==========================================
# Rutas (¡Asegúrate de cambiar estas rutas por tus directorios reales!)
FOLDER_TO_WATCH = r"D:\DinoCapture\Timelapse photo 001"
NEW_FOLDERS_TO  = r"D:\\"

# Parámetros del experimento
CHECK_INTERVAL = 60            # Tiempo en segundos entre cada revisión (ej: 60 s = 1 min)
MAX_IMAGES_PER_FOLDER = 250  # Etapa de partición (mover bloque de 10,000 en 10,000)
SAFE_MARGIN = 20               # Archivos recientes que NUNCA se tocarán para evitar colisiones
# ==========================================

def get_files_sorted_by_time(folder_path):
    """
    Obtiene los archivos en la carpeta objetivo y los ordena cronológicamente (más antiguo primero)
    esencial para mantener la secuencia temporal del Tracking IA (SAM 2).
    """
    try:
        # Extraemos solo archivos ignorando subcarpetas.
        files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                 if os.path.isfile(os.path.join(folder_path, f))]
        
        # Ordenamos mediante el tiempo de modificación del archivo
        files.sort(key=lambda x: os.path.getmtime(x))
        return files
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] Falló el listado de archivos: {e}")
        return []

def move_files_to_new_folder(files_to_move):
    """
    Mueve (NO copia) los archivos a un nuevo directorio y genera los logs pertinentes.
    """
    # 4. NOMENCLATURA DE CARPETAS BASADA EN MARCA DE TIEMPO
    now_str = datetime.now().strftime('%Y-%m-%d-%H-%M')
    new_folder_path = os.path.join(NEW_FOLDERS_TO, now_str)
    
    # Tolerancia a duplicidad (en el raro caso de que se creen 2 carpetas en el mismo minuto)
    counter = 1
    original_path = new_folder_path
    while os.path.exists(new_folder_path):
        new_folder_path = f"{original_path}_{counter}"
        counter += 1
        
    try:
        os.makedirs(new_folder_path)
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [CRÍTICO] Error creando destino '{new_folder_path}': {e}")
        return

    log_file_path = os.path.join(new_folder_path, "move_log.txt")
    
    successful_moves = 0
    errors = 0
    
    # 5. ROBUSTEZ Y CONTROL DE ERRORES (Generación de log propio en la nueva subcarpeta)
    with open(log_file_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"=== Movimiento de Bloque de Imágenes ===\n")
        log_file.write(f"Fecha de inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"Archivos previstos: {len(files_to_move)}\n")
        log_file.write("-" * 40 + "\n")
        
        for file_path in files_to_move:
            filename = os.path.basename(file_path)
            dest_path = os.path.join(new_folder_path, filename)
            
            # 3. OPERACIÓN DE MOVIMIENTO INSTANTÁNEO 
            try:
                # os.rename realiza un movimiento atómico (cambio de puntero en la MFT de NTFS), no reescribe datos.
                os.rename(file_path, dest_path)
                successful_moves += 1
            except PermissionError:
                # El componente más frágil: bloqueos por el software externo DinoCapture o indexación de Windows
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
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [ÉXITO] Lote de {successful_moves} imágenes movido a -> {os.path.basename(new_folder_path)} (Errores: {errors})")

def main():
    print("=" * 60)
    print("Iniciando Monitorización NTFS para Experimento Biológico")
    print("=" * 60)
    print(f"Ruta Origen (Live): {FOLDER_TO_WATCH}")
    print(f"Ruta Destino (Lotes): {NEW_FOLDERS_TO}")
    print(f"Intervalo: {CHECK_INTERVAL} s | Límite: {MAX_IMAGES_PER_FOLDER} imgs | Margen: {SAFE_MARGIN} imgs")
    print("=" * 60)
    
    # Comprobar/Crear estructuralmente los directorios requeridos
    os.makedirs(FOLDER_TO_WATCH, exist_ok=True)
    os.makedirs(NEW_FOLDERS_TO, exist_ok=True)

    # 2. LÓGICA DE MONITOREO INFINITO (Bajo impacto en CPU)
    while True:
        try:
            current_time = datetime.now().strftime('%H:%M:%S')
            
            all_files = get_files_sorted_by_time(FOLDER_TO_WATCH)
            total_files = len(all_files)
            
            print(f"[{current_time}] [PING] Chequeo de carpeta completado. Archivos vivos: {total_files}")
            
            # Comprobación de corte (Superar los que se moverán + el margen seguro de 20 imágenes)
            if total_files >= (MAX_IMAGES_PER_FOLDER + SAFE_MARGIN):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [ACCIÓN] Límite superado. Iniciando redirección NTFS...")
                
                # Excluir el margen seguro cortando la lista
                # Seleccionamos exclusivamente los primeros MAX_IMAGES_PER_FOLDER (los más viejos)
                files_to_move = all_files[:MAX_IMAGES_PER_FOLDER]
                
                # Ejecutar traspaso
                move_files_to_new_folder(files_to_move)
            
        except KeyboardInterrupt:
            # Salida limpia si el usuario cierra la consola con Ctrl+C
            print("\nMonitoreo detenido por el usuario. Saliendo de manera segura...")
            break
        except Exception as e:
            # Fallback genérico para que el proceso nuca muera en sus 5 días
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR CRÍTICO DEL BUCLE]: {e}")
            
        # Reposo para NO saturar el HDD/CPU.
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()