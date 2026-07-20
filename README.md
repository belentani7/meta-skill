# Meta-Skill

![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Python: stdlib only](https://img.shields.io/badge/python-stdlib_only-blue) ![Deps: 0](https://img.shields.io/badge/dependencies-0-brightgreen)

> Router universal y guardia de tokens para Claude Code / Claude.ai.
> [Versao em Portugues (BR)](README.pt-BR.md)

## Que hace

Antes de que le pidas algo a Claude, este skill clasifica tu peticion por keywords (espanol e ingles), elige el modelo mas barato que pueda resolverlo, y si te pasas de presupuesto te frena el gasto. Todo local, sin APIs externas, sin tokens de mas.

```
tu prompt -> clasificar -> tier -> modelo -> skill -> ejecutar
                        si falla o cuesta mucho
                     fallback mas barato
```

Los nombres de los modelos no estan hardcodeados en el codigo. Viven en `index.json`, que es un archivo de datos. Asi cuando un modelo desaparezca o salga uno nuevo, solo tocas ese archivo y el resto sigue funcionando igual.

## Instalacion

**En Claude.ai:** descarga `meta-skill.skill` y usa "Save skill", o sube la carpeta desde Settings -> Capabilities.

**En Claude Code:** copia la carpeta `meta-skill/` a `~/.claude/skills/` (en Windows: `%USERPROFILE%\.claude\skills\`).

## Actualizar los modelos

```bash
python3 meta-skill/scripts/update_models.py
python3 meta-skill/scripts/update_models.py --validate
```

Es Python puro, sin dependencias. Consulta la lista publica de OpenRouter (no necesitas API key), busca el modelo mas nuevo por cada tier, y reescribe `index.json`. Si no hay internet, no toca nada y sigue funcionando con lo ultimo que tenia.

## Estructura

```
meta-skill/
  SKILL.md                 # el protocolo de enrutamiento
  index.json               # tareas, tiers, aliases, regex, precios
  scripts/
    update_models.py       # el que actualiza los modelos desde OpenRouter
tests/
  test_meta_skill.py       # tests, stdlib
.github/
  workflows/ci.yml         # CI en Linux y Windows
```

## Tests

```bash
python -m unittest
```

## Limitaciones

Esto es v1 y es experimental. La clasificacion es por keywords, no semantica. Claude activa el skill cuando la tarea coincide con lo que define, o si lo invocas directamente. Los precios que salen en index.json son orientativos, sacados de OpenRouter.

## Autor

**BELENTANI** — artista y cantante.
Neurodivergente, sin etiquetas, lo vivo como un don.
Hecho con alma brasileña desde Barcelona, mi casa.
IG: [@BELENTANI_](https://instagram.com/belentani_)

Licencia [MIT](LICENSE).
