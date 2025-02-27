#!/bin/bash
set -e

# Compile Rust code in WebAssembly
cargo build --target wasm32-unknown-unknown --release

# Optimized WebAssembly binary
wasm-opt -Oz target/wasm32-unknown-unknown/release/h3o_wasm.wasm -o add_optimized.wasm

# Convert WebAssembly binary to C array for use in SQL
xxd -p -c 0 add_optimized.wasm > wasm_array.txt