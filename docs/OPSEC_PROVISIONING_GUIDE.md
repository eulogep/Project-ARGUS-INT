# OPSEC Provisioning & Anonymity Guide

This guide outlines operational security (OPSEC) strategies for acquiring resources, obtaining external API credentials, and running nodes anonymously when executing OSINT investigations.

---

## 1. Anonymous Acquisition of Network Infrastructure & Proxies

To prevent network calls from revealing the operator's home IP, all outgoing traffic must route through SOCKS5 proxies, residential proxy pools, or Tor circuits. 

### Sourcing Residential and Mobile Proxies Without KYC
Most mainstream proxy services (e.g., Oxylabs, Bright Data) require credit card payments and strict Identity Verification (KYC). For stealth operations, operators should utilize providers that support:
*   No personal details required for registration (temporary/anonymous email only).
*   Direct Monero (XMR) or Bitcoin Lightning network payments.
*   Tor-accessible admin panels (.onion domains).

#### Recommended Provider Categories:
1.  **Non-KYC Crypto-Native Proxy Services**: Providers like *ProxyRack* or specific darknet-adjacent services (accessible via Tor directory aggregators) sell residential proxy bandwidth paid in XMR.
2.  **Self-Hosted Mobile Proxies**: 
    *   Deploy low-cost Android phones running routing software (e.g., Proxy Server apps) on cellular networks.
    *   Purchase prepaid SIM cards using cash at physical retail outlets.
    *   Rotate the cellular IP by sending automated AT commands or ADB scripts to toggle Airplane Mode.

---

## 2. Acquiring Threat Intelligence API Keys Anonymously

When active scrapers cannot extract data directly, PHYNX relies on APIs (e.g., Dehashed, Intelligence X, Shodan, Censys). 

### Strategy for Sock Puppets (Fictitious Identities)
1.  **Operational Environment**: Never register for API keys from your personal browser. Always launch an isolated virtual machine (e.g., Whonix workstation) or use a secure browser profile (e.g., LibreWolf over Tor).
2.  **Email Addresses**: Use privacy-focused, non-KYC email providers (e.g., ProtonMail, Tuta, or Elude) registered over Tor. Do not link a recovery email or phone number.
3.  **Virtual Phone Numbers (SMS Bypass)**: If a service requires SMS verification during signup, use non-virtual SMS reception services that accept Monero. Avoid public free SMS services, as their numbers are often blacklisted.
4.  **Payments**: Generate subaddresses on the Monero network for any purchases. For credit-card-only platforms, use virtual prepaid credit cards (VCC) obtained from platforms that allow funding via cryptocurrency without KYC verification (e.g., generic crypto-to-gift-card or crypto VCC platforms).

---

## 3. Node Configuration & Wallet Security

### Monero Daemon & Wallet RPC Configuration
By default, the `phynx-monerod` service is configured to prune the blockchain to save disk space and routes transactions through Tor proxy interfaces.

*   **Database Directory**: Mount the wallet data folder `./data/monero_wallets` on an encrypted LUKS partition.
*   **Daemon RPC**: Ensure the wallet RPC container (`phynx-monero-wallet-rpc`) is only accessible within the internal bridge network (`phynx-net`). Never expose port `18082` to the public host interface.

### LND Lightning Network Security
*   **Macaroons**: Use only `invoice.macaroon` for the `worker-finops` container. This macaroon only allows creating and paying invoices, preventing the container from performing administration or channel closing operations.
*   **Network Access**: Ensure `lnd` communications with the external peer network route exclusively through Tor to prevent exposing the node's physical IP address.
