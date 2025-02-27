#!/bin/bash
set -e

# Create artifacts directory if it does not exist
mkdir -p artifacts

# Compile Rust code in WebAssembly
cargo build --target wasm32-unknown-unknown --release

# Optimized WebAssembly binary
wasm-opt -Oz target/wasm32-unknown-unknown/release/h3o_wasm.wasm -o add_optimized.wasm

# Convert WebAssembly binary to C array for use in SQL
xxd -p -c 0 add_optimized.wasm > artifacts/wasm_array.txt