# Enrutamiento de modelos: tendencias, probabilidades y plan de evaluación

**Revisión:** 11 de octubre de 2026<br>
**Alcance:** router léxico local de Meta-Skill. No es una comparación de modelos ni un benchmark de calidad.

## Qué sugiere la investigación consultada

1. **El valor se mide en la frontera coste-calidad, no por el nombre o la fecha del modelo.** RouteLLM estudia routers entrenados con preferencias humanas y evalúa el equilibrio entre respuesta y coste en benchmarks concretos. El artículo publicado en ICLR 2025 informa ahorros superiores a 2× en algunos de sus experimentos; ese resultado pertenece a sus modelos, datos y objetivos, no es una predicción para cualquier repositorio o carga de trabajo. [Ong et al., *RouteLLM: Learning to Route LLMs with Preference Data*](https://arxiv.org/abs/2406.18665).
2. **El presupuesto de salida también importa.** R2-Router, un trabajo de investigación de 2026, plantea elegir conjuntamente el modelo y el límite de longitud de respuesta. Sus resultados son evidencia experimental temprana —no una garantía comercial— y muestran por qué una etiqueta estática de “modelo barato/caro” puede omitir alternativas. [Xue et al., *R2-Router: A New Paradigm for LLM Routing with Reasoning*](https://arxiv.org/abs/2602.02823).
3. **El catálogo de modelos es más que el identificador.** La API documentada de OpenRouter expone campos como fecha de creación, ventana de contexto, modalidades y tarifas separadas de prompt y completion. Son datos útiles para filtrar y estimar costes, pero no prueban que un modelo resuelva mejor una tarea. [Documentación oficial de modelos de OpenRouter](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties).
4. **Una ruta debe poder abstenerse.** Si no hay señal, si varias intenciones empatan o si no puede verificarse un límite duro, adivinar una categoría o precio puede ser peor que pedir revisión. Esta implementación conserva un tier predeterminado solo como recomendación y no envía inferencias.

### Decisión de producto derivada

- El actualizador **descubre candidatos** y guarda sus precios separados; no cambia alias seleccionados automáticamente. La fecha más reciente no es una medida de calidad. `--promote-newest` existe como acción explícita y advierte que no es un benchmark.
- La taxonomía combina tareas de ingeniería con investigación, escritura/traducción y razonamiento. El router busca frases completas tras normalizar acentos, pondera menos las señales que comparten varias tareas y devuelve varios candidatos.
- `needs_review` es una salida válida, no un error oculto. Términos sin evidencia no se convierten en `quick_fix`.
- El límite de coste solo se aplica automáticamente si el alias corresponde exactamente al modelo del catálogo, hay tarifas válidas de **entrada y salida**, y el contexto estimado cabe. Un precio ausente nunca equivale a $0; un límite no verificable devuelve `budget_unknown`.
- El recuento de tokens por caracteres es una aproximación configurable. No sustituye el tokenizer ni contempla por completo prefijos de sistema, caché, imágenes, reintentos o tarifas específicas de una CLI.

## ¿Qué significa aquí “probabilidad”?

El campo `confidence` es un **softmax sobre pesos IDF de keywords escritos a mano**. Sirve para ordenar candidatos y aplicar un umbral/margen; no se entrenó con prompts etiquetados, no se contrastó con respuestas buenas/malas y no es una probabilidad calibrada de que la clasificación o la respuesta sean correctas. Un 0,9 en este router no significa “90 % de probabilidad de éxito”. El evaluator calcula Brier/ECE solo para la corrección de la tarea seleccionada y solo entre los casos enrutados; no mide calidad de respuestas, calibración multiclase completa ni resultados futuros. No convierte datos sintéticos en evidencia de producción.

La suite incluida tiene **39 casos sintéticos redactados a mano**: 36 se clasifican y 3 se abstienen. En la última ejecución local, los 39 casos coincidieron con sus etiquetas previstas. Esa coincidencia solo confirma que el smoke set ejercita las reglas que se escribieron para él; no estima precisión futura, popularidad de tareas, calidad del modelo ni ahorro. No debe citarse como KPI.

No existe en el repositorio una distribución real de prompts, tasa de tareas, coste de inferencia, preferencia de usuarios ni rendimiento comparativo por modelo. Por eso no sería responsable inventar probabilidades globales o un porcentaje de ahorro.

## Cómo estimar una carga de trabajo con datos reales

Con una muestra representativa y etiquetada, el equipo podría estimar, por tarea e idioma:

- **Cobertura:** fracción de solicitudes en las que el router se atreve a elegir.
- **Precisión/recall y macro-F1 por tarea:** dónde confunde categorías o se abstiene.
- **Calibración:** Brier/ECE en datos reservados, calculados sobre solicitudes no usadas para ajustar umbrales.
- **Calidad por ruta:** evaluación humana o benchmark pareado del resultado de cada modelo para la misma solicitud.
- **Coste observado:** tokens reales de entrada y salida, tarifas vigentes y cargos por caché/media/proveedor.

Como contabilidad simplificada, si `p_i` es la proporción observada de la tarea `i`, y `c_i` es su coste medio medido (no supuesto), entonces:

```text
coste medio del router ≈ Σ p_i × c_i
ahorro frente a baseline = 1 − (coste medio del router / coste medio del baseline)
```

La fórmula solo es informativa si la calidad se mantiene en un umbral predefinido y el baseline usa la misma carga de trabajo, salida, proveedores y periodo de precios. `meta-skill/scripts/estimate_savings.py` implementa la comparación desde un JSON de agregados (`task_id`, número de solicitudes, promedios de tokens y, opcionalmente, máximos observados). Modela los fallbacks configurados y el límite de coste por solicitud; el baseline fijo no aplica fallbacks. Como los umbrales pueden cambiar una ruta, aplicar el agregado promedio no equivale a reproducir cada solicitud. No lee prompts ni registra telemetría. Los máximos ayudan a revisar el límite de contexto, aunque no predicen solicitudes futuras; como se suman por separado, pueden combinar máximos de peticiones distintas y dar un límite conservador. El índice distribuido todavía no tiene precios por modelo, así que la salida de ahorro seguirá como desconocida hasta cargar tarifas del alias exacto. Este repositorio aún no recoge esas observaciones.

### Protocolo recomendado antes de hablar de probabilidades

1. Añadir casos de prueba de forma consentida; redactar secretos y evitar guardar prompts identificables.
2. Etiquetar intención y permitir `abstain`; incluir errores, tareas mixtas y ejemplos adversariales, no solo ejemplos “limpios”.
3. Separar entrenamiento/ajuste de umbrales de una prueba temporal y por idioma que no se use para afinar keywords.
4. Comparar contra baselines simples (tier fijo, reglas actuales) y registrar calidad, coste real, latencia y cobertura por categoría.
5. Calibrar en la partición de validación; publicar intervalos e incertidumbre y volver a comprobarlos cuando cambien modelos, keywords o precios.
6. Mantener el registro local/opt-in y agregado. El CLI actual no persiste prompts ni telemetría.

## Siguiente evolución recomendada

1. **Enriquecer capacidades y disponibilidad**: modalidades de entrada/salida, contexto efectivo, endpoints y región, sin escoger modelos que no soporten la solicitud.
2. **Medir presupuestos de salida**: permitir escenarios por longitud/tarea y comparar coste-calidad sin asegurar que acortar una respuesta conserve su calidad.
3. **Calibrar solo con datos suficientes y autorizados**: mantener este router determinista como baseline e introducir un modelo aprendido únicamente si mejora el conjunto reservado.
4. **Vigilar deriva y coste real**: un alias nuevo, una tarifa cambiada o un cambio en idiomas modifica la distribución. La fecha de creación no es una puntuación de calidad.

## Fuentes primarias

- [RouteLLM — arXiv:2406.18665](https://arxiv.org/abs/2406.18665), publicado en ICLR 2025.
- [R2-Router — arXiv:2602.02823](https://arxiv.org/abs/2602.02823), prepublicación de 2026; resultados sujetos a sus configuraciones experimentales.
- [OpenRouter — catálogo y propiedades de modelos](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties), fuente de metadatos y tarifas públicas usada por el actualizador.
