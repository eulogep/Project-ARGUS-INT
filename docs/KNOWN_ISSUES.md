# ARGUS-INT Known Issues

Liste des problèmes connus à la version Release Candidate 1.0 :

1. **Latence vLLM (Génération de brouillons HUMINT)**
   - *Problème* : Sur les GPUs avec < 24Go de VRAM (ex: RTX 3080/4080 16GB), le "Continuous Batching" de vLLM peut saturer la mémoire et bloquer la file d'attente Celery.
   - *Workaround* : Lancez le conteneur avec la variable `VLLM_GPU_MEMORY_UTILIZATION=0.85` pour forcer un seuil plus strict.

2. **Désynchronisation Tor / SOCKS5 proxy**
   - *Problème* : Le ProxyRouter bloque après de nombreuses requêtes OSINT vers les réseaux sociaux (Rate limits bloquant les nœuds de sortie Tor).
   - *Workaround* : Configurez un pool de proxys résidentiels dans le fichier `config.yaml` du router.

3. **PaddleOCR sur images très corrompues**
   - *Problème* : L'extraction de texte sur des images volontairement corrompues par des *Adversarial Patches* très agressifs retourne du texte tronqué.
   - *Workaround* : Appliquez le filtre de débruitage OpenCV avant de soumettre l'image au moteur de vision.
