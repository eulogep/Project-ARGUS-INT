// ==============================================================================
// Project ARGUS-INT - Multi-Spectrum Intelligence Fusion Platform
// ==============================================================================
// Copyright (C) 2026 eulogep
//
// This file is part of Project ARGUS-INT.
//
// Project ARGUS-INT is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Project ARGUS-INT is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with Project ARGUS-INT. If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later
// ==============================================================================

// ARGUS-INT — Platform OPSEC, Anti-Tampering & Defensive Subsystem
// backend/src/anti_tampering.rs
//
// Détection d'environnements hostiles, anti-debugging et Dead Man's Switch.

use std::fs;
use std::process;
use std::time::Instant;
use std::arch::x86_64::__rdtsc;

/// Détecte si le processus courant fait l'objet d'un traçage / debugging via ptrace.
/// Sur Linux, un processus ne peut être tracé que par un seul parent à la fois.
/// Tenter ptrace(PTRACE_TRACEME) renverra une erreur si un debugger est déjà attaché.
pub fn is_debugger_present() -> bool {
    #[cfg(target_os = "linux")]
    {
        use libc::{ptrace, PTRACE_TRACEME};
        unsafe {
            if ptrace(PTRACE_TRACEME, 0, std::ptr::null_mut::<libc::c_void>(), std::ptr::null_mut::<libc::c_void>()) < 0 {
                return true;
            }
        }
    }
    false
}

/// Détecte les anomalies de timing à l'aide de l'instruction RDTSC (Read Time-Step Counter).
/// Si un debugger exécute le binaire pas-à-pas, l'écart de ticks CPU sera anormalement élevé.
pub fn check_timing_anomaly() -> bool {
    unsafe {
        let t1 = __rdtsc();
        // Petite opération neutre pour forcer un délai minimal
        let mut _x = 0;
        for i in 0..50 {
            _x ^= i;
        }
        let t2 = __rdtsc();
        // Si l'écart dépasse un seuil réaliste de ticks (ex: 20000 ticks pour 50 XORs),
        // cela suggère un arrêt pas-à-pas ou une instrumentation dynamique.
        if (t2 - t1) > 20000 {
            return true;
        }
    }
    false
}

/// Détecte la présence d'un hyperviseur ou d'une sandbox forensique classique
/// en vérifiant l'instruction CPUID et la présence d'artefacts système de fichiers typiques.
pub fn is_sandbox_detected() -> bool {
    // 1. Vérification de l'instruction CPUID (hypervisor present bit)
    #[cfg(target_arch = "x86_64")]
    {
        use std::arch::x86_64::__cpuid;
        unsafe {
            let cpuid = __cpuid(1);
            // Le bit 31 de ECX indique si nous tournons sur un hyperviseur.
            if (cpuid.ecx & (1 << 31)) != 0 {
                return true;
            }
        }
    }

    // 2. Vérification des fichiers d'artefacts système virtuels (VMware, VirtualBox, KVM)
    let vm_artifacts = [
        "/sys/class/dmi/id/product_name",
        "/sys/class/dmi/id/sys_vendor",
    ];

    for path in &vm_artifacts {
        if let Ok(content) = fs::read_to_string(path) {
            let content_lower = content.to_lowercase();
            if content_lower.contains("vmware") 
                || content_lower.contains("virtualbox") 
                || content_lower.contains("qemu") 
                || content_lower.contains("xen") 
                || content_lower.contains("kvm") 
            {
                return true;
            }
        }
    }
    false
}

/// Déclenche l'autodestruction cryptographique sécurisée immédiate.
/// Remplace par des zéros les clés privées critiques et supprime les bases locales
/// avant d'arrêter brutalement le processus.
pub fn trigger_dead_mans_switch(reason: &str) {
    eprintln!("[!] CRITICAL OPSEC VOID DETECTED: {}", reason);
    eprintln!("[!] initiating secure cryptographic shredding...");

    // 1. Purge et écrasement des fichiers de configuration sensibles si présents
    let sensitive_files = [
        "config.json",
        ".env",
        "keys/private_key.pem",
    ];

    for file in &sensitive_files {
        if fs::metadata(file).is_ok() {
            if let Ok(metadata) = fs::metadata(file) {
                let size = metadata.len() as usize;
                // Écrasement par des patterns de zéros (Zeroing memory/disk footprint)
                let zeroes = vec![0u8; size];
                let _ = fs::write(file, zeroes);
                let _ = fs::remove_file(file);
            }
        }
    }

    // 2. Arrêt forcé immédiat du processus (sans laisser aux destructeurs l'opportunité de flusher)
    process::exit(137);
}

/// Exécute l'ensemble des vérifications de sécurité active.
/// Si un environnement hostile est détecté, le processus est détruit immédiatement.
pub fn run_security_checks() {
    // Si la variable d'échappement OPSEC est présente, on ignore les vérifications pour le dev/CI
    if std::env::var("ARGUS_ALLOW_SANDBOX").is_ok() {
        return;
    }

    if is_debugger_present() {
        trigger_dead_mans_switch("ACTIVE_DEBUGGER_ATTACHED");
    }

    if check_timing_anomaly() {
        trigger_dead_mans_switch("TIMING_ANOMALY_DETECTED");
    }

    if is_sandbox_detected() {
        trigger_dead_mans_switch("UNAUTHORIZED_SANDBOX_ENVIRONMENT");
    }
}
