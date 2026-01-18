import os
import shutil
from datetime import datetime

def criar_backup():
    base_path = r"c:\Users\Pichau\Desktop\o mundo de pandorha, vscode"
    file_to_backup = os.path.join(base_path, "editor", "forge.py")
    
    # Pasta específica para esta feature
    backup_folder = os.path.join(base_path, "backup-modificações", "feature-camadas")
    os.makedirs(backup_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"forge_backup_{timestamp}.py"
    backup_path = os.path.join(backup_folder, backup_filename)

    if os.path.exists(file_to_backup):
        shutil.copy2(file_to_backup, backup_path)
        print(f"[OK] Backup criado em: {backup_path}")
    else:
        print(f"[ERRO] Arquivo não encontrado: {file_to_backup}")

if __name__ == "__main__":
    criar_backup()
