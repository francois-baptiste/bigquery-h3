#!/usr/bin/env python3
"""
Generate BigQuery SQL with embedded WebAssembly code.
This script reads a WebAssembly byte array from wasm_array.txt,
formats it, and creates a BigQuery SQL file with the WebAssembly
embedded in a JavaScript UDF.
"""

import os
import re
import datetime

# Create artifacts directory if it doesn't exist
os.makedirs('artifacts', exist_ok=True)

# Read the WebAssembly array from the file
print("Reading WebAssembly byte array...")
with open('wasm_hex.txt', 'r') as f:
    wasm_array_content = f.read()

# Clean up the array content (remove variable names and newlines)
wasm_bytes = re.sub(r'unsigned char.*\[\] = \{|\};.*', '', wasm_array_content, flags=re.DOTALL)
wasm_bytes = re.sub(r'\s+', ' ', wasm_bytes).strip()

# Generate SQL file with the WebAssembly embedded
print("Generating BigQuery SQL...")
sql_content = f"""CREATE TEMP FUNCTION lat_lng_to_h3(x FLOAT64, y FLOAT64)
RETURNS INT64
LANGUAGE js AS r\"\"\"
async function main() {{
    const memory = new WebAssembly.Memory({{ initial: 256, maximum: 256 }});
    const env = {{
        'abortStackOverflow': _ => {{ throw new Error('overflow'); }},
        'table': new WebAssembly.Table({{ initial: 0, maximum: 0, element: 'anyfunc' }}),
        'tableBase': 0,
        'memory': memory,
        'memoryBase': 1024,
        'STACKTOP': 0,
        'STACK_MAX': memory.buffer.byteLength,
    }};
    const imports = {{ env }};
    const bytes = new Uint8Array([
      {wasm_bytes}
    ]);
    return WebAssembly.instantiate(bytes, imports).then(wa => {{
        const exports = wa.instance.exports;
        const func = exports.lat_lng_to_h3;
        return func(x, y);
    }});
}}
return main();
\"\"\";

-- Example usage
WITH numbers AS (
  SELECT 1 AS lon, 5 as lat UNION ALL
  SELECT 2 AS lon, 10 as lat UNION ALL
  SELECT 3 as lon, 15 as lat
  )
SELECT
lon,
lat,
lat_lng_to_h3(lon, lat) as h3
FROM numbers;
"""

# Write the SQL to a file
with open('artifacts/sumInputs.sql', 'w') as f:
    f.write(sql_content)

# Create README for the artifact
readme_content = """# WebAssembly BigQuery Function

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
"""

with open('artifacts/README.md', 'w') as f:
    f.write(readme_content)

print("BigQuery SQL successfully generated in artifacts/sumInputs.sql")