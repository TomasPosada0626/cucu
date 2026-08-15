# Contribuir a CUCU

CUCU es un fork activo mantenido en solitario por [@TomasPosada0626](https://github.com/TomasPosada0626), a partir de un proyecto académico en equipo (ver [Colaboradores](README.md#colaboradores)). No es un proyecto con un equipo de revisión dedicado, pero los issues y PRs son bienvenidos — esto describe cómo hacerlos útiles.

## Antes de escribir código

Para un cambio chico (typo, bug obvio), andá directo al PR. Para algo más grande, abrí primero un [issue](https://github.com/TomasPosada0626/cucu/issues) describiendo qué querés cambiar y por qué, para no invertir tiempo en algo que no encaja con la dirección del proyecto (ver la [Wiki](../../wiki) para arquitectura y roadmap).

Para reportar una vulnerabilidad de seguridad, **no** abras un issue público — ver [SECURITY.md](SECURITY.md).

## Levantar el entorno local

Ver la sección "Ejecución Local con Docker Compose" del [README](README.md). En resumen: `cp .env.example .env`, ajustar los valores, `docker compose up --build -d`.

## Antes de abrir el PR

- **Lint:** el repo usa [ruff](pyproject.toml) (solo reglas de corrección real, no de estilo/formato — no hagas un reformateo masivo). Corré `ruff check .` o instalá el hook con `pre-commit install` para que corra solo en cada commit.
- **Type checking:** `mypy`, con alcance angosto a propósito — solo `domain/` y `application/` de cada app (Python puro, sin Django/DRF). Corré `mypy` en la raíz del repo; el mismo `pre-commit install` de arriba también instala este hook.
- **Tests:** `python manage.py test` para el monolito Django; `pytest` dentro de cada carpeta `*_microservice/` para los microservicios. El CI corre ambos automáticamente en cada PR — revisalo antes de pedir review.
- **Diseño:** si tocás templates/CSS, seguí [DESIGN.md](DESIGN.md) — es la fuente de verdad del sistema de diseño (colores, tipografía, radios, componentes). No introduzcas un hex o un radio nuevo sin buena razón.
- Un PR chico y enfocado es más fácil de revisar que uno grande con varios cambios sin relación.

## Estilo de commits

Mensajes en inglés, formato `tipo: descripción corta` (`fix:`, `feat:`, `docs:`, `test:`, `chore:`, `refactor:`, `security:`, `ci:`) — mirá `git log` para ejemplos. El cuerpo del commit explica el *por qué*, no solo el *qué*.
