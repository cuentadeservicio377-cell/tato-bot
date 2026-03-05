"""
data/seed.py — Carga los expedientes de Tato desde los DOCX a PostgreSQL.

Uso:
  python data/seed.py \\
    --control "../- - -C O N T R O L  E X P E D I E N T E S---.docx" \\
    --pendientes "../- 2026  FEBRERO JUZGADOS PENDIENTES.docx" \\
    --user-id <TATO_TELEGRAM_USER_ID>

IMPORTANTE: Ejecutar DESPUÉS de que Tato haya hecho /start en el bot
(necesita que el usuario exista en la DB).
"""

import argparse
import os
import sys
from pathlib import Path

# Agregar directorio padre al path para importar memory
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from parse_docx import parse_control_expedientes, parse_pendientes, merge_pendientes_into_expedientes
import memory


def main():
    parser = argparse.ArgumentParser(description="Seed expedientes de Tato a PostgreSQL")
    parser.add_argument("--control",    required=True, help="Ruta al DOCX de Control de Expedientes")
    parser.add_argument("--pendientes", required=True, help="Ruta al DOCX de Juzgados Pendientes")
    parser.add_argument("--user-id",    required=True, type=int, help="Telegram user_id de Tato")
    args = parser.parse_args()

    control_path    = Path(args.control).expanduser().resolve()
    pendientes_path = Path(args.pendientes).expanduser().resolve()
    user_id         = args.user_id

    # Validaciones
    if not control_path.exists():
        print(f"ERROR: No encontré el archivo: {control_path}")
        sys.exit(1)
    if not pendientes_path.exists():
        print(f"ERROR: No encontré el archivo: {pendientes_path}")
        sys.exit(1)

    # Verificar que el usuario existe en la DB
    user = memory.get_user(user_id)
    if not user:
        print(f"ERROR: El usuario {user_id} no existe en la DB.")
        print("Asegúrate de que Tato haya hecho /start en el bot antes de correr el seed.")
        sys.exit(1)

    print(f"Usuario encontrado: {user.get('user_id')} ✓")

    # 1. Parsear control de expedientes
    print(f"\nParsando {control_path.name}...")
    expedientes = parse_control_expedientes(str(control_path))
    print(f"  → {len(expedientes)} expedientes parseados")

    # 2. Parsear pendientes
    print(f"Parsando {pendientes_path.name}...")
    pendientes = parse_pendientes(str(pendientes_path))
    print(f"  → {len(pendientes)} pendientes parseados")

    # 3. Merge: actualizar expedientes con datos de pendientes
    print("Cruzando información...")
    expedientes = merge_pendientes_into_expedientes(expedientes, pendientes)
    matches = sum(1 for p in pendientes if any(
        e["numero"].strip() == p["numero"].strip() for e in expedientes
    ))
    print(f"  → {matches} pendientes cruzados con expedientes")

    # 4. Estadísticas
    activos    = sum(1 for e in expedientes if e["estado"] == "activo")
    caducidad  = sum(1 for e in expedientes if e["estado"] == "caducidad")
    terminados = sum(1 for e in expedientes if e["estado"] == "terminado")

    print(f"\nResumen:")
    print(f"  Total:      {len(expedientes)}")
    print(f"  Activos:    {activos}")
    print(f"  Caducidad:  {caducidad}")
    print(f"  Terminados: {terminados}")

    # 5. Confirmar antes de escribir
    print(f"\n¿Guardar {len(expedientes)} expedientes para user_id={user_id}? (s/n): ", end="")
    resp = input().strip().lower()
    if resp not in ("s", "si", "sí", "y", "yes"):
        print("Cancelado.")
        sys.exit(0)

    # 6. Guardar en PostgreSQL
    print("Guardando en PostgreSQL...")
    memory.save_expedientes_sync(user_id, expedientes)
    print(f"✅ {len(expedientes)} expedientes guardados para user_id={user_id}")
    print("\nPróximo paso: conectar Google OAuth para que el bot cree la hoja de Sheets.")


if __name__ == "__main__":
    main()
