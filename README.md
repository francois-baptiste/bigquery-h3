# WebAssembly in BigQuery

This project demonstrates how to use WebAssembly in BigQuery SQL queries, with an automated CI/CD pipeline using GitHub Actions.

## How It Works

1. We write a Rust function that gets compiled to WebAssembly
2. The WebAssembly binary is converted to a byte array
3. The byte array is embedded in a BigQuery SQL query with JavaScript UDF
4. The GitHub Actions workflow automates this process and produces artifacts

## Development

### Prerequisites

- Rust with wasm32-unknown-unknown target
- xxd tool (for binary to array conversion)

### Local Build

```bash
# Compile Rust to WebAssembly
cargo build --target wasm32-unknown-unknown --release

# Convert to C array
xxd -i target/wasm32-unknown-unknown/release/wasm_bq_function.wasm > wasm_array.txt

# Generate SQL
./scripts/generate_bq_query.sh
```

## CI/CD Pipeline

The GitHub Actions workflow in this repository:

1. Compiles the Rust code to WebAssembly
2. Generates a SQL file with the embedded WebAssembly
3. Creates artifacts with the SQL and documentation
4. On main branch commits, creates a GitHub release

## Usage

After the workflow runs, download the artifact or release, and run the SQL in BigQuery console to use the WebAssembly-powered function.

## License

MIT