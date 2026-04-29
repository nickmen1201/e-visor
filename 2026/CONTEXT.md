# e-Visor — Contexto del Proyecto

Indicadores energéticos y tableros de visualización para **Ecocampus UPB**, bajo criterios **ESG**.

## Objetivos

1. **Sistema de indicadores de sostenibilidad** — definir y calcular nuevos indicadores (eficiencia energética, sostenibilidad, impacto ambiental) que complementen los existentes, para evaluar el desempeño del Ecocampus y las estrategias implementadas.
2. **Estrategias de gestión energética** — medidas por segmento: optimización de intensidad energética, reducción de consumo por m², minimización del pico de demanda, integración de renovables.

## Fase actual

Desarrollo de tableros de visualización e indicadores energéticos (infraestructura ya operativa). Visualización por edificio, tipo de carga y zona; KPIs tradicionales (consumo/m², intensidad energética, pico de demanda) y nuevos orientados a sostenibilidad e impacto ambiental.

**Actividades:**
- A2.1 — Selección e instalación de herramientas de visualización
- A2.2 — Diseño de tableros interactivos por zona, carga y edificio
- A2.3 — Definición y cálculo de indicadores energéticos y de sostenibilidad
- A2.4 — Validación y ajuste con actores institucionales
- A2.5 — Documentación y manual de uso

## Marco institucional

**Grupos de interés priorizados:** estudiantes, empleados, sector empresarial, sector social, comunidad, arquidiócesis y diócesis, egresados, donantes y benefactores, sector académico e investigativo, sector público.

**Asuntos materiales priorizados:**
1. **Liderazgo consciente** — innovación, inversiones, creación de empleo y desarrollo.
2. **Regeneración y resiliencia** — energías renovables, biodiversidad, gestión de residuos.
3. **Interés colectivo** — voluntariado, salud mental y bienestar, diversidad e inclusión.

**ODS priorizados:** 3, 4, 6, 7, 9, 13, 16, 17.

**Ejes del departamento:**
1. **Flexibilidad energética** — renovables y tecnologías para integración.
2. **Territorios inteligentes** — ciudades inteligentes, Industria 4.0.
3. **Energía y sostenibilidad** — comunidades energéticas, nexo energía-agua-alimentos.

**Focos energéticos UPB:** territorios inteligentes; energía, desarrollo sostenible y cultura.

## Lineamientos de diseño

- **Dashboards:** claros, dinámicos, visualmente atractivos y comprensibles para el ciudadano común. Prioridad = **sencillez**. Visión: *"campus que hable en todos los rincones"*.
- **KPIs:** diagnóstico inmediato por área para líderes; revelar dolores y qué pasa en cada edificio para orientar decisiones basadas en datos.

## Restricciones técnicas

- **Sin automatización** por ahora — no es objetivo de esta fase.
- **Prioridad:** KPIs e indicadores con **validez académica** (aún en validación).
- **Granularidad espacial:** separados por **bloque/edificio**.
- **Temporalidad:** **1 hora**.


## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```