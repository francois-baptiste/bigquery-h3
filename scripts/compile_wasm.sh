#!/bin/bash
set -e

# Compile Rust code in WebAssembly
cargo build --target wasm32-unknown-unknown --release

# Optimized WebAssembly binary
wasm-opt -Oz target/wasm32-unknown-unknown/release/h3o_wasm.wasm -o h3o_optimized.wasm

xxd -p h3o_optimized.wasm | tr -d '\n' > wasm_hex.txt
