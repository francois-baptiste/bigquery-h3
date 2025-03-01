#!/usr/bin/env python3
"""
Generate BigQuery SQL with embedded WebAssembly code.
This script reads a WebAssembly byte array from wasm_array.txt,
formats it, and creates a BigQuery SQL file with the WebAssembly
embedded in a JavaScript UDF.
"""

import os


def read_binary_file(filename):
    with open(filename, 'rb') as file:
        return file.read()


def hex_encode(binary_data):
    return binary_data.hex()


def compress_hex_rle(hex_string):
    result = []
    i = 0

    # Traiter les caractères deux par deux (chaque octet en hex)
    while i < len(hex_string):
        if i + 1 < len(hex_string):
            current_pair = hex_string[i:i + 2]
            count = 1
            j = i + 2

            # Compter combien de fois ce pair apparaît de suite
            while j + 1 < len(hex_string) and hex_string[j:j + 2] == current_pair:
                count += 1
                j += 2

            if count > 1:
                # Utiliser lettres non-hexadécimales (g-z) pour l'encodage RLE
                if count <= 20:
                    # g=1, h=2, ..., z=20
                    count_char = chr(ord('g') + count - 1)
                    result.append(count_char + current_pair)
                else:
                    # Si count > 20, diviser en plusieurs segments
                    while count > 0:
                        segment = min(count, 20)
                        count_char = chr(ord('g') + segment - 1)
                        result.append(count_char + current_pair)
                        count -= segment
            else:
                result.append(current_pair)

            i = j
        else:
            # Cas d'un caractère unique à la fin
            result.append(hex_string[i])
            i += 1

    return ''.join(result)

def generate_js_decompression(compressed_data):
    # Créer une version formatée du code hexadécimal compressé
    formatted_data = ''
    for i in range(0, len(compressed_data), 300):
        chunk = compressed_data[i:i + 300]
        formatted_data += f'    "{chunk}"+\n'
    formatted_data = formatted_data.rstrip('+\n')

    sql_code = f"""CREATE TEMP FUNCTION lat_lng_to_h3(x FLOAT64, y FLOAT64, res INT64)
RETURNS INT64
LANGUAGE js AS r\"\"\"

// Décompression WASM
function decompressWasm() {{
  const compressed = 
{formatted_data};

  let decompressed = '';
  let i = 0;

  while (i < compressed.length) {{
    // Vérifier si le caractère actuel est un marqueur de répétition (g-z)
    if (compressed[i] >= 'g' && compressed[i] <= 'z') {{
      const count = compressed[i].charCodeAt(0) - 'g'.charCodeAt(0) + 1;
      const pair = compressed[i+1] + compressed[i+2];
      for (let j = 0; j < count; j++) {{
        decompressed += pair;
      }}
      i += 3;
    }} else {{
      decompressed += compressed[i];
      i++;
    }}
  }}

  // Convertir la chaîne hexadécimale en tableau d'octets
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

# Lire le fichier binaire et encoder en hexadécimal
binary_data = read_binary_file("h3o_optimized.wasm")
hex_data = hex_encode(binary_data)

# Compresser les données en utilisant RLE
compressed_data = compress_hex_rle(hex_data)

# Calculer le taux de compression
original_size = len(binary_data)
compressed_size = len(compressed_data) / 2  # approximation car notre encodage compressé utilise des caractères
compression_ratio = (1 - compressed_size / original_size) * 100

print(f"Taille originale: {original_size} octets")
print(f"Taille compressée estimée: {compressed_size:.0f} octets")
print(f"Taux de compression: {compression_ratio:.2f}%")

# Générer le code JavaScript pour la décompression
sql_content = generate_js_decompression(compressed_data)

# Écrire le résultat dans un fichier
output_file = "artifacts/sumInputs.sql"
with open(output_file, 'w') as f:
    f.write(sql_content)
print(f"Code JavaScript enregistré dans {output_file}")

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