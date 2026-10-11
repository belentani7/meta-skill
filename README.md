# Meta-Skill 🇧🇷

![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Python: stdlib only](https://img.shields.io/badge/python-stdlib_only-blue) ![Dependencies: 0](https://img.shields.io/badge/dependencies-0-brightgreen)

> Skill y router local, explicable y sin dependencias para recomendar tareas, modelos y límites de coste.

## Qué aporta

Meta-Skill convierte su índice de tareas y alias en una herramienta que se puede probar, no solo en instrucciones para un agente. Clasifica señales en español, portugués e inglés; calcula una **confianza heurística** explicable; se abstiene ante solicitudes ambiguas o desconocidas; recomienda un tier; y estima tokens y coste solo si dispone de tarifas separadas y aplicables al runtime.

No ejecuta inferencias ni envía el prompt a un proveedor. Es una recomendación offline, no un proxy ni una garantía de calidad o ahorro. Una tarifa ausente se muestra como **desconocida**, nunca como cero.

### Probar el router

```bash
# Recomendación legible
python3 meta-skill/scripts/route.py "Build a responsive React component"

# Salida JSON; alias de Claude Code
python3 meta-skill/scripts/route.py --runtime claude_code --json "Write pytest tests"

# Leer el prompt desde stdin (no se incluye en el resultado)
printf '%s' "Audita esta API por vulnerabilidades OWASP" \
  | python3 meta-skill/scripts/route.py --json

# Aplicar un límite alternativo en USD
python3 meta-skill/scripts/route.py --budget 0.10 "Investiga tendencias y cita fuentes"
```

Los términos se normalizan sin distinguir mayúsculas ni acentos, se comparan como palabras/frases completas y las señales compartidas pesan menos. Si no hay coincidencia, el router **no** la inventa ni la convierte en `quick_fix`: marca revisión y usa el tier predeterminado. El umbral y el margen de confianza se configuran en `index.json`.

La puntuación softmax solo ordena coincidencias manuales; **no es una probabilidad calibrada de acierto**. La estimación de tokens por caracteres es aproximada, no usa el tokenizer del proveedor. Si falta precio, contexto o compatibilidad con el runtime, el router no afirma que el presupuesto esté protegido.

### Pruebas y evaluación reproducible

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python meta-skill/scripts/update_models.py --validate
python meta-skill/scripts/evaluate_router.py
```

El evaluador calcula cobertura, accuracy, macro-F1, Brier y error de calibración (ECE) sobre un archivo etiquetado. `meta-skill/evaluations/smoke.json` contiene ejemplos sintéticos, escritos a mano para encontrar regresiones; **no** es una muestra de tráfico real ni permite afirmar precisión, probabilidad de éxito o ahorro económico en producción. Para medir rendimiento real se necesitan etiquetas representativas, consentimiento, una partición de prueba independiente y precios/calidad observados.

### Estimar ahorro con tu carga de trabajo

`estimate_savings.py` compara la política de routing por tarea (incluidos los fallbacks configurados y el límite de coste por solicitud) con un baseline fijo (por defecto, `premium_reasoning`, sin fallback). Acepta **solo agregados**; no necesita ni guarda prompts. Estima coste como tokens promedio × número de solicitudes. Como el fallback depende de cada solicitud, los agregados no equivalen a reproducir el tráfico petición por petición. Ejemplo de estructura —los números son ilustrativos, no datos medidos—:

```json
{
  "observations": [
    {
      "task_id": "testing",
      "requests": 1,
      "avg_input_tokens": 500,
      "avg_output_tokens": 200,
      "max_input_tokens": 800,
      "max_output_tokens": 400
    }
  ]
}
```

Guarda tu agregado fuera del repositorio y ejecuta:

```bash
python3 meta-skill/scripts/estimate_savings.py \
  --workload /ruta/privada/workload.json --baseline-tier premium_reasoning --json
```

Puedes probar otro límite con `--max-cost 0.10` (USD por solicitud); si se omite, se usa el del índice. Si tienes un índice privado con precios, pásalo con `--index /ruta/privada/index-con-precios.json`; los registros deben coincidir exactamente con el alias activo y contener tarifas de entrada y salida por 1.000 tokens. No hace falta guardar ese índice ni el workload en este repositorio. La herramienta marca como desconocido cualquier coste que no pueda calcular. Los campos `max_*` ayudan a detectar si las solicitudes observadas caben en el contexto; su suma es conservadora y puede combinar máximos de solicitudes distintas. Sin ellos solo se comprueba el promedio y queda incertidumbre sobre los extremos. Una cifra de ahorro negativa representa un aumento estimado de gasto. El cálculo **no mide calidad** y no es una factura ni una promesa de ahorro. El índice incluido todavía no contiene tarifas por modelo, así que no mostrará ahorro numérico hasta que cargues precios que coincidan con los alias activos y aportes agregados reales.

## Qué cubre

12 arquetipos ampliables en `meta-skill/index.json`: seguridad, frontend, APIs, DevOps/IaC, datos/ETL, ML/RAG, tests, cambios mínimos de texto, ingeniería de software general, investigación, escritura/traducción y razonamiento matemático. La clasificación sigue siendo léxica, no semántica: los casos dudosos se abstienen y deben revisarse.

Los `fallback` son alternativas declaradas, no una promesa de que un tier sea más barato que otro. El guardián solo selecciona una alternativa si puede verificar las tarifas de entrada/salida, el límite configurado y el contexto. Si no hay alternativa verificablemente asequible, bloquea la recomendación.

## Instalación de la skill

- **Claude Code:** copia la carpeta `meta-skill/` a `~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`).
- **Claude.ai / Cowork:** sube la carpeta desde Settings → Capabilities, siguiendo el flujo disponible en tu cuenta.

El CLI de recomendación se ejecuta aparte con Python 3.11 o posterior y solo biblioteca estándar. No necesitas instalar paquetes.

## Actualizar el catálogo de modelos

```bash
python3 meta-skill/scripts/update_models.py --validate  # local, no red
python3 meta-skill/scripts/update_models.py --dry-run          # vista previa
python3 meta-skill/scripts/update_models.py                    # descubre candidatos
python3 meta-skill/scripts/update_models.py --promote-newest   # promoción explícita y no evaluada
```

El actualizador lee la lista pública de modelos de OpenRouter, normalmente sin API key; si tu acceso requiere autenticación, usa opcionalmente `OPENROUTER_API_KEY` desde el entorno (nunca se guarda en el índice). Filtra modelos con salida de texto, mantiene por separado precio de entrada y salida, conserva el último dato si no hay coincidencia y escribe de forma atómica. **Por defecto no cambia los alias seleccionados**: que un modelo sea nuevo no demuestra que sea mejor. Tras evaluar una alternativa, actualiza manualmente `aliases`; `--promote-newest` es un atajo optativo no basado en calidad. `local_zero_token` nunca se autoactualiza. Consulta [el estudio y sus fuentes](docs/ROUTING_RESEARCH.md) antes de interpretar métricas o tendencias.

El catálogo es una referencia, no facturación: no incorpora necesariamente caché, imágenes, reintentos, descuentos, límites del proveedor ni la tarifa real de una CLI.

## Estructura

```text
meta-skill/
  SKILL.md                         # protocolo neutral respecto a marcas/versiones
  index.json                       # tareas, alias, umbrales y ajustes
  scripts/route.py                 # router CLI offline
  scripts/evaluate_router.py       # métricas reproducibles con casos etiquetados
  scripts/estimate_savings.py      # comparación de coste con workload agregado
  scripts/update_models.py         # actualizador de catálogo, stdlib
  evaluations/smoke.json           # casos sintéticos; no datos de producción
tests/
  test_meta_skill.py               # índice y actualizador
  test_router.py                   # clasificación, privacidad, límites y CLI
.github/workflows/ci.yml            # CI multiplataforma
```

## Autor

**BELENTANI**, artista y cantante. Neurodivergente, sin etiquetas: lo vivo como un don. Hecho con alma brasileña desde Barcelona, mi casa.

IG: [@BELENTANI_](https://instagram.com/belentani_)

Licencia [MIT](LICENSE).
