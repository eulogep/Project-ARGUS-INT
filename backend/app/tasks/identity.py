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
ARGUS-INT — Module Identity : Tâche Celery complète
backend/app/tasks/identity.py

Intègre Holehe, Sherlock-style username enumeration, etc.
"""

import asyncio
import random
import time
import httpx
import logging
from typing import Optional
from celery import shared_task
from celery.utils.log import get_task_logger

from app.celery_app import celery_app
from app.services.graph import GraphService
from app.services.proxy import ProxyPool
from app.services.encryption import encrypt_data
from app.database import get_db_session_sync

logger = get_task_logger(__name__)

# ─── User-Agent Pool ───────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

# ─── Plateformes pour l'énumération de pseudos ──────────────────────────
USERNAME_PLATFORMS = [
    {"name": "GitHub",      "url": "https://github.com/{username}",          "error_type": "status_code", "error_code": 404},
    {"name": "Twitter/X",   "url": "https://x.com/{username}",               "error_type": "status_code", "error_code": 404},
    {"name": "Instagram",   "url": "https://www.instagram.com/{username}/",  "error_type": "message",     "error_msg": "Sorry, this page"},
    {"name": "Reddit",      "url": "https://www.reddit.com/user/{username}", "error_type": "status_code", "error_code": 404},
    {"name": "TikTok",      "url": "https://www.tiktok.com/@{username}",     "error_type": "status_code", "error_code": 404},
    {"name": "HackerNews",  "url": "https://news.ycombinator.com/user?id={username}", "error_type": "message", "error_msg": "No such user"},
    {"name": "Keybase",     "url": "https://keybase.io/{username}",          "error_type": "status_code", "error_code": 404},
    {"name": "GitLab",      "url": "https://gitlab.com/{username}",          "error_type": "status_code", "error_code": 404},
    {"name": "Twitch",      "url": "https://www.twitch.tv/{username}",       "error_type": "status_code", "error_code": 404},
    {"name": "LinkedIn",    "url": "https://www.linkedin.com/in/{username}", "error_type": "status_code", "error_code": 404},
    # ... 990+ autres plateformes via fichier YAML externe
]

# ─── Holehe — Services supportés ────────────────────────────────────────
HOLEHE_SERVICES = [
    {"name": "Adobe",    "url": "https://account.adobe.com/", "method": "POST",
     "endpoint": "https://adobeid-na1.services.adobe.com/ims/check/v6/token",
     "data_key": "username"},
    {"name": "Snapchat", "url": "https://www.snapchat.com/",  "method": "POST",
     "endpoint": "https://feelinsonice-hrd.appspot.com/loq/suggest_username",
     "data_key": "username"},
    # ... 100+ services
]


# ============================================================
#  TÂCHE CELERY PRINCIPALE
# ============================================================

@celery_app.task(
    bind=True,
    name="app.tasks.identity.run_identity_search",
    max_retries=3,
    default_retry_delay=30,
    queue="identity"
)
def run_identity_search(
    self,
    investigation_id: str,
    target: str,
    target_type: str,  # "email" | "username" | "phone"
    depth: int = 1
) -> dict:
    """
    Tâche Celery principale pour la recherche d'identités.
    Exécute les sous-modules de manière asynchrone et injecte dans Neo4j.
    """
    logger.info(f"[Identity] Démarrage recherche — target={target}, type={target_type}, depth={depth}")

    results = {"profiles": [], "email_services": [], "raw_count": 0}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Exécution asynchrone dans le worker Celery (event loop isolé)
        if target_type == "username":
            results["profiles"] = loop.run_until_complete(
                _enumerate_username(target, depth)
            )
        elif target_type == "email":
            results["email_services"] = loop.run_until_complete(
                _holehe_check(target, depth)
            )
            if depth >= 2:
                # Recherche croisée : extraire pseudo depuis email
                username_guess = target.split("@")[0]
                results["profiles"] = loop.run_until_complete(
                    _enumerate_username(username_guess, depth - 1)
                )

        results["raw_count"] = len(results["profiles"]) + len(results["email_services"])

        # ─── Injection dans Neo4j ──────────────────────────────────────
        graph = GraphService()
        _inject_to_graph(graph, investigation_id, target, target_type, results)

        # ─── Mise à jour PostgreSQL ────────────────────────────────────
        with get_db_session_sync() as db:
            db.execute(
                """UPDATE investigations
                   SET result_count = result_count + $1, status = 'COLLECTING'
                   WHERE id = $2""",
                results["raw_count"], investigation_id
            )

        logger.info(f"[Identity] Terminé — {results['raw_count']} résultats injectés")
        return results

    except Exception as exc:
        logger.error(f"[Identity] Erreur : {exc}", exc_info=True)
        raise self.retry(exc=exc)

    finally:
        loop.close()


# ============================================================
#  SOUS-MODULE : Énumération de pseudos
# ============================================================

async def _enumerate_username(username: str, depth: int) -> list[dict]:
    """
    Vérifie l'existence d'un username sur N plateformes en parallèle.
    Utilise httpx avec rotation de proxies et User-Agent.
    """
    proxy_pool = ProxyPool()
    found_profiles = []

    platforms = USERNAME_PLATFORMS if depth >= 2 else USERNAME_PLATFORMS[:200]

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(10.0),
        follow_redirects=True,
        verify=False  # Bypass SSL pour certaines plateformes
    ) as client:

        semaphore = asyncio.Semaphore(20)  # Max 20 requêtes simultanées

        async def check_platform(platform: dict) -> Optional[dict]:
            async with semaphore:
                url = platform["url"].format(username=username)
                proxy = await proxy_pool.get_proxy()
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "DNT": "1",
                }

                # Délai aléatoire anti-détection (loi exponentielle)
                await asyncio.sleep(random.expovariate(2))

                try:
                    response = await client.get(url, headers=headers, proxy=proxy)

                    # Détection de présence
                    found = False
                    if platform["error_type"] == "status_code":
                        found = response.status_code != platform["error_code"]
                    elif platform["error_type"] == "message":
                        found = platform["error_msg"] not in response.text

                    if found and response.status_code == 200:
                        return {
                            "platform": platform["name"],
                            "url": url,
                            "status": "FOUND",
                            "status_code": response.status_code,
                        }
                except (httpx.TimeoutException, httpx.ConnectError):
                    return None
                except Exception as e:
                    logger.debug(f"Erreur plateforme {platform['name']}: {e}")
                    return None

        tasks = [check_platform(p) for p in platforms]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        found_profiles = [r for r in results if r is not None]

    logger.info(f"[Username] '{username}' trouvé sur {len(found_profiles)} plateformes")
    return found_profiles


# ============================================================
#  SOUS-MODULE : Holehe — Email ↔ Services
# ============================================================

async def _holehe_check(email: str, depth: int) -> list[dict]:
    """
    Vérifie silencieusement si un email est enregistré sur 100+ services.
    Méthode : exploitation des endpoints de récupération de mot de passe.
    """
    proxy_pool = ProxyPool()
    registered_services = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0), verify=False) as client:
        semaphore = asyncio.Semaphore(10)

        async def check_service(service: dict) -> Optional[dict]:
            async with semaphore:
                proxy = await proxy_pool.get_proxy()
                headers = {"User-Agent": random.choice(USER_AGENTS)}

                await asyncio.sleep(random.uniform(0.5, 2.0))

                try:
                    if service["method"] == "POST":
                        response = await client.post(
                            service["endpoint"],
                            data={service["data_key"]: email},
                            headers=headers,
                            proxy=proxy
                        )
                    else:
                        response = await client.get(
                            service["endpoint"].format(email=email),
                            headers=headers,
                            proxy=proxy
                        )

                    # Analyse de la réponse pour détecter si l'email existe
                    is_registered = _analyze_holehe_response(service, response)

                    if is_registered:
                        return {
                            "service": service["name"],
                            "url": service["url"],
                            "status": "REGISTERED",
                            "confidence": 0.9,
                        }
                except Exception:
                    return None

        tasks = [check_service(s) for s in HOLEHE_SERVICES]
        results = await asyncio.gather(*tasks)
        registered_services = [r for r in results if r is not None]

    logger.info(f"[Holehe] '{email}' enregistré sur {len(registered_services)} services")
    return registered_services


def _analyze_holehe_response(service: dict, response: httpx.Response) -> bool:
    """Analyse la réponse HTTP pour déterminer si l'email est enregistré."""
    # Logique générique — chaque service peut avoir sa propre heuristique
    if response.status_code in (200, 302):
        # Indicateurs négatifs (email non trouvé)
        negative_indicators = [
            "email not found", "no account", "user does not exist",
            "compte inexistant", "adresse introuvable"
        ]
        body_lower = response.text.lower()
        if any(ind in body_lower for ind in negative_indicators):
            return False
        # Indicateurs positifs
        positive_indicators = [
            "reset password", "we sent", "check your email",
            "réinitialiser", "vérifiez votre email"
        ]
        return any(ind in body_lower for ind in positive_indicators)
    return False


# ============================================================
#  INJECTION NEO4J — GraphService
# ============================================================

def _inject_to_graph(
    graph: "GraphService",
    investigation_id: str,
    target: str,
    target_type: str,
    results: dict
) -> None:
    """
    Injecte les entités et relations découvertes dans Neo4j.
    Utilise MERGE pour éviter les doublons.
    """
    # Nœud cible principal
    target_node = graph.upsert_node(
        label=target_type.capitalize(),
        properties={
            "uid": f"{target_type}:{target}",
            "value": encrypt_data(target),  # Chiffré au repos
            "investigation_id": investigation_id,
        }
    )

    # Profils trouvés → nœuds Profile
    for profile in results.get("profiles", []):
        profile_node = graph.upsert_node(
            label="SocialProfile",
            properties={
                "uid": f"profile:{profile['platform']}:{target}",
                "platform": profile["platform"],
                "url": profile["url"],
                "status": profile["status"],
            }
        )
        graph.upsert_relation(
            from_uid=target_node["uid"],
            to_uid=profile_node["uid"],
            relation_type="HAS_PROFILE",
            properties={"source": "identity_module", "confidence": 0.95}
        )

    # Services email → nœuds Service
    for svc in results.get("email_services", []):
        service_node = graph.upsert_node(
            label="OnlineService",
            properties={
                "uid": f"service:{svc['service']}:{target}",
                "service": svc["service"],
                "url": svc["url"],
                "confidence": svc["confidence"],
            }
        )
        graph.upsert_relation(
            from_uid=target_node["uid"],
            to_uid=service_node["uid"],
            relation_type="REGISTERED_ON",
            properties={"source": "holehe_module", "confidence": svc["confidence"]}
        )
