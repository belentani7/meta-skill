# Meta-Skill 🇧🇷

![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Python: stdlib only](https://img.shields.io/badge/python-stdlib_only-blue) ![Dependencies: 0](https://img.shields.io/badge/dependencies-0-brightgreen)

> Skill y router local, explicable y sin dependencias para recomendar tareas, modelos y límites de coste.

## Qué aporta

Meta-Skill convierte su índice de tareas y alias en una herramienta que se puede probar, no solo en instrucciones para un agente. Clasifica señales en español, portugués e inglés; calcula una **confianza heurística** explicable; se abstiene ante solicitudes ambiguas o desconocidas; recomienda un tier; y estima tokens y coste solo si dispone de tarifas separadas y aplicables al runtime.

No ejecuta inferencias ni envía el prompt a un proveedor. Es una recomendación offline, no un proxy ni una garantía de calidad o ahorro. Una tarifa ausente se muestra como **desconocida**, nunca como cero.

### Probar el router

```bash
python3 meta-skill/scripts/route.py "Build a responsive React component"
python3 meta-skill/scripts/route.py --runtime claude_code --json "Write pytest tests"
printf '%s' "Audita esta API por vulnerabilidades OWASP" | python3 meta-skill/scripts/route.py --json
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

El evaluador existente calcula métricas sobre ejemplos etiquetados. Los ejemplos sintéticos no representan tráfico real ni permiten afirmar precisión, probabilidad de éxito o ahorro económico en producción. Para medir rendimiento real se necesitan etiquetas representativas, consentimiento, una partición de prueba independiente y precios/calidad observados.

## Evaluation Lab

El directorio [evaluation-lab](evaluation-lab/README.md) añade un harness independiente y sin dependencias para evaluar routers mediante JSONL etiquetado. Informa accuracy, macro-F1, métricas por clase, matriz de confusión, cobertura, accuracy selectiva y abstención; calcula Brier y ECE solo cuando se entregan vectores de probabilidad completos. Rechaza IDs duplicados, predicciones ausentes, clases desconocidas y datos de calibración incompletos.

```bash
python3 evaluation-lab/evaluate.py \
  --gold evaluation-lab/fixtures/gold.jsonl \
  --predictions evaluation-lab/fixtures/predictions.jsonl \
  --out /tmp/report.json --markdown /tmp/report.md
python3 -m unittest discover -s evaluation-lab/tests -v
```

**Importante:** las fixtures son sintéticas y solo demuestran el contrato del evaluador. No son resultados medidos de Meta-Skill ni de ningún modelo. Consulta [la metodología](evaluation-lab/METHODOLOGY.md) antes de usar métricas para decisiones de release.

### Estimar ahorro con tu carga de trabajo

**Estado: en desarrollo.** La herramienta es un estimador inicial, no una función de producción validada. Aún hacen falta tarifas verificadas, datos agregados representativos y una evaluación de calidad antes de interpretar sus cifras como ahorro real.

`estimate_savings.py` compara la política de routing por tarea (incluidos los fallbacks configurados y el límite de coste por solicitud) con un baseline fijo. Acepta **solo agregados**; no necesita ni guarda prompts. Estima coste como tokens promedio × número de solicitudes. Como el fallback depende de cada solicitud, los agregados no equivalen a reproducir el tráfico petición por petición. La herramienta marca como desconocido cualquier coste que no pueda calcular. El cálculo **no mide calidad** y no es una factura ni una promesa de ahorro.

## Qué cubre

12 arquetipos ampliables en `meta-skill/index.json`: seguridad, frontend, APIs, DevOps/IaC, datos/ETL, ML/RAG, tests, cambios mínimos de texto, ingeniería de software general, investigación, escritura/traducción y razonamiento matemático. La clasificación sigue siendo léxica, no semántica: los casos dudosos se abstienen y deben revisarse.

Los `fallback` son alternativas declaradas, no una promesa de que un tier sea más barato que otro. El guardián solo selecciona una alternativa si puede verificar las tarifas de entrada/salida, el límite configurado y el contexto. Si no hay alternativa verificablemente asequible, bloquea la recomendación.

## Instalación de la skill

- **Claude Code:** copia la carpeta `meta-skill/` a `~/.claude/skills/` (Windows: `%USERPROFILE%\\.claude\\skills\\`).
- **Claude.ai / Cowork:** sube la carpeta desde Settings → Capabilities, siguiendo el flujo disponible en tu cuenta.

El CLI de recomendación se ejecuta aparte con Python 3.11 o posterior y solo biblioteca estándar. No necesitas instalar paquetes.

## Actualizar el catálogo de modelos

```bash
python3 meta-skill/scripts/update_models.py --validate
python3 meta-skill/scripts/update_models.py --dry-run
python3 meta-skill/scripts/update_models.py
python3 meta-skill/scripts/update_models.py --promote-newest
```

El actualizador lee la lista pública de modelos de OpenRouter, normalmente sin API key; si tu acceso requiere autenticación, usa opcionalmente `OPENROUTER_API_KEY` desde el entorno (nunca se guarda en el índice). **Por defecto no cambia los alias seleccionados**: que un modelo sea nuevo no demuestra que sea mejor. Consulta [el estudio y sus fuentes](docs/ROUTING_RESEARCH.md) antes de interpretar métricas o tendencias.

El catálogo es una referencia, no facturación: no incorpora necesariamente caché, imágenes, reintentos, descuentos, límites del proveedor ni la tarifa real de una CLI.

## Autor

**BELENTANI**, artista y cantante. Hecho con alma brasileña desde Barcelona.

IG: [@BELENTANI_](https://instagram.com/belentani_)

Licencia [MIT](LICENSE).
