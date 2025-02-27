#!/bin/bash
set -e

# Get content of generated array file
WASM_ARRAY=$(cat wasm_array.txt | grep -v "unsigned" | tr -d '\n' | sed 's/  / /g')

# Create artifacts directory
mkdir -p artifacts

# Generate SQL query with embedded WebAssembly code
echo "Generating BigQuery SQL with WebAssembly..."
cat > artifacts/sumInputs.sql << EOF
-- WebAssembly-powered BigQuery function
-- Generated: $(date)
-- This SQL creates a temporary function that uses WebAssembly to add two numbers

CREATE TEMP FUNCTION lat_lng_to_h3(x FLOAT64, y FLOAT64)
RETURNS FLOAT64
LANGUAGE js AS r"""
async function main() {
    const memory = new WebAssembly.Memory({ initial: 256, maximum: 256 });
    const env = {
        'abortStackOverflow': _ => { throw new Error('overflow'); },
        'table': new WebAssembly.Table({ initial: 0, maximum: 0, element: 'anyfunc' }),
        'tableBase': 0,
        'memory': memory,
        'memoryBase': 1024,
        'STACKTOP': 0,
        'STACK_MAX': memory.buffer.byteLength,
    };
    const imports = { env };
const wasmHexLines = [
${WASM_ARRAY}
];

const wasmBytes = new Uint8Array(wasmHexLines.join('').match(/.{1,2}/g).map(byte => parseInt(byte, 16)));

    return WebAssembly.instantiate(wasmBytes, imports).then(wa => {
        const exports = wa.instance.exports;
        const func = exports.lat_lng_to_h3;
        return func(y, x, 7);
    });
}
return main();
""";

-- Example usage
WITH numbers AS (
  SELECT 1 AS lon, 5 as lat UNION ALL
  SELECT 2 AS x, 10 as y UNION ALL
  SELECT 3 as x, 15 as y
  )
SELECT
lon,
lat,
lat_lng_to_h3(lon, lat) << 12 as h3
FROM numbers;
EOF

# Create a README for the artifact
cat > artifacts/README.md << EOF
# WebAssembly BigQuery Function

This SQL file contains a BigQuery UDF (User-Defined Function) powered by WebAssembly.

## Usage

1. Copy the SQL content into your BigQuery query editor
2. Run the query to see the function in action
3. Modify the example query at the bottom to use your own data

## Function Details

- Function name: \`lat_lng_to_h3\`
- Parameters: two FLOAT64 values
- Returns: The H3 index as INT64
- Implementation: WebAssembly compiled from Rust
EOF

echo "BigQuery SQL successfully generated in artifacts/sumInputs.sql"
