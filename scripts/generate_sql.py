#!/usr/bin/env python3
"""
Generate BigQuery SQL with embedded WebAssembly code.
This script reads a WebAssembly byte array, compresses it using a hex-encoded
dictionary, and creates a BigQuery SQL file with the WebAssembly embedded in
a JavaScript UDF.
"""

import os
from collections import Counter


def read_binary_file(filename):
    """Read binary data from a file"""
    with open(filename, 'rb') as file:
        return file.read()


def hex_encode(binary_data):
    """Convert binary data to hexadecimal string"""
    return binary_data.hex()


def compress_hex_dictionary(hex_string):
    """
    Compress a hexadecimal string using a custom dictionary compression
    Using non-hexadecimal characters to encode dictionary entries
    """
    # Split the hexadecimal string into 4-character chunks (2 bytes)
    chunks = [hex_string[i:i + 4] for i in range(0, len(hex_string), 4)]

    # Identify the most frequent patterns
    counter = Counter(chunks)
    # Utilisez plus de motifs communs (jusqu'à 80) pour profiter du dictionnaire étendu
    most_common = counter.most_common(80)

    # Create a substitution dictionary using non-hex letters as markers
    dictionary = {}
    reverse_dict = {}

    # Utilisez une gamme beaucoup plus large de caractères comme marqueurs
    # Exclure les caractères qui pourraient interférer avec le code JS: \, ", ', `, $, {, },
    valid_markers = (
            "GHIJKLMNOPQRSTUVWXYZ" +  # Majuscules non-hexa
            "ghijklmnopqrstuvwxyz" +  # Minuscules non-hexa
            "!#%&()*+,-./:;<=>?@[]^_|~" +  # Caractères spéciaux sans interférence
            "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞß" +  # Caractères accentués et internationaux
            "àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"  # Caractères accentués minuscules
    )

    for i, (pattern, _) in enumerate(most_common):
        if i < len(valid_markers) and len(pattern) == 4:
            marker = valid_markers[i]
            dictionary[pattern] = marker
            reverse_dict[marker] = pattern

    # Encode using the dictionary
    compressed = []
    i = 0
    while i < len(hex_string):
        found = False
        if i + 3 < len(hex_string):
            chunk = hex_string[i:i + 4]
            if chunk in dictionary:
                compressed.append(dictionary[chunk])
                i += 4
                found = True

        if not found:
            # Add raw hex data (not compressed)
            compressed.append(hex_string[i:i + 2])
            i += 2

    # Build the serialized dictionary
    serialized_dict = []
    for marker, pattern in reverse_dict.items():
        serialized_dict.append(f"{marker}{pattern}")

    # Return the dictionary and compressed data
    return "".join(serialized_dict), "".join(compressed)


def generate_js_decompression(dict_part, data_part):
    """Generate JavaScript code for decompression and SQL wrapper"""
    # Format dictionary and data for code readability
    formatted_dict = ''
    for i in range(0, len(dict_part), 200):
        chunk = dict_part[i:i + 200]
        formatted_dict += f'    "{chunk}"+\n'
    formatted_dict = formatted_dict.rstrip('+\n')

    formatted_data = ''
    for i in range(0, len(data_part), 200):
        chunk = data_part[i:i + 200]
        formatted_data += f'    "{chunk}"+\n'
    formatted_data = formatted_data.rstrip('+\n')

    sql_code = f"""CREATE TEMP FUNCTION lat_lng_to_h3(x FLOAT64, y FLOAT64, res INT64)
RETURNS INT64
LANGUAGE js AS r\"\"\"

// WASM decompression with hexadecimal dictionary
function decompressWasm() {{
  // Dictionary encoded in hexadecimal
  const dictPart = 
{formatted_dict};

  // Compressed data
  const dataPart = 
{formatted_data};

  // Build the dictionary
  const dict = {{}};
  let i = 0;
  while (i < dictPart.length) {{
    const marker = dictPart.substr(i, 1);
    const pattern = dictPart.substr(i+1, 4);
    dict[marker] = pattern;
    i += 5;
  }}

  // Decompress the data
  let decompressed = '';
  i = 0;
  while (i < dataPart.length) {{
    const char = dataPart.substr(i, 1);
    // Check if it's a dictionary marker (non-hexadecimal character)
    if (!/[0-9a-fA-F]/.test(char)) {{
      // It's a code in our dictionary
      if (dict[char]) {{
        decompressed += dict[char];
      }}
      i += 1;
    }} else {{
      // It's a regular hex byte
      decompressed += dataPart.substr(i, 2);
      i += 2;
    }}
  }}

  // Convert the hexadecimal string to a byte array
  const bytes = new Uint8Array(decompressed.length / 2);
  for (let i = 0; i < decompressed.length; i += 2) {{
    bytes[i / 2] = parseInt(decompressed.substr(i, 2), 16);
  }}

  return bytes;
}}


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
    const wasmBytes = decompressWasm();
    return WebAssembly.instantiate(wasmBytes, imports).then(wa => {{
        const exports = wa.instance.exports;
        const func = exports.lat_lng_to_h3;
        return func(y, x, res);
    }});
}}
return main();
\"\"\";

-- Example usage
WITH numbers AS (
  SELECT 1 AS lon, 5 as lat, 3 as res UNION ALL
  SELECT 2 AS lon, 10 as lat, 5 as res UNION ALL
  SELECT 3 as lon, 15 as lat, 7 as res
  )
SELECT
lon,
lat,
lat_lng_to_h3(lon, lat, res) as h3
FROM numbers;
"""
    return sql_code


# Create artifacts directory if it doesn't exist
os.makedirs('artifacts', exist_ok=True)

# Read binary file and encode as hexadecimal
binary_data = read_binary_file("h3o_optimized.wasm")
hex_data = hex_encode(binary_data)

# Compress data using a hexadecimal dictionary
dict_part, data_part = compress_hex_dictionary(hex_data)

# Calculate compression ratio
original_size = len(binary_data)
compressed_size = (len(dict_part) + len(data_part)) / 2  # estimation in bytes
compression_ratio = (1 - compressed_size / original_size) * 100

print(f"Original size: {original_size} bytes")
print(f"Estimated compressed size: {compressed_size:.0f} bytes")
print(f"Dictionary size: {len(dict_part) / 2:.0f} bytes")
print(f"Compressed data size: {len(data_part) / 2:.0f} bytes")
print(f"Compression ratio: {compression_ratio:.2f}%")

# Generate JavaScript code for decompression
sql_content = generate_js_decompression(dict_part, data_part)

# Write the result to a file
output_file = "artifacts/sumInputs.sql"
with open(output_file, 'w') as f:
    f.write(sql_content)
print(f"JavaScript code saved to {output_file}")

# Create README for the artifact
readme_content = """# WebAssembly BigQuery Function

This SQL file contains a BigQuery UDF (User-Defined Function) powered by WebAssembly.

## Usage

1. Copy the SQL content into your BigQuery query editor
2. Run the query to see the function in action
3. Modify the example query at the bottom to use your own data

## Function Details

- Function name: `lat_lng_to_h3`
- Parameters: x (longitude) and y (latitude) as FLOAT64, resolution as INT64
- Returns: The H3 index as INT64
- Implementation: WebAssembly compiled from Rust
"""

with open('artifacts/README.md', 'w') as f:
    f.write(readme_content)

print("BigQuery SQL successfully generated in artifacts/sumInputs.sql")
