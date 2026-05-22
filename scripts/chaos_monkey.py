# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Chaos Monkey (Resilience & Chaos Engineering)
scripts/chaos_monkey.py

Script qui cible les conteneurs Docker de la stack ARGUS-INT et induit aléatoirement
des pannes (kill, restart) ou des throttles CPU pour vérifier la résilience,
le mécanisme de retry Celery et les fallbacks vLLM.
"""

import argparse
import random
import sys
import time
import structlog
try:
    import docker
except ImportError:
    print("Erreur: Le module 'docker' est requis (pip install docker).")
    sys.exit(1)

logger = structlog.get_logger()

# Conteneurs cibles prioritaires
TARGET_CONTAINERS = [
    "argus-celery-worker",
    "argus-celery-gpu-heavy",
    "argus-celery-gpu-light",
    "argus-backend",
]

# Actions de chaos possibles
class ChaosAction:
    KILL = "kill"
    RESTART = "restart"
    PAUSE = "pause_unpause"

def get_target_containers(client: docker.DockerClient) -> list[docker.models.containers.Container]:
    """Récupère les conteneurs cibles s'ils sont en cours d'exécution."""
    running_containers = client.containers.list()
    targets = []
    for container in running_containers:
        for target_name in TARGET_CONTAINERS:
            if target_name in container.name:
                targets.append(container)
                break
    return targets

def execute_chaos(container: docker.models.containers.Container, action: str, dry_run: bool = False):
    """Exécute une action de chaos sur un conteneur."""
    logger.info("chaos.execute", container=container.name, action=action, dry_run=dry_run)
    
    if dry_run:
        return

    try:
        if action == ChaosAction.KILL:
            # Envoie SIGKILL, provoque un crash immédiat sans nettoyage
            container.kill()
            logger.warning("chaos.killed", container=container.name)
        
        elif action == ChaosAction.RESTART:
            # Redémarre brusquement (timeout=0 équivaut à un kill suivi d'un start)
            container.restart(timeout=0)
            logger.warning("chaos.restarted", container=container.name)
            
        elif action == ChaosAction.PAUSE:
            # Gèle le processus pendant quelques secondes, puis le reprend (simule saturation I/O ou CPU)
            container.pause()
            logger.warning("chaos.paused", container=container.name)
            time.sleep(random.uniform(5, 15))
            container.unpause()
            logger.warning("chaos.unpaused", container=container.name)
            
    except Exception as exc:
        logger.error("chaos.action_failed", container=container.name, action=action, error=str(exc))

def main():
    parser = argparse.ArgumentParser(description="ARGUS-INT Chaos Monkey")
    parser.add_argument("--dry-run", action="store_true", help="Afficher les actions sans les exécuter")
    parser.add_argument("--interval", type=int, default=60, help="Intervalle (en secondes) entre deux événements de chaos")
    parser.add_argument("--count", type=int, default=5, help="Nombre total d'événements à déclencher (0 = infini)")
    args = parser.parse_args()

    client = docker.from_env()
    
    logger.info("chaos.start", dry_run=args.dry_run, interval=args.interval, max_events=args.count)
    
    events_triggered = 0
    while True:
        targets = get_target_containers(client)
        if not targets:
            logger.warning("chaos.no_targets", message="Aucun conteneur cible en cours d'exécution.")
            time.sleep(args.interval)
            continue
            
        target = random.choice(targets)
        action = random.choice([ChaosAction.KILL, ChaosAction.RESTART, ChaosAction.PAUSE])
        
        execute_chaos(target, action, args.dry_run)
        events_triggered += 1
        
        if args.count > 0 and events_triggered >= args.count:
            logger.info("chaos.done", events_triggered=events_triggered)
            break
            
        logger.info("chaos.sleep", duration=args.interval)
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
