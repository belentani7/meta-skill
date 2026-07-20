# Meta-Skill 🇧🇷

![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Python: stdlib only](https://img.shields.io/badge/python-stdlib_only-blue) ![Deps: 0](https://img.shields.io/badge/dependencies-0-brightgreen)

> Router universal y guardián de tokens para **Claude Code / Claude.ai** — la "mother skill".
> 🇧🇷 [Versão em Português (BR)](README.pt-BR.md)

## Qué hace

Se activa ANTES de cualquier tarea: clasifica tu prompt (keywords ES/EN), elige el **tier de modelo más barato capaz** de resolverla, delega al skill instalado que mejor encaje y **frena el gasto** si supera tu presupuesto. El enrutamiento es 100% local — cero APIs, cero tokens extra.

```
prompt → clasificar (keywords) → tier → modelo (aliases) → skill/directiva → ejecutar
                                  ↓ si falla o excede presupuesto
                               fallback más barato
```

Los nombres de modelos viven solo en `index.json` (datos, no código): diseñado para seguir funcionando cuando los modelos de hoy ya no existan.

## Instalación

**Claude.ai / Cowork:** descarga `meta-skill.skill` (release) y usa "Save skill", o sube la carpeta en Settings → Capabilities.

**Claude Code:** copia la carpeta `meta-skill/` a `~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`).

## Actualizar el catálogo de modelos

```bash
python3 meta-skill/scripts/update_models.py            # actualiza index.json
python3 meta-skill/scripts/update_models.py --validate # chequeo offline (CI)
```

Python puro (stdlib, cero dependencias). Consulta la lista pública de OpenRouter (sin API key), elige el modelo de texto más nuevo por tier vía regex y reescribe solo `index.json` con **escritura atómica**. Sin red no toca nada: sigue funcionando offline. El tier local (`local_zero_token`) nunca se auto-actualiza.

## Estructura

```
meta-skill/
├── SKILL.md                 # protocolo de enrutamiento (nunca contiene nombres de modelos)
├── index.json               # tareas, tiers, aliases, regex, precios — los datos
└── scripts/update_models.py # actualizador (OpenRouter, sin key, atómico)
tests/                       # unittest, stdlib
.github/workflows/ci.yml     # CI: tests + validate en Linux y Windows
```

## Tests

```bash
python -m unittest
```

## Limitaciones (honestas)

- Proyecto experimental v1: la clasificación es heurística por keywords, no semántica.
- No intercepta cada prompt por sí solo: Claude lo activa cuando la tarea coincide con su descripción, o al invocarlo explícitamente.
- Los precios de `index.json` son informativos (fuente OpenRouter), no una facturación real.

## Autor

**BELENTANI** — artista y cantante.
Neurodivergente, sin etiquetas: lo vivo como un don.
Hecho con alma brasileña 🇧🇷 desde Barcelona, mi casa.
IG: [@BELENTANI_](https://instagram.com/belentani_)

Licencia [MIT](LICENSE).
