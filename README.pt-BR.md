# Meta-Skill 🇧🇷

![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Python: stdlib only](https://img.shields.io/badge/python-stdlib_only-blue) ![Deps: 0](https://img.shields.io/badge/dependencies-0-brightgreen)

> Roteador universal e guardião de tokens para **Claude Code / Claude.ai** — a "mother skill".
> [Versión en Español](README.md)

## O que faz

Ativa ANTES de qualquer tarefa: classifica seu prompt (keywords PT/ES/EN), escolhe o **tier de modelo mais barato capaz** de resolver, delega ao skill instalado que melhor se encaixa e **freia o gasto** se passar do seu orçamento. O roteamento é 100% local — zero APIs, zero tokens extras.

```
prompt → classificar (keywords) → tier → modelo (aliases) → skill/diretiva → executar
                                   ↓ se falhar ou passar do orçamento
                                fallback mais barato
```

Os nomes dos modelos vivem só no `index.json` (dados, não código): feito para continuar funcionando quando os modelos de hoje já não existirem.

## Instalação

**Claude.ai / Cowork:** baixe `meta-skill.skill` (release) e use "Save skill", ou envie a pasta em Settings → Capabilities.

**Claude Code:** copie a pasta `meta-skill/` para `~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`).

## Atualizar o catálogo de modelos

```bash
python3 meta-skill/scripts/update_models.py            # atualiza index.json
python3 meta-skill/scripts/update_models.py --validate # checagem offline (CI)
```

Python puro (stdlib, zero dependências). Consulta a lista pública do OpenRouter (sem API key), escolhe o modelo de texto mais novo por tier via regex e reescreve só o `index.json` com **escrita atômica**. Sem internet, não toca em nada: segue funcionando offline. O tier local (`local_zero_token`) nunca se auto-atualiza.

## Estrutura

```
meta-skill/
├── SKILL.md                 # protocolo de roteamento (nunca contém nomes de modelos)
├── index.json               # tarefas, tiers, aliases, regex, preços — os dados
└── scripts/update_models.py # atualizador (OpenRouter, sem key, atômico)
tests/                       # unittest, stdlib
.github/workflows/ci.yml     # CI: tests + validate em Linux e Windows
```

## Tests

```bash
python -m unittest
```

## Limitações (honestas)

- Projeto experimental v1: a classificação é heurística por keywords, não semântica.
- Não intercepta cada prompt sozinho: o Claude o ativa quando a tarefa bate com a descrição, ou ao invocá-lo explicitamente.
- Os preços do `index.json` são informativos (fonte OpenRouter), não cobrança real.

## Autor

**BELENTANI** — artista e cantor.
Neurodivergente, sem rótulos: vivo isso como um dom.
Feito com alma brasileira 🇧🇷 de Barcelona, minha casa.
IG: [@BELENTANI_](https://instagram.com/belentani_)

Licença [MIT](LICENSE).
