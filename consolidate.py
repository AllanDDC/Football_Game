#!/usr/bin/env python3
"""
Consolidador de archivos por extensión.
Copia el contenido de todos los archivos de un árbol de directorios
en archivos únicos por extensión dentro de una carpeta plana.

Uso:
    python consolidate.py [directorio_origen] [directorio_destino]

Si no se especifican argumentos, se usa el directorio actual como origen
y se crea una carpeta 'consolidado' en el directorio actual.
"""

import os
import sys
from pathlib import Path
from collections import defaultdict

# Extensiones que queremos procesar (vacío = todas)
EXTENSIONES_INTERES = {'.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.scss', '.sql', '.json', '.txt', '.md', '.yaml', '.yml', '.toml', '.ini', '.conf', '.sh', '.bat', '.env', '.rs'}

# Directorios a ignorar (nombres exactos)
IGNORAR_DIRS = {
    '__pycache__', 'node_modules', '.git', '.venv', 'venv', 'env',
    'dist', 'build', 'target', 'out', '.idea', '.vscode', 'coverage',
    'cypress/videos', 'cypress/screenshots', '.next', '.nuxt',
    'src-tauri/target', 'target', '__pycache__', 'logs', 'temp', 'tmp'
}

def deberia_procesar(ruta: Path) -> bool:
    """Decide si un archivo debe ser incluido."""
    for parte in ruta.parent.parts:
        if parte in IGNORAR_DIRS:
            return False
    if ruta.name.startswith('.') or ruta.name in {'package-lock.json', 'yarn.lock', 'poetry.lock', 'Cargo.lock'}:
        return False
    if EXTENSIONES_INTERES:
        return ruta.suffix in EXTENSIONES_INTERES
    return True

def consolidate(source_root: Path, dest_dir: Path):
    """Recorre source_root y consolida archivos por extensión en dest_dir."""
    archivos_por_ext = defaultdict(list)

    for ruta in source_root.rglob('*'):
        if not ruta.is_file():
            continue
        if not deberia_procesar(ruta):
            continue
        archivos_por_ext[ruta.suffix].append(ruta)

    dest_dir.mkdir(parents=True, exist_ok=True)

    for ext, lista_archivos in archivos_por_ext.items():
        nombre_salida = f"codigo_{ext[1:]}.txt" if ext else "codigo_sin_ext.txt"
        archivo_salida = dest_dir / nombre_salida

        with open(archivo_salida, 'w', encoding='utf-8', errors='replace') as out:
            out.write(f"# ============================================================\n")
            out.write(f"# Archivos con extensión {ext} consolidados\n")
            out.write(f"# Origen: {source_root.resolve()}\n")
            out.write(f"# ============================================================\n\n")

            for archivo in sorted(lista_archivos, key=lambda p: str(p)):
                rel = archivo.relative_to(source_root)
                abs_path = archivo.resolve()
                out.write(f"\n# ---------- INICIO: {rel} (ruta absoluta: {abs_path}) ----------\n")
                try:
                    contenido = archivo.read_text(encoding='utf-8', errors='ignore')
                    out.write(contenido)
                    if not contenido.endswith('\n'):
                        out.write('\n')
                except Exception as e:
                    out.write(f"# ERROR al leer el archivo: {e}\n")
                out.write(f"# ---------- FIN: {rel} (ruta absoluta: {abs_path}) ----------\n")

            out.write(f"\n# Total de archivos consolidados: {len(lista_archivos)}\n")

    print(f"✅ Consolidación completada. Archivos generados en: {dest_dir.resolve()}")
    for ext, lista in archivos_por_ext.items():
        print(f"   - {ext} : {len(lista)} archivos")

def main():
    # Valores por defecto
    if len(sys.argv) == 1:
        origen = Path.cwd()
        destino = Path.cwd() / "consolidado"
    elif len(sys.argv) == 2:
        origen = Path(sys.argv[1]).resolve()
        destino = Path.cwd() / "consolidado"
    elif len(sys.argv) == 3:
        origen = Path(sys.argv[1]).resolve()
        destino = Path(sys.argv[2]).resolve()
    else:
        print(__doc__)
        sys.exit(1)

    if not origen.exists() or not origen.is_dir():
        print(f"Error: '{origen}' no es un directorio válido.")
        sys.exit(1)

    consolidate(origen, destino)

if __name__ == '__main__':
    main()