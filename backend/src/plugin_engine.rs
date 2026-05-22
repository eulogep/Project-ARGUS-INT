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

// ARGUS-INT — WebAssembly Sandbox Plugin Engine
// backend/src/plugin_engine.rs
//
// Charge, isole et exécute des plugins tiers compilés en Wasm.

use wasmtime::*;
use wasmtime_wasi::sync::WasiCtxBuilder;
use wasmtime_wasi::WasiCtx;
use std::path::Path;

pub struct PluginStore {
    pub wasi: WasiCtx,
}

pub struct PluginEngine {
    engine: Engine,
}

impl PluginEngine {
    pub fn new() -> Self {
        // Configuration de l'Engine Wasmtime
        let mut config = Config::new();
        // Activer la compilation à la volée (JIT) et les vérifications de débordement mémoire
        config.cranelift_opt_level(OptLevel::SpeedAndSize);
        let engine = Engine::new(&config).expect("Échec d'initialisation de l'Engine Wasmtime");
        
        Self { engine }
    }

    /// Charge et exécute un module Wasm dans une sandbox WASI ultra-restreinte.
    /// Pas d'accès au système de fichiers de l'hôte, pas de variables d'env héritées.
    pub fn execute_plugin(&self, wasm_path: &Path, input: &str) -> Result<String, Box<dyn std::error::Error>> {
        let mut linker = Linker::new(&self.engine);
        wasmtime_wasi::add_to_linker(&mut linker, |s: &mut PluginStore| &mut s.wasi)?;

        // Créer un contexte WASI totalement vierge (aucun dossier pré-ouvert, aucune variable d'environnement)
        // Les entrées/sorties standards (stdout/stderr) peuvent être capturées si nécessaire.
        let wasi_ctx = WasiCtxBuilder::new()
            .inherit_stdout()
            .inherit_stderr()
            .build();

        let mut store = Store::new(&self.engine, PluginStore { wasi: wasi_ctx });

        // Charger le module Wasm
        let module = Module::from_file(&self.engine, wasm_path)?;
        
        // Instancier le module dans la sandbox
        let instance = linker.instantiate(&mut store, &module)?;

        // Récupérer la fonction d'entrée du plugin (ex: "run_scraper")
        let run_func = instance
            .get_typed_func::<(), ()>(&mut store, "run_scraper")?;

        println!("[Wasm Engine] Lancement du plugin sandboxé: {:?}", wasm_path);
        
        // Exécution de la fonction Wasm
        run_func.call(&mut store, ())?;

        Ok("Plugin exécuté avec succès dans sa sandbox".to_string())
    }
}
