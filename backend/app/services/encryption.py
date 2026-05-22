# ==============================================================================
# Project ARGUS-INT - Multi-Spectrum Intelligence Fusion Platform
# ==============================================================================
# Copyright (C) 2026 emc2
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
ARGUS-INT — Chiffrement AES-256-GCM souverain
backend/app/services/encryption.py

Toutes les données sensibles (emails, pseudos, mots de passe leakés)
sont chiffrées au repos avec AES-256-GCM.
"""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import settings


def _get_key() -> bytes:
    """Dérive une clé AES-256 depuis la config (32 bytes)."""
    key = settings.ENCRYPTION_KEY.encode("utf-8")
    return key[:32].ljust(32, b'\x00')


def encrypt_data(plaintext: str) -> str:
    """
    Chiffre une chaîne avec AES-256-GCM.
    Retourne : base64(nonce + ciphertext)
    """
    key = _get_key()
    nonce = os.urandom(12)  # 96 bits — standard GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_data(encrypted: str) -> str:
    """Déchiffre une chaîne chiffrée par encrypt_data."""
    key = _get_key()
    data = base64.b64decode(encrypted.encode("utf-8"))
    nonce = data[:12]
    ciphertext = data[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def hash_target(target: str) -> str:
    """Génère un hash SHA-256 de la cible pour l'indexation sans exposition."""
    import hashlib
    return hashlib.sha256(target.encode()).hexdigest()
