# Contributing

¡Se aceptan PRs! Mantén las decisiones transparentes y los datos privados:

1. `meta-skill/index.json` es la fuente de verdad para tareas, aliases, tarifas y umbrales. Los términos deben ser específicos y multilingües; evita keywords genéricas que disparen categorías equivocadas.
2. `meta-skill/SKILL.md` contiene el protocolo neutral a modelos. No escribas nombres de versiones allí.
3. Para una nueva tarea o regla, añade ejemplos positivos, una colisión/ambigüedad y un caso sin coincidencia al smoke set; luego escribe tests de regresión. El smoke set es sintético, no lo presentes como rendimiento real.
4. No llames `confidence` una probabilidad salvo que exista una calibración con etiquetas representativas y una prueba reservada independiente. No añadas telemetría de prompts por defecto.
5. El estimador de ahorro solo procesa agregados; no incorpores cargas de trabajo privadas al repositorio ni afirmes ahorro real sin validar calidad y contrastar la facturación.
6. El actualizador descubre candidatos; mantén el alias elegido salvo que exista una evaluación de calidad/capacidad. `--promote-newest` es una opción explícita, no recomendación de calidad.
7. Antes del PR (stdlib only):

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python meta-skill/scripts/update_models.py --validate
python meta-skill/scripts/evaluate_router.py
```

`--validate` y el evaluador son offline. Solo `update_models.py` sin `--validate`/`--dry-run` consulta el catálogo remoto; `--dry-run` también requiere red y no escribe.

MIT — by BELENTANI.
