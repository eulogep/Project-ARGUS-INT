#!/usr/bin/env python3
# ==============================================================================
# Project ARGUS-INT - Multi-Spectrum Intelligence Fusion Platform
# ==============================================================================
# Copyright (C) 2026 eulogep
#
# This file is part of Project ARGUS-INT.
#
# Project ARGUS-INT is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Project ARGUS-INT is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Project ARGUS-INT. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================

"""
ARGUS-INT — SPDX License Header & Watermark Enforcement Script
scripts/inject_spdx.py

Parcourt récursivement le répertoire de travail pour s'assurer que
chaque fichier source contient bien l'en-tête de licence AGPLv3.
"""

import os
import sys

# Configuration de l'en-tête standard (Python, Shell, YAML, etc.)
PYTHON_HEADER = """# ==============================================================================
# Project ARGUS-INT - Multi-Spectrum Intelligence Fusion Platform
# ==============================================================================
# Copyright (C) 2026 eulogep
#
# This file is part of Project ARGUS-INT.
#
# Project ARGUS-INT is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Project ARGUS-INT is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Project ARGUS-INT. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""

# Configuration de l'en-tête pour le Rust / C / C++
RUST_HEADER = """// ==============================================================================
// Project ARGUS-INT - Multi-Spectrum Intelligence Fusion Platform
// ==============================================================================
// Copyright (C) 2026 eulogep
//
// This file is part of Project ARGUS-INT.
//
// Project ARGUS-INT is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Project ARGUS-INT is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with Project ARGUS-INT. If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later
// ==============================================================================
"""

EXCLUDED_DIRS = {".git", ".github", ".venv", "venv", "__pycache__", "target", "assets", "node_modules", ".next"}
EXCLUDED_FILES = {"LICENSE", "README.md", "DISCLAIMER.md"}

def check_and_inject(filepath: str, check_only: bool = False) -> bool:
    _, ext = os.path.splitext(filepath)
    header = ""
    comment_char = ""
    
    if ext in {".py", ".sh", ".yaml", ".yml"}:
        header = PYTHON_HEADER
        comment_char = "#"
    elif ext in {".rs", ".go", ".cpp", ".h"}:
        header = RUST_HEADER
        comment_char = "//"
    else:
        return True # Ignorer les types de fichiers non gérés
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        return True # Fichier binaire ou encodage non compatible

    # Vérification de la présence de la ligne SPDX-License-Identifier
    if "SPDX-License-Identifier" in content:
        return True

    if check_only:
        print(f"[!] License header missing: {filepath}")
        return False

    print(f"[*] Injecting SPDX header into: {filepath}")
    
    # Conservation du shebang si présent en première ligne
    lines = content.splitlines(keepends=True)
    if lines and lines[0].startswith("#!"):
        shebang = lines[0]
        remaining = "".join(lines[1:])
        new_content = shebang + header + "\n" + remaining
    else:
        new_content = header + "\n" + content

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    return True

def main():
    check_only = "--check" in sys.argv
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    success = True

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filtrer les répertoires exclus
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        
        for filename in filenames:
            if filename in EXCLUDED_FILES:
                continue
                
            filepath = os.path.join(dirpath, filename)
            if not check_and_inject(filepath, check_only):
                success = False

    if not success:
        sys.exit(1)
    
    print("[+] All checks passed successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()
