#!/bin/bash
set -e

# Récupérer le contenu du fichier d'array généré
WASM_ARRAY=$(cat wasm_array.txt | grep -v "unsigned" | tr -d '\n' | sed 's/  / /g')

# Générer la requête SQL avec le code WebAssembly intégré
cat > bq_query.sql << EOF
CREATE TEMP FUNCTION sumInputs(x FLOAT64, y FLOAT64)
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
    const bytes = new Uint8Array([
      ${WASM_ARRAY}
    ]);
    return WebAssembly.instantiate(bytes, imports).then(wa => {
        const exports = wa.instance.exports;
        const sum = exports.sum;
        return sum(x, y);
    });
}
return main();
""";

WITH numbers AS
  (SELECT 1 AS x, 5 as y
  UNION ALL
  SELECT 2 AS x, 10 as y
  UNION ALL
  SELECT 3 as x, 15 as y)
SELECT x, y, sumInputs(x, y) as sum
FROM numbers;
EOF

echo "BigQuery SQL a été généré avec succès dans le fichier bq_query.sql"
