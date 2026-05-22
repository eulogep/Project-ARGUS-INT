# ARGUS-INT : OFFICIAL MIRRORS & CHECKSUMS

Ce fichier liste les seuls miroirs officiels autorisés à distribuer les artefacts ARGUS-INT (ISO, Docker Images).
**Tout autre domaine est considéré comme hostile et potentiellement compromis.**

## Miroirs Officiels

| Type | URL / Registre | Empreinte GPG / Clé Cosign Associée |
|------|---------------|----------------------------------|
| **Git Repo** | `https://github.com/yourorg/argus-int` | `[GPG KEY ID]` |
| **Docker Registry** | `ghcr.io/yourorg/argus-int-*` | `[COSIGN PUBLIC KEY]` |
| **IPFS Gateway** | `ipfs://[CID-HASH]` | `[GPG KEY ID]` |
| **Tor Onion** | `http://argus[...].onion` | `[GPG KEY ID]` |

## Clés Cryptographiques Officielles

### Clé GPG Maître (Release Signing)
```text
Fingerprint: XXXX XXXX XXXX XXXX XXXX  XXXX XXXX XXXX XXXX XXXX
Email: security@argus.local
```

### Clé Cosign (Container Signing)
```text
-----BEGIN PUBLIC KEY-----
[Insérer la clé publique Cosign]
-----END PUBLIC KEY-----
```

> [!CAUTION]
> Si vous téléchargez ARGUS-INT depuis une source absente de cette liste, **NE L'EXÉCUTEZ PAS**. Le risque de backdoor compromettant votre anonymat OSINT est critique.
