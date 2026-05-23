from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import time

router = APIRouter()

CRASH_REPORTS_DIR = "/opt/argus-data/crash_reports"
os.makedirs(CRASH_REPORTS_DIR, exist_ok=True)

@router.post("/crash-report")
async def receive_crash_report(file: UploadFile = File(...)):
    """
    Reçoit un rapport de crash chiffré (GPG) envoyé de manière anonyme.
    """
    if not file.filename.endswith(".gpg"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers chiffrés GPG sont acceptés.")
    
    # Génération d'un nom de fichier sécurisé pour éviter les injections
    safe_filename = f"crash_{int(time.time())}.tar.gz.gpg"
    file_path = os.path.join(CRASH_REPORTS_DIR, safe_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            # Lire par chunks pour éviter le débordement de mémoire
            while content := await file.read(1024 * 1024):
                buffer.write(content)
        return {"status": "success", "message": "Crash report received anonymously."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")
