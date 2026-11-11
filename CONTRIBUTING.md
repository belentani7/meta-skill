# Contributing to Belentani Project
## Getting Started
Fork, clone, install (npm install / pip install -r requirements.txt), create branch.

## Development Workflow
Run lint/test/build. Follow conventional commits.

## Pull Request Process
Submit PR with description, link issues.

## Code Standards
Use ESLint/Prettier (JS) or ruff/black (Python). Write tests.

## Reporting Issues
Use .github/ISSUE_TEMPLATE/bug_report.yml.

<!-- repo-forge:contributing:inicio -->
# Contribuir

## Antes de tocar nada

1. Lee `BIBLIA.md` (doctrina del repositorio) y `plataforma/FICHA.md` (alcance permitido).
2. Ejecuta `python scripts/doctor.py` y guarda la salida: es la línea base.
3. Un cambio resuelve **un solo resultado verificable**.

## Cómo enviar

```bash
git checkout -b fix/<asunto-corto>
# ... cambio mínimo ...
python scripts/doctor.py
git commit -m "fix(alcance): <qué se arregla>"
```

Convención de commit: `type(scope): resumen` con tipos `feat|fix|docs|chore|refactor|test|perf`.

## Qué no se acepta

- Cambios que rompan una regla del catálogo sin justificar la excepción.
- Archivos generados a mano que el build regenera.
- Datos personales, credenciales o capturas de clientes.
- Promesas en el README que el código no cumpla.

<!-- repo-forge:contributing -->
<!-- repo-forge:contributing:fin -->
