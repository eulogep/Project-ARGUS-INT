# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Vision Evasion Testing
tests/red_team/vision_evasion.py

Suite PyTest pour évaluer la robustesse des modèles de Vision (YOLOv8, InsightFace)
face aux Adversarial Patches (ex: imprimés sur un t-shirt ou masque).
"""
import pytest
import numpy as np
try:
    import cv2
except ImportError:
    pass

# Mock du pipeline de détection d'objets pour les tests si YOLOv8 n'est pas chargé
def mock_yolov8_detect(image: np.ndarray) -> list:
    """Simulation de la détection: si l'image contient un carré blanc au centre, on détecte une 'person'."""
    h, w = image.shape[:2]
    center_roi = image[h//2-20:h//2+20, w//2-20:w//2+20]
    # Si la zone centrale a une moyenne > 200 (proche du blanc), c'est une "person" non masquée
    if np.mean(center_roi) > 200:
        return [{"class": "person", "conf": 0.85}]
    return []

# Mock pour InsightFace (détection de visage)
def mock_insightface_detect(image: np.ndarray) -> list:
    """Simulation de la détection faciale: carré blanc en haut = visage."""
    h, w = image.shape[:2]
    face_roi = image[20:60, w//2-20:w//2+20]
    if np.mean(face_roi) > 200:
        return [{"embedding": np.random.rand(512).tolist()}]
    return []

def apply_adversarial_patch(image: np.ndarray, patch: np.ndarray, x: int, y: int) -> np.ndarray:
    """Applique un patch de pixels (ex: bruit de foolbox) sur une image."""
    img = image.copy()
    ph, pw = patch.shape[:2]
    img[y:y+ph, x:x+pw] = patch
    return img

@pytest.fixture
def base_person_image():
    """Crée une image factice de 640x640 représentant une personne (carré blanc au centre)."""
    img = np.zeros((640, 640, 3), dtype=np.uint8)
    img[200:600, 200:440] = [255, 255, 255]
    return img

@pytest.fixture
def base_face_image():
    """Crée une image factice de 112x112 représentant un visage (carré blanc en haut)."""
    img = np.zeros((112, 112, 3), dtype=np.uint8)
    img[20:60, 36:76] = [255, 255, 255]
    return img


def test_yolov8_adversarial_patch_evasion(base_person_image):
    """
    Test d'évasion YOLOv8 : un patch d'Adversarial Noise sur le "torse" 
    doit rendre la personne "invisible" pour le détecteur (Evasion rate).
    """
    # 1. Vérification que la personne est détectée normalement
    normal_results = mock_yolov8_detect(base_person_image)
    assert len(normal_results) == 1, "La personne de base n'est pas détectée"
    assert normal_results[0]["class"] == "person"

    # 2. Génération d'un patch bruité (simulation d'Advertorch/Foolbox)
    patch = np.random.randint(0, 100, (40, 40, 3), dtype=np.uint8)
    
    # 3. Application du patch au centre
    h, w = base_person_image.shape[:2]
    adv_img = apply_adversarial_patch(base_person_image, patch, w//2-20, h//2-20)

    # 4. Vérification de l'évasion
    adv_results = mock_yolov8_detect(adv_img)
    # L'objectif de l'attaquant est que len(adv_results) == 0 (évasion réussie)
    # Dans ce test, on s'attend à ce que l'évasion fonctionne (le mock le simule).
    assert len(adv_results) == 0, "YOLOv8 a détecté la personne malgré l'Adversarial Patch"


def test_insightface_adversarial_glasses(base_face_image):
    """
    Test d'évasion InsightFace : simulation de lunettes adversariales
    bloquant l'extraction du visage ou corrompant l'embedding.
    """
    # 1. Visage normal
    normal_faces = mock_insightface_detect(base_face_image)
    assert len(normal_faces) == 1, "Visage de base non détecté"
    
    # 2. Patch de type "lunettes adverses"
    glasses_patch = np.zeros((10, 40, 3), dtype=np.uint8) # Bande noire
    
    # 3. Application du patch
    h, w = base_face_image.shape[:2]
    adv_img = apply_adversarial_patch(base_face_image, glasses_patch, w//2-20, 30)

    # 4. Vérification de l'extraction (doit échouer ou être dégradée)
    adv_faces = mock_insightface_detect(adv_img)
    assert len(adv_faces) == 0, "InsightFace a extrait un visage malgré les lunettes adversariales"
