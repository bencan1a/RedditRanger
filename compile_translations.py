import os
import subprocess
from pathlib import Path

def compile_translations():
    translations_dir = Path(__file__).parent / "translations"
    
    for lang_dir in translations_dir.glob("*/LC_MESSAGES"):
        po_file = lang_dir / "messages.po"
        mo_file = lang_dir / "messages.mo"
        
        if po_file.exists():
            try:
                subprocess.run(['msgfmt', str(po_file), '-o', str(mo_file)], check=True)
                print(f"Compiled translations for {lang_dir.parent.name}")
            except subprocess.CalledProcessError as e:
                print(f"Error compiling translations for {lang_dir.parent.name}: {e}")
            except FileNotFoundError:
                print("msgfmt not found. Installing gettext...")
                subprocess.run(['apt-get', 'update'], check=True)
                subprocess.run(['apt-get', 'install', '-y', 'gettext'], check=True)
                # Retry compilation
                subprocess.run(['msgfmt', str(po_file), '-o', str(mo_file)], check=True)
                print(f"Compiled translations for {lang_dir.parent.name}")

if __name__ == "__main__":
    compile_translations()
