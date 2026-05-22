# PHYNX — Architecture FinOps & Crypto-Tracking

## Isolation du Module Financier — Garanties de Sécurité

### Principe fondamental : Séparation des domaines

```
┌─────────────────────────────────────────────────────────────────┐
│              ZONE OSINT (données collectées)                    │
│  [Identity] [Breach] [DarkWeb] [GEOINT] [TechRecon]            │
└────────────────────────┬────────────────────────────────────────┘
                         │  Celery task.s() — pas d'accès direct
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              ZONE FINOPS (paiements anonymes)                   │
│                                                                 │
│  [FinOps Worker] ←─ queue Redis "finops" ─→ 1 seul worker      │
│       │                                      (séquentiel)      │
│       ├──► [Monero RPC Client] ─── Tor ──► [monero-wallet-rpc] │
│       └──► [Lightning Client]  ─── Tor ──► [LND REST :8080]    │
│                                                                 │
│  ISOLATION :                                                    │
│  - Réseau Docker séparé (tor-net)                               │
│  - Zéro variable d'env partagée avec la zone OSINT             │
│  - Concurrence worker = 1 (une tx à la fois)                   │
│  - Clés privées jamais en mémoire Celery                       │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              ZONE CLÉS (wallets chiffrés)                       │
│                                                                 │
│  [monero-wallet-rpc] → volume monero_wallets (bind mount LUKS) │
│  [LND]               → volume lnd_data (bind mount LUKS)       │
│                                                                 │
│  GARANTIES :                                                    │
│  - Clés privées JAMAIS dans les variables d'environnement      │
│  - JAMAIS dans PostgreSQL ni Neo4j                              │
│  - JAMAIS loguées (même chiffrées)                             │
│  - wallet-rpc déchiffre à la demande → RPC local uniquement    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flux : Paiement XMR pour débloquer un accès API

```
[Module Breach] détecte que IntelX requiert un paiement XMR
    │
    │  celery_app.send_task("app.tasks.finops.pay_and_fetch",
    │      args=[investigation_id, target, "intelx", "xmr"])
    ▼
Redis Queue "finops"
    │
    ▼
[FinOps Worker] (seul worker sur cette queue)
    │
    ├─[1] Vérification solde XMR (via monero-wallet-rpc local)
    │      MoneroRPCClient._call("get_balance")
    │
    ├─[2] Sélection de méthode : XMR > Lightning selon disponibilité
    │
    ├─[3] Paiement
    │      MoneroRPCClient.send_payment(
    │          destination=INTELX_XMR_ADDRESS,
    │          amount_xmr=0.0005,
    │          ring_size=17    ← mixin=16
    │      )
    │      → Transaction broadcastée via Tor (tx-proxy dans monerod)
    │
    ├─[4] Délai anti-corrélation : sleep(random.uniform(2, 8))
    │      ← Empêche la corrélation temporelle paiement → requête API
    │
    ├─[5] Appel API IntelX via Tor
    │      httpx.Client(transport=HTTPTransport(proxy=TOR_PROXY))
    │
    ├─[6] Normalisation + chiffrement des résultats sensibles
    │
    ├─[7] Injection Neo4j (BreachRecord nodes)
    │
    └─[8] Enregistrement dépense PostgreSQL (montant + provider, tx_hash chiffré)
```

---

## Flux : Paiement Lightning pour proxies résidentiels (1h)

```
[ProxyPool] health-check → pool épuisé → demande recharge
    │
    │  pay_and_fetch.delay("inv_id", "", "proxypool_1h", "lightning")
    ▼
[FinOps Worker]
    │
    ├─[1] Vérification solde LND (local_balance_sats)
    │
    ├─[2] LightningClient.pay_invoice(
    │          payment_request=PROXY_PROVIDER_LN_INVOICE,
    │          max_fee_sats=10  ← frais max 10 sats
    │      )
    │      → Invoice payée en <1 seconde (Lightning)
    │      → Preuve de paiement (preimage) stockée chiffrée
    │
    ├─[3] Délai 2-8 secondes
    │
    └─[4] Appel API provider → tokens proxies récupérés → ProxyPool.reload()
```

---

## Anonymisation des Transactions Sortantes

### Monero (XMR) — Garanties natives

| Propriété | Mécanisme |
|---|---|
| Montant chiffré | RingCT (Confidential Transactions) |
| Émetteur masqué | Ring Signature (16 decoys) |
| Destinataire masqué | Stealth Addresses (subaddress) |
| IP source masquée | `--tx-proxy=tor,tor:9050` dans monerod |
| Pas de blockchain analysis | Impossible sans compromission du ring |

### Lightning Network — Garanties

| Propriété | Mécanisme |
|---|---|
| Montant opaque | HTLCs routés via canaux intermédiaires |
| IP source masquée | LND routé via Tor (onion service) |
| Pas de trace on-chain | Seulement les channels opening/closing |
| Vitesse | <1 seconde — pas de corrélation temporelle |

### Anti-corrélation Réseau

```python
# Séquence temporelle dans finops.py :
payment_result = _execute_payment(method, config, label)
# ↑ Paiement terminé

time.sleep(random.uniform(2.0, 8.0))   # Délai aléatoire !
# ↑ Coupure temporelle — un observateur réseau ne peut pas
#   corréler le paiement avec l'appel API suivant

api_results = _fetch_from_provider(config, target)
# ↑ Appel API via Tor (IP différente du paiement)
```

---

## Gestion des Clés Privées — Modèle de Menace

### Ce qui est protégé

```
┌────────────────────────────────────────────────────────┐
│  JAMAIS exposé :                                       │
│  ✗ Seed phrase / mnemonic Monero                       │
│  ✗ spend_key Monero                                    │
│  ✗ Private key Bitcoin/Lightning                       │
│  ✗ LND seed                                            │
│                                                        │
│  Réside uniquement dans :                              │
│  → Volume bind-mount LUKS chiffré (./data/monero_wallets)│
│  → Volume bind-mount LUKS chiffré (./data/lnd)         │
│  → Déchiffré en RAM par wallet-rpc/lnd UNIQUEMENT      │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  Stocké chiffré (AES-256-GCM) :                        │
│  ✓ tx_hash des transactions (PostgreSQL)               │
│  ✓ preimage Lightning (PostgreSQL)                     │
│  ✓ Adresses publiques des wallets opérationnels        │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  Stocké en clair (non sensible) :                      │
│  ✓ Montants des dépenses (pour le dashboard)           │
│  ✓ Nom des providers                                   │
│  ✓ Méthode de paiement utilisée                        │
└────────────────────────────────────────────────────────┘
```

### Production : Volume LUKS

```bash
# Créer un volume chiffré LUKS pour les wallets
sudo cryptsetup luksFormat /dev/sdX1
sudo cryptsetup open /dev/sdX1 phynx-wallets
sudo mkfs.ext4 /dev/mapper/phynx-wallets
sudo mount /dev/mapper/phynx-wallets /home/phynx/data/monero_wallets
```

---

## Fichiers créés (édition FinOps)

| Fichier | Description |
|---|---|
| `backend/app/services/monero_rpc.py` | Client Monero RPC via Tor |
| `backend/app/services/lightning.py` | Client LND Lightning via Tor |
| `backend/app/tasks/finops.py` | Tâche Celery : paiement → fetch → inject |
| `backend/app/tasks/crypto_trace.py` | CryptoTrace : BTC/ETH/XMR |
| `db/migrations/002_finops.sql` | Tables PostgreSQL FinOps |
| `docker-compose.yml` | +monerod, monero-wallet-rpc, bitcoind, lnd |
| `.env.example` | +variables FinOps |
