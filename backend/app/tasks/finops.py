"""
PHYNX — FinOps Task : Micro-paiement anonyme + accès API premium
backend/app/tasks/finops.py

FLUX COMPLET :
  1. Module OSINT détecte qu'une source requiert un paiement
  2. Celery dispatch → finops.pay_and_fetch()
  3. Sélection automatique XMR ou Lightning selon le montant et la disponibilité
  4. Paiement via Tor → confirmation → appel API premium
  5. Résultats injectés dans Neo4j
  6. Dépense enregistrée dans le dashboard FinOps (chiffrée)

EXEMPLE D'USE-CASE :
  - Achat d'un lookup Dehashed (Lightning, ~50 sats)
  - Achat d'un dump IntelX (XMR, ~0.001 XMR)
  - Achat d'un accès proxy résidentiel 1h (Lightning, ~100 sats)
"""
import logging
import time
import httpx
from typing import Optional, Literal
from celery.utils.log import get_task_logger

from app.celery_app import celery_app
from app.services.monero_rpc import MoneroRPCClient, XMRPaymentResult
from app.services.lightning import LightningClient, LNPaymentResult
from app.services.graph import GraphService
from app.services.encryption import encrypt_data
from app.database import get_db_session_sync
from app.config import settings

logger = get_task_logger(__name__)

PaymentMethod = Literal["xmr", "lightning", "auto"]


# ============================================================
#  TÂCHE CELERY PRINCIPALE : Paiement + Fetch de données
# ============================================================

@celery_app.task(
    bind=True,
    name="app.tasks.finops.pay_and_fetch",
    max_retries=2,
    default_retry_delay=60,
    queue="finops",
    soft_time_limit=180,
    time_limit=300,
)
def pay_and_fetch(
    self,
    investigation_id: str,
    target: str,
    provider: str,            # "dehashed", "intelx", "proxypool_1h", ...
    payment_method: PaymentMethod = "auto",
) -> dict:
    """
    Déclenche un micro-paiement anonyme pour débloquer un accès
    à une source de données premium, puis injecte les résultats.

    Le paiement est sélectionné ainsi :
    - Si Lightning disponible ET montant < seuil → Lightning (rapide, très faible coût)
    - Sinon → Monero XMR (plus anonyme, plus lent, frais plus élevés)
    """
    logger.info(f"[FinOps] Démarrage — provider={provider}, method={payment_method}, target={target}")

    # 1. Récupération de la configuration du provider
    provider_config = _get_provider_config(provider)
    if not provider_config:
        return {"success": False, "error": f"Provider '{provider}' non configuré"}

    # 2. Sélection de la méthode de paiement
    method = _select_payment_method(payment_method, provider_config)
    logger.info(f"[FinOps] Méthode sélectionnée : {method}")

    # 3. Exécution du paiement
    payment_result = _execute_payment(method, provider_config, provider)
    if not payment_result["success"]:
        logger.error(f"[FinOps] Paiement échoué : {payment_result['error']}")
        return payment_result

    # 4. Délai anti-corrélation temporelle (entre paiement et appel API)
    # Empêche la corrélation "paiement → requête immédiate → identité"
    import random
    time.sleep(random.uniform(2.0, 8.0))

    # 5. Appel à l'API premium avec les credentials débloqués
    api_results = _fetch_from_provider(provider_config, target)

    # 6. Enregistrement de la dépense (chiffré)
    _record_expense(
        investigation_id=investigation_id,
        provider=provider,
        method=method,
        amount=provider_config["cost"],
        currency=provider_config["currency"],
        result_count=len(api_results),
    )

    # 7. Injection dans Neo4j
    if api_results:
        graph = GraphService()
        _inject_breach_results(graph, investigation_id, target, api_results, provider)

    return {
        "success": True,
        "provider": provider,
        "method": method,
        "results_count": len(api_results),
        "payment": {
            "amount": provider_config["cost"],
            "currency": provider_config["currency"],
        },
    }


# ============================================================
#  CONFIGURATION DES PROVIDERS
# ============================================================

def _get_provider_config(provider: str) -> Optional[dict]:
    """
    Retourne la configuration d'un provider premium.
    En production : chargé depuis un fichier YAML chiffré ou la DB.
    """
    PROVIDER_CONFIGS = {
        "dehashed": {
            "name": "Dehashed",
            "description": "Base de données de leaks (9B+ entrées)",
            "api_base": "https://api.dehashed.com",
            "api_endpoint": "/search",
            "auth_type": "basic",           # basic auth débloquée après paiement
            "cost": 500,                    # 500 sats Lightning
            "currency": "sats",
            "payment_method": "lightning",
            "invoice_endpoint": None,       # Invoice BOLT11 pré-générée en config
            "invoice": settings.DEHASHED_LN_INVOICE,
            "xmr_address": None,
        },
        "intelx": {
            "name": "Intelligence X",
            "description": "Moteur OSINT Deep/Dark Web",
            "api_base": "https://2.intelx.io",
            "api_endpoint": "/intelligent/search",
            "auth_type": "api_key",
            "cost": 0.0005,                 # 0.0005 XMR
            "currency": "xmr",
            "payment_method": "xmr",
            "xmr_address": settings.INTELX_XMR_ADDRESS,
            "invoice": None,
        },
        "proxypool_1h": {
            "name": "Proxy Pool Premium (1h)",
            "description": "Proxies résidentiels rotatifs, 1h d'accès",
            "api_base": settings.PROXY_PROVIDER_API,
            "api_endpoint": "/activate",
            "auth_type": "token",
            "cost": 100,
            "currency": "sats",
            "payment_method": "lightning",
            "invoice": settings.PROXY_PROVIDER_LN_INVOICE,
            "xmr_address": None,
        },
    }
    return PROVIDER_CONFIGS.get(provider)


# ============================================================
#  SÉLECTION DE LA MÉTHODE DE PAIEMENT
# ============================================================

def _select_payment_method(requested: PaymentMethod, config: dict) -> str:
    """
    Logique de sélection automatique :
    - "auto" → préfère Lightning si montant < 1000 sats et channel disponible
    - Sinon → XMR (plus anonyme)
    """
    if requested != "auto":
        return requested

    # Vérifier la disponibilité Lightning
    if config["currency"] == "sats":
        try:
            ln = LightningClient()
            balance = ln.get_balance()
            ln.close()
            if balance["local_balance_sats"] >= config["cost"] + 100:  # +100 sats frais
                return "lightning"
        except Exception as e:
            logger.warning(f"[FinOps] Lightning indisponible : {e}")

    # Vérifier la disponibilité XMR
    try:
        xmr = MoneroRPCClient()
        balance = xmr.get_balance()
        xmr.close()
        if balance["unlocked_xmr"] >= config.get("cost", 0):
            return "xmr"
    except Exception as e:
        logger.warning(f"[FinOps] Monero indisponible : {e}")

    return "unavailable"


# ============================================================
#  EXÉCUTION DU PAIEMENT
# ============================================================

def _execute_payment(method: str, config: dict, label: str) -> dict:
    """Route le paiement vers Lightning ou Monero."""
    if method == "unavailable":
        return {"success": False, "error": "Aucun wallet disponible"}

    if method == "lightning":
        return _pay_lightning(config, label)
    elif method == "xmr":
        return _pay_monero(config, label)

    return {"success": False, "error": f"Méthode inconnue : {method}"}


def _pay_lightning(config: dict, label: str) -> dict:
    """Paie une invoice Lightning BOLT11."""
    invoice = config.get("invoice")
    if not invoice:
        return {"success": False, "error": "Invoice Lightning non configurée"}

    try:
        ln = LightningClient()
        result: LNPaymentResult = ln.pay_invoice(
            payment_request=invoice,
            max_fee_sats=min(50, config["cost"] // 10),  # Frais max = 10% du montant
            label=label,
        )
        ln.close()

        if result.success:
            return {"success": True, "method": "lightning", "fee_sats": result.fee_sats}
        return {"success": False, "error": result.error}

    except Exception as e:
        return {"success": False, "error": str(e)}


def _pay_monero(config: dict, label: str) -> dict:
    """Envoie un paiement XMR à l'adresse du provider."""
    xmr_address = config.get("xmr_address")
    if not xmr_address:
        return {"success": False, "error": "Adresse XMR du provider non configurée"}

    try:
        xmr = MoneroRPCClient()
        result: XMRPaymentResult = xmr.send_payment(
            destination=xmr_address,
            amount_xmr=config["cost"],
            payment_label=label,
        )
        xmr.close()

        if result.success:
            # Attente de confirmation (au moins 1 bloc Monero ≈ 2 min)
            logger.info(f"[FinOps] XMR envoyé — attente confirmation bloc...")
            time.sleep(settings.XMR_CONFIRMATION_WAIT_SECONDS)  # 120s par défaut
            return {"success": True, "method": "xmr", "fee_xmr": result.fee_xmr}
        return {"success": False, "error": result.error}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
#  APPEL À L'API PREMIUM POST-PAIEMENT
# ============================================================

def _fetch_from_provider(config: dict, target: str) -> list[dict]:
    """
    Appelle l'API premium pour récupérer les données sur la cible.
    Toutes les requêtes passent par Tor.
    """
    provider_name = config["name"]

    transport = httpx.HTTPTransport(proxy=settings.TOR_PROXY)
    headers = {"User-Agent": "PHYNX/1.0"}

    if config["auth_type"] == "api_key":
        headers["X-Key"] = settings.INTELX_API_KEY

    try:
        with httpx.Client(transport=transport, timeout=30.0, verify=False) as client:
            params = {"query": target, "limit": 100}

            response = client.get(
                f"{config['api_base']}{config['api_endpoint']}",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            results = _normalize_provider_results(provider_name, data)
            logger.info(f"[FinOps] {provider_name} → {len(results)} résultats pour '{target}'")
            return results

    except Exception as e:
        logger.error(f"[FinOps] Erreur fetch {provider_name} : {e}")
        return []


def _normalize_provider_results(provider: str, raw: dict) -> list[dict]:
    """Normalise les résultats bruts selon le provider."""
    if provider == "Dehashed":
        entries = raw.get("entries") or []
        return [
            {
                "email": e.get("email", ""),
                "username": e.get("username", ""),
                "password": e.get("password", ""),
                "hashed_password": e.get("hashed_password", ""),
                "ip_address": e.get("ip_address", ""),
                "database_name": e.get("database_name", ""),
                "source": "dehashed",
            }
            for e in entries
        ]
    elif provider == "Intelligence X":
        records = raw.get("records") or []
        return [
            {
                "systemid": r.get("systemid", ""),
                "date": r.get("date", ""),
                "name": r.get("name", ""),
                "bucket": r.get("bucket", ""),
                "source": "intelx",
            }
            for r in records
        ]
    return []


# ============================================================
#  INJECTION NEO4J — DONNÉES DE BREACH
# ============================================================

def _inject_breach_results(
    graph: GraphService,
    investigation_id: str,
    target: str,
    results: list[dict],
    provider: str,
) -> None:
    """Injecte les credentials/leaks dans le graphe comme nœuds BreachRecord."""
    target_uid = f"email:{target}" if "@" in target else f"username:{target}"

    for record in results:
        import hashlib
        record_uid = hashlib.sha256(
            f"{provider}:{record.get('email','')}:{record.get('password','')}".encode()
        ).hexdigest()[:24]

        node = graph.upsert_node(
            label="BreachRecord",
            properties={
                "uid": f"breach:{record_uid}",
                "source": provider,
                "database_name": record.get("database_name", ""),
                "has_plaintext_password": bool(record.get("password")),
                "has_hashed_password": bool(record.get("hashed_password")),
                "ip_address": record.get("ip_address", ""),
                "investigation_id": investigation_id,
                # JAMAIS le mot de passe en clair dans Neo4j → chiffré
                "email_enc": encrypt_data(record.get("email", "")) if record.get("email") else "",
                "password_enc": encrypt_data(record.get("password", "")) if record.get("password") else "",
            }
        )
        graph.upsert_relation(
            from_uid=target_uid,
            to_uid=node["uid"],
            relation_type="FOUND_IN_BREACH",
            properties={"source": provider, "confidence": 0.99}
        )


# ============================================================
#  ENREGISTREMENT DE LA DÉPENSE (Dashboard FinOps)
# ============================================================

def _record_expense(
    investigation_id: str,
    provider: str,
    method: str,
    amount: float,
    currency: str,
    result_count: int,
) -> None:
    """
    Enregistre la dépense dans PostgreSQL (table finops_expenses).
    Toutes les valeurs sensibles sont chiffrées.
    Sert au dashboard FinOps pour le suivi des coûts.
    """
    try:
        with get_db_session_sync() as db:
            db.execute(
                """INSERT INTO finops_expenses
                   (investigation_id, provider, method, amount, currency, result_count, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6, NOW())""",
                investigation_id, provider, method,
                float(amount), currency, result_count
            )
    except Exception as e:
        logger.warning(f"[FinOps] Impossible d'enregistrer la dépense : {e}")
