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
ARGUS-INT — Module Dark Web : Tâche Celery + Tor Scraper
backend/app/tasks/darkweb.py

Scraping de sites .onion via Tor avec rotation de circuits.
"""

import asyncio
import random
import time
import httpx
import logging
from typing import Optional
import socket
import socks  # PySocks

from app.celery_app import celery_app
from app.services.graph import GraphService
from app.config import settings

logger = logging.getLogger(__name__)

# ─── Configuration Tor ──────────────────────────────────────────────────
TOR_PROXY = settings.TOR_PROXY  # socks5h://tor:9050
TOR_CONTROL_HOST = "tor"
TOR_CONTROL_PORT = 9051
TOR_CONTROL_PASSWORD = settings.TOR_CONTROL_PASSWORD

# Délai minimum entre renouvellement de circuit (secondes)
CIRCUIT_RENEWAL_DELAY = 10


# ============================================================
#  ROTATION DE CIRCUIT TOR
# ============================================================

def renew_tor_circuit():
    """
    Demande un nouveau circuit Tor via le ControlPort.
    Équivalent de : echo 'SIGNAL NEWNYM' | nc tor 9051
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((TOR_CONTROL_HOST, TOR_CONTROL_PORT))
        s.send(f"AUTHENTICATE \"{TOR_CONTROL_PASSWORD}\"\r\n".encode())
        time.sleep(0.5)
        s.send(b"SIGNAL NEWNYM\r\n")
        time.sleep(CIRCUIT_RENEWAL_DELAY)  # Attendre le nouveau circuit
        s.close()
        logger.info("[Tor] Nouveau circuit demandé (NEWNYM)")
    except Exception as e:
        logger.warning(f"[Tor] Impossible de renouveler le circuit : {e}")


# ============================================================
#  TÂCHE CELERY DARK WEB
# ============================================================

@celery_app.task(
    bind=True,
    name="app.tasks.darkweb.run_darkweb_search",
    max_retries=2,
    default_retry_delay=60,
    queue="darkweb",
    soft_time_limit=240,
    time_limit=480,
)
def run_darkweb_search(
    self,
    investigation_id: str,
    target: str,
    depth: int = 2
) -> dict:
    """
    Recherche une cible sur le Dark Web (forums .onion, Telegram, IRC).
    Chaque tâche utilise un circuit Tor isolé.
    """
    logger.info(f"[DarkWeb] Démarrage — target={target}, depth={depth}")

    # Nouveau circuit pour cette tâche
    renew_tor_circuit()

    results = {"mentions": [], "forums": [], "channels": [], "raw_count": 0}

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Recherche sur les moteurs .onion indexés
        results["mentions"] = loop.run_until_complete(
            _search_onion_search_engines(target, depth)
        )

        # Scan des forums connus si profondeur suffisante
        if depth >= 3:
            results["forums"] = loop.run_until_complete(
                _scan_known_forums(target)
            )

        results["raw_count"] = sum(len(v) for v in results.values() if isinstance(v, list))

        # Injection Neo4j
        graph = GraphService()
        _inject_darkweb_to_graph(graph, investigation_id, target, results)

        return results

    except Exception as exc:
        logger.error(f"[DarkWeb] Erreur : {exc}", exc_info=True)
        raise self.retry(exc=exc)
    finally:
        try:
            loop.close()
        except Exception:
            pass


# ============================================================
#  MOTEURS DE RECHERCHE .ONION
# ============================================================

ONION_SEARCH_ENGINES = [
    {
        "name": "Ahmia",
        "url": "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/search/?q={query}",
        "result_selector": ".result"
    },
    {
        "name": "Torch",
        "url": "http://xmh57jrknzkhv6y3ls3ubitzfqnkrwxhopf5aygthi7d6rplyvk3noyd.onion/4a1f6b371c/search.cgi?cmd=Search&pg=1&stype=phrase&q={query}",
        "result_selector": "dl dt a"
    },
    {
        "name": "DarkSearch",
        "url": "http://darksearch7cs42qaqb3o6vflz7usdolezm7oo37fdghsrxcnihwqsyd.onion/api/search?query={query}",
        "is_api": True
    },
]


async def _search_onion_search_engines(target: str, depth: int) -> list[dict]:
    """Requête les moteurs de recherche .onion via Tor."""
    mentions = []

    transport = httpx.AsyncHTTPTransport(proxy=TOR_PROXY)

    async with httpx.AsyncClient(
        transport=transport,
        timeout=httpx.Timeout(60.0),  # Tor est lent
        follow_redirects=True,
        verify=False,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/109.0",
        }
    ) as client:
        for engine in ONION_SEARCH_ENGINES:
            try:
                url = engine["url"].format(query=target)
                await asyncio.sleep(random.uniform(2, 5))  # Délai plus long sur Tor

                response = await client.get(url)

                if engine.get("is_api"):
                    data = response.json()
                    for item in data.get("results", [])[:10]:
                        mentions.append({
                            "source": engine["name"],
                            "url": item.get("link", ""),
                            "title": item.get("title", ""),
                            "snippet": item.get("description", ""),
                            "network": "tor",
                        })
                else:
                    # Parsing HTML basique (BeautifulSoup en prod)
                    # Simplifié ici pour l'exemple
                    if target.lower() in response.text.lower():
                        mentions.append({
                            "source": engine["name"],
                            "url": url,
                            "network": "tor",
                            "match": True,
                        })

            except Exception as e:
                logger.debug(f"[DarkWeb] Erreur moteur {engine['name']}: {e}")
                renew_tor_circuit()  # Renouveler si échec

    return mentions


async def _scan_known_forums(target: str) -> list[dict]:
    """Scan des forums .onion connus (liste maintenue manuellement + via IA)."""
    # Liste partielle — en production, chargée depuis un fichier YAML
    known_forums = [
        "http://facebookwkhpilnemxj7asber7cybptq7cq7xj4dvfss34oq2q7rfid.onion",
        # ... autres forums indexés
    ]
    found = []
    # Implémentation similaire à _search_onion_search_engines
    return found


# ============================================================
#  INJECTION NEO4J
# ============================================================

def _inject_darkweb_to_graph(
    graph: GraphService,
    investigation_id: str,
    target: str,
    results: dict
) -> None:
    """Injecte les mentions Dark Web comme nœuds DarkWebMention."""
    target_uid = f"unknown:{target}"

    for mention in results.get("mentions", []):
        node = graph.upsert_node(
            label="DarkWebMention",
            properties={
                "uid": f"dwm:{mention['source']}:{target}:{hash(mention.get('url', ''))}",
                "source_engine": mention["source"],
                "url": mention.get("url", ""),
                "title": mention.get("title", ""),
                "network": mention.get("network", "tor"),
                "investigation_id": investigation_id,
            }
        )
        graph.upsert_relation(
            from_uid=target_uid,
            to_uid=node["uid"],
            relation_type="MENTIONED_ON",
            properties={"source": "darkweb_module", "confidence": 0.7}
        )
