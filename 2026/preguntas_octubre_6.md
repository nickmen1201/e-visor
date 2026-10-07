# Auditoría de los indicadores IND-15 a IND-22 — 6 de octubre de 2026

**Pregunta:** ¿los indicadores propuestos por los docentes (del 15 en adelante) se pueden calcular de verdad con nuestros datos, y se están calculando bien?

**Respuesta corta:** no es una alucinación. Los 8 indicadores se pueden plantear con los datos que hay (del 15 al 20) o están bien bloqueados a la espera de la frontera EPM (el 21 y el 22). El notebook los calcula como dice la ficha. Lo que encontré está en otra parte: una regla de lectura del IND-19 que los datos contradicen, dos promedios mal hechos en el dashboard (IND-17 e IND-18) y un medidor con datos inconsistentes (B8_CPA).

---

## Cómo se verificó

Ejecuté las celdas del notebook que calculan los IND-15 a 22 (`notebook_evisor_calculo.ipynb`, celdas 2–8 y 39–55) sobre `clean_etsmartmeter.csv`: 16 medidores, del 30-ene al 6-jun-2026, 42 692 filas medidor-hora. Después probé cada supuesto contra los datos.

Lo que sostiene todo resultó sólido:

- **Unidades y contador:** la energía que sale del contador (Δ`activeenergyimport`) cuadra con Σ(`activepower` × 1 h) a ±0,1 % en 15 de los 16 medidores. La excepción es B8_CPA (hallazgo 4).
- **Festivos 2026 (`FESTIVOS_COL_2026`):** revisé a mano las 18 fechas. La Pascua es el 5 de abril, así que Jueves y Viernes Santo caen el 2 y 3 de abril; Ascensión el 18 de mayo, Corpus el 8 de junio y Sagrado Corazón el 15 de junio. Los traslados a lunes están bien.
- **Mecánica:** las bases móviles por tipo de día, el `shift(1)` que deja fuera el día evaluado, la mediana en vez del promedio, la exigencia de lectura anterior a exactamente 1 h, todos los medidores del bloque presentes y 24 horas válidas por día hacen lo que dice la ficha.
- **Desfase menor:** como el CSV promedia el contador por hora, la energía etiquetada a la hora *t* corresponde aproximadamente al intervalo [t−0,5 h, t+0,5 h]. La correlación con la potencia es 0,999 contra (P_t + P_t−1)/2 y 0,991 contra P_t. Es un desfase de media hora, sin efecto práctico.

### Cobertura real de los datos

| Hecho | Detalle |
|---|---|
| Período | 2026-01-30 19:00 → 2026-06-06 02:00 |
| Meses parciales | Enero: 29 h por bloque · Junio: 99 h |
| Hueco grande | **29-mar 12:00 → 6-abr 19:00 (8 días, todos los medidores)**, que coincide con Semana Santa |
| Huecos de 22–25 h | 5-feb, 19-mar, 17-abr, 10-may, 1-jun |
| Bloque 15 | Sin datos hasta ~8 de marzo (37 días faltantes) |
| Días por tipo | 83 hábiles, 18 sábados, 20 domingos-festivos |

---

## Veredicto uno por uno

| IND | ¿Es posible? | ¿Bien calculado? | Problema |
|---|---|---|---|
| 15 DDCE horaria | Sí | Sí | Muy ruidoso por naturaleza |
| 16 DDCE diaria | Sí | Sí | No excluye las vacaciones, aunque su propia ficha lo exige |
| 17 P90/P95 | Sí | Notebook sí, **dashboard no** | Promedia meses parciales |
| 18 Participación | Sí | Notebook sí, **dashboard no** | Los bloques suman 103,6 % |
| 19 Persistencia | Sí | Sí | **La regla de lectura "6 de 7 = cambio sostenido" es falsa** |
| 20 Valor de referencia | Sí | Sí | Es demostrativo (tarifa de referencia), correcto y bien declarado |
| 21 Cobertura | Sí, con datos de EPM | Lógica correcta | Usa días incompletos |
| 22 Correlación | Sí, con datos de EPM | Lógica correcta | Igual que el 21, y le afecta más |

---

## Hallazgos, de más a menos grave

### 1. IND-19: el cálculo está bien, la interpretación no

La ficha (`indicadores_y_kpis.json`, PERS → `explicacion`) y el dashboard dicen que, por azar, 6 o 7 días de 7 por encima ocurre en ~6 % de las ventanas, y que por eso solo una racha de 6 o 7 apunta a un cambio sostenido. Ese 6 % sale de una binomial (7, 0,5), que supone que cada día es independiente del anterior. No lo son: si un bloque gasta de más un día, tiende a seguir así al siguiente.

| Días por encima (de 7) | Observado | Azar (binomial) |
|---|---|---|
| 0 | 3,5 % | 0,8 % |
| 1 | 4,9 % | 5,5 % |
| 2 | 12,2 % | 16,4 % |
| 3 | 18,1 % | 27,3 % |
| 4 | 23,5 % | 27,3 % |
| 5 | 19,9 % | 16,4 % |
| 6 | 11,6 % | 5,5 % |
| 7 | 6,3 % | 0,8 % |
| **≥ 6** | **17,9 %** | **6,25 %** |

- Base: 680 ventanas completas.
- La autocorrelación de un día al siguiente del signo de DDCE_d va de 0,10 a 0,49 según el bloque (0,49 en el B7, 0,40 en el B4).
- En 25 de las 60 fechas evaluables hay 3 o más bloques "en racha" a la vez (por ejemplo, 6 bloques el 2-mar).

**Consecuencia:** el dashboard pinta en rojo, como "cambio sostenido", algo que pasa casi una semana de cada cinco.
**Qué hacer:** recalibrar el umbral con la distribución observada (o con una base que tenga en cuenta la autocorrelación), o quitar la frase de la ficha y del pie del gráfico (`dashboard.py`, sección IND-19).

**Lo que sí está bien en el IND-19:** las 680 ventanas publicadas abarcan exactamente 7 días calendario. Aunque el `rolling(7)` cuenta filas y no días, la regla de "lectura anterior a 1 h" garantiza que el día posterior a cualquier hueco nunca queda completo, así que una ventana de 7 días evaluados no puede saltarse un hueco.

### 2. IND-18 en el dashboard: el promedio no suma 100 %

El dashboard calcula `groupby('bloque_lbl')['valor_num'].mean()`, o sea, promedia la participación de cada mes. Pero el Bloque 15 no existe hasta marzo y enero tiene 2 días, así que la suma da **103,6 %**.

| Bloque | Dashboard (media de meses) | Real del período | Diferencia |
|---|---|---|---|
| 7 | 18,45 % | 17,91 % | +0,54 pp |
| **15** | **10,88 %** | **8,26 %** | **+2,61 pp** |
| 17 | 2,88 % | 2,47 % | +0,41 pp |

**Qué hacer:** calcular la energía del bloque en todo el período dividida por la de los 16 medidores en el mismo período, no el promedio de los porcentajes mensuales. Además, en enero y febrero el denominador son 15 medidores (falta el B15), así que esos meses no se pueden comparar con los demás.

### 3. IND-17 en el dashboard: los meses parciales pesan igual que los completos

El gráfico muestra el "promedio de los meses del período". El rango por defecto arranca el 30-ene, así que enero (29 horas de un viernes por la noche y un sábado) cuenta lo mismo que un mes entero. Eso baja el P90:

| Bloque | P90 con todo el período | P90 feb–may | Sesgo |
|---|---|---|---|
| Ecovilla | 1,5 | 2,0 | −22,8 % |
| 9.1 | 58,8 | 67,3 | −12,6 % |
| 12 | 14,1 | 16,0 | −11,7 % |
| 9.2 | 49,2 | 55,3 | −11,0 % |
| 5 | 56,8 | 63,7 | −10,8 % |
| 4 | 42,1 | 47,0 | −10,3 % |
| 3 | 9,7 | 10,7 | −9,2 % |

**Qué hacer:** excluir los meses incompletos o ponderar por `n_horas`.

### 4. El medidor B8_CPA tiene datos inconsistentes

Su contador de energía registra un **7,4 % menos** de lo que implica su potencia; los otros 15 medidores cuadran a ±0,1 %.

- Por mes: ene 0,98 · feb 0,93 · **mar 0,78** · abr 0,98 · may 0,96 · jun 1,00.
- El contador casi no avanza mientras la potencia sigue apareciendo: **14 y 15 de marzo** (0 kWh contra ~7 kWh/día) y **16 a 18 de mayo**.
- No se puede saber cuál de las dos variables está mal.
- El filtro `_hora_limpia` no lo detecta, porque un contador quieto pasa como "0 kWh válido".
- Afecta a todo lo que use la energía del Bloque 8: IND-16, 18, 19, 20 y los KPIs de energía.

**Qué hacer:** agregar un chequeo de energía contra potencia por medidor y día, y confirmar con mantenimiento qué pasó con ese medidor.

### 5. Vacaciones: la ficha del IND-16 pide manejarlas y el código no lo hace

La nota de alcance del DDCE_D dice: *"marcar los días de receso o excluirlos del agrupador antes de emitir veredicto"*. No está implementado. Por ahora no hace daño:

- Semana Santa cae justo dentro del hueco de 8 días sin datos.
- Los datos terminan el 6-jun, y ya se ve el efecto: en junio solo el 13 % de los días queda por encima de lo esperado, porque el consumo cayó.

**Riesgo:** cuando lleguen julio y agosto, después del receso todos los bloques van a marcar desviaciones altas y rachas de 7 de 7 durante semanas.

### 6. IND-21 e IND-22 suman días incompletos

`submedido_diario` se arma con `daily_bloque` (la energía horaria sin depurar, `E_hora_wh`), así que va a incluir:

- días con cortes de ingesta de 22–25 h (un día de −95 % seguido de uno de +150 %);
- días parciales en el borde del hueco grande (29-mar, 6-abr);
- días sin todos los medidores (B15 en enero y febrero).

Para el total mensual del IND-21 importa poco; a la correlación diaria del IND-22 la deforma.
**Qué hacer:** usar el mismo filtro de días completos que ya tiene el DDCE (`daily_bloque_td`, solo días con todos los medidores y 24 h válidas).

---

## Matices menores (no invalidan nada)

- **Bases cortas:** el esperado de sábados y domingos es la mediana de solo 3–4 días (mediana efectiva: 3 para domingo-festivo, 4 para sábado). El 10,3 % de los días hábiles evaluados tiene menos de 10 días de base. Cumple la ficha, pero hace ruido.
- **Lunes y viernes juntos:** "hábil" mete en la misma base a lunes y viernes, que consumen menos que martes y jueves. Fracción de días por encima de lo esperado: lunes 42 %, viernes 46 %, miércoles 53 %, jueves 58 %, martes 60 %.
- **Festivos ≠ domingos:** el 1 y el 18 de mayo el campus consumió 4 181 y 4 018 kWh, contra una mediana de 3 530 kWh en domingo (+16 a +20 %). El 23 de marzo sí se pareció a un domingo. Contarlos como domingo los infla un poco y, con bases de 3–4 días, mueve el esperado de los domingos siguientes.
- **Ruido del IND-15:** en horario operativo, 9 de cada 10 horas caen entre −34 % y +67 %. En Ecovilla (esperado típico de 0,33 kWh/h), el 12 % de las horas supera ±100 %. Sirve para ver la distribución, no para leer horas sueltas, y así lo presenta el dashboard.
- **B9 en el IND-15:** el dashboard junta las horas de SFA1 y SFA2 en una sola distribución, en vez de calcular la desviación sobre la suma del bloque como en los demás bloques con varios medidores. Es una mezcla de dos distribuciones, no la del bloque.
- **Comentario contradictorio:** en el notebook, el comentario del IND-17 dice que sirve "para decir que una lectura es inusual", y la ficha dice lo contrario ("No detecta anomalías"). Solo hay que alinear el comentario.
- **IND-20:** las horas perdidas en huecos de más de 48 h (Semana Santa) no entran en el total, así que el valor de marzo y abril queda algo subestimado. Es un efecto de la cobertura, no del cálculo.

---

## Pendientes propuestos

1. Corregir la agregación del IND-18 en el dashboard (energía del período / total del período).
2. Corregir la agregación del IND-17 en el dashboard (excluir meses incompletos o ponderar por horas).
3. Recalibrar con los datos la regla de lectura del IND-19 y actualizar la ficha y el pie del gráfico.
4. Investigar B8_CPA con mantenimiento y agregar un chequeo de energía contra potencia.
5. Implementar el marcado de receso académico antes de que entren datos de julio y agosto.
6. Cuando llegue `frontera_epm.csv`, filtrar `submedido_diario` a días completos.
