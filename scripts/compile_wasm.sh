#!/bin/bash
set -e

# Compiler le code Rust en WebAssembly
cargo build --target wasm32-unknown-unknown --release

# Convertir le binaire WebAssembly en array C pour l'utiliser dans le SQL
xxd -i target/wasm32-unknown-unknown/release/wasm_bq_function.wasm > wasm_array.txt
