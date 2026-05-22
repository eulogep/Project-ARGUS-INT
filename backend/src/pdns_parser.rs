// PHYNX — High-Velocity Network & pDNS Stream Parser
// backend/src/pdns_parser.rs
//
// Moteur de parsing haute performance en Rust.
// Traite les trames Ethernet/IP/UDP brutes en streaming via pcap,
// extrait les enregistrements pDNS et sérialise en JSON à haute vélocité.

use pcap::{Capture, Device};
use serde::{Serialize, Deserialize};
use std::net::IpAddr;
use std::time::Instant;

#[derive(Serialize, Deserialize, Debug)]
pub struct DnsRecord {
    pub timestamp_ms: u64,
    pub source_ip: String,
    pub query_domain: String,
    pub record_type: String,
    pub resolved_ips: Vec<String>,
}

pub struct PacketEngine {
    interface_name: String,
}

impl PacketEngine {
    pub fn new(interface_name: &str) -> Self {
        Self {
            interface_name: interface_name.to_string(),
        }
    }

    /// Démarre le traitement en continu du flux réseau de l'interface
    pub fn run_capture(&self) -> Result<(), Box<dyn std::error::Error>> {
        let device = Device::list()?
            .into_iter()
            .find(|d| d.name == self.interface_name)
            .ok_or("Interface réseau introuvable")?;

        let mut cap = Capture::from_device(device)?
            .promisc(true)
            .snaplen(65535)
            .timeout(10)
            .open()?;

        // Appliquer un filtre BPF (Berkeley Packet Filter) pour ne capturer que le trafic DNS (port 53)
        cap.filter("udp port 53", true)?;

        let start_time = Instant::now();
        let mut packet_count = 0;

        println!("[Rust PacketEngine] Capture démarrée sur {}", self.interface_name);

        while let Ok(packet) = cap.next_packet() {
            packet_count += 1;
            
            if let Some(dns_record) = self.parse_dns_payload(&packet.data) {
                // En production, sérialiser en JSON et envoyer vers un socket Unix ou Kafka
                if let Ok(json_data) = serde_json::to_string(&dns_record) {
                    // Simule le flux de sortie vers la diode de données logicielle
                    // println!("{}", json_data);
                }
            }

            if packet_count % 100000 == 0 {
                let duration = start_time.elapsed().as_secs_f64();
                println!(
                    "[Rust PacketEngine] Mpps moyen: {:.2}",
                    (packet_count as f64) / duration / 1_000_000.0
                );
            }
        }

        Ok(())
    }

    /// Parse la structure binaire de la trame Ethernet -> IP -> UDP -> DNS
    fn parse_dns_payload(&self, data: &[u8]) -> Option<DnsRecord> {
        // En-tête Ethernet : 14 octets
        if data.len() < 14 + 20 + 8 + 12 {
            return None;
        }

        // Identifier IPv4 (0x0800) ou IPv6 (0x86DD) dans le type Ethernet
        let eth_type = u16::from_be_bytes([data[12], data[13]]);
        let ip_header_offset = 14;

        let (src_ip, dns_offset) = match eth_type {
            0x0800 => { // IPv4
                let ip_header_len = (data[ip_header_offset] & 0x0F) as usize * 4;
                let src_ip_bytes = [
                    data[ip_header_offset + 12],
                    data[ip_header_offset + 13],
                    data[ip_header_offset + 14],
                    data[ip_header_offset + 15],
                ];
                let src_ip = IpAddr::V4(src_ip_bytes.into()).to_string();
                let udp_offset = ip_header_offset + ip_header_len;
                (src_ip, udp_offset + 8) // Sauter les 8 octets du header UDP
            },
            _ => return None, // Ignorer les autres protocoles pour ce parser ultra-rapide
        };

        if data.len() <= dns_offset {
            return None;
        }

        let dns_payload = &data[dns_offset..];
        
        // Parsing simplifié de la requête DNS (QNAME)
        // Les 12 premiers octets correspondent au header DNS
        let qd_count = u16::from_be_bytes([dns_payload[4], dns_payload[5]]);
        if qd_count == 0 {
            return None;
        }

        let mut domain = String::new();
        let mut idx = 12; // Début de la section Question
        
        // Lire le format DNS Label (3www3domain3com0)
        while idx < dns_payload.len() {
            let label_len = dns_payload[idx] as usize;
            if label_len == 0 {
                break;
            }
            if idx + 1 + label_len > dns_payload.len() {
                return None;
            }
            if !domain.is_empty() {
                domain.push('.');
            }
            let label = std::str::from_utf8(&dns_payload[idx + 1..idx + 1 + label_len]).ok()?;
            domain.push_str(label);
            idx += 1 + label_len;
        }

        Some(DnsRecord {
            timestamp_ms: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .ok()?
                .as_millis() as u64,
            source_ip: src_ip,
            query_domain: domain,
            record_type: "A".to_string(), // Par défaut pour ce prototype
            resolved_ips: vec![],
        })
    }
}
