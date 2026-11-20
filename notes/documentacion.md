# Observabilidad con Datadog — Documentación del curso

Este documento recoge, ordenado por temas, lo que se trabajó en las sesiones del curso
(notas `day1.md` a `day4.md`). También añade lo que faltaba para que cada tema quede completo.

Hay dos tipos de recuadro:

> **Complemento.** Contenido que no se dio en clase y que se añade aquí para cerrar el tema.

> **Precisión.** Una corrección o un matiz sobre algo que se dijo en clase de forma simplificada.

La aplicación de prácticas (la «tienda») y dónde se configura cada dato se explican en
[`tienda/README.md`](../tienda/README.md). Este documento se queda en los conceptos.

---

## Índice

1. [Monitorización y observabilidad](#1-monitorización-y-observabilidad)
2. [Datadog como plataforma](#2-datadog-como-plataforma)
3. [Los tipos de telemetría](#3-los-tipos-de-telemetría)
4. [Arquitectura: cómo llegan los datos a Datadog](#4-arquitectura-cómo-llegan-los-datos-a-datadog)
5. [El entorno del curso](#5-el-entorno-del-curso)
6. [Etiquetado y Unified Service Tagging](#6-etiquetado-y-unified-service-tagging)
7. [Versionado: qué versión es «la versión»](#7-versionado-qué-versión-es-la-versión)
8. [El coste: almacenamiento, agregación y cardinalidad](#8-el-coste-almacenamiento-agregación-y-cardinalidad)
9. [Métricas](#9-métricas)
10. [Logs](#10-logs)
11. [Trazas y APM](#11-trazas-y-apm)
12. [RUM: la experiencia del usuario real](#12-rum-la-experiencia-del-usuario-real)
13. [Tests sintéticos](#13-tests-sintéticos)
14. [Eventos](#14-eventos)
15. [Estadística para construir dashboards](#15-estadística-para-construir-dashboards)
16. [Diseño de dashboards](#16-diseño-de-dashboards)
17. [Monitores, notificaciones y automatización](#17-monitores-notificaciones-y-automatización)
18. [SLI, SLO, SLA y presupuesto de error](#18-sli-slo-sla-y-presupuesto-de-error)
19. [CI/CD, DORA y plataforma de desarrollo](#19-cicd-dora-y-plataforma-de-desarrollo)
20. [Memoria en aplicaciones Java sobre Kubernetes](#20-memoria-en-aplicaciones-java-sobre-kubernetes)
21. [Glosario](#21-glosario)

---

## 1. Monitorización y observabilidad

| | Monitorización | Observabilidad |
|---|---|---|
| Conocimiento | **A priori**: decido de antemano qué puede fallar y qué es importante | **A posteriori**: entender qué pasa aunque no se hubiera previsto |
| Pregunta | **¿Qué** está roto? | **¿Por qué** está (o se ha) roto? |
| Herramienta típica | Medidas a lo largo del tiempo y alertas con umbrales | Correlación de métricas, logs, trazas y eventos |

Ejemplos de monitorización con umbrales:

- Heap de la JVM por encima del 80 %.
- Recolecciones de basura de la generación vieja (no solo del *eden*) con mucha frecuencia.
- Porcentaje de respuestas 5XX por encima del 3 %.

La monitorización es un **subconjunto** de la observabilidad. Detecta los problemas conocidos.
La observabilidad permite además diagnosticar los que nadie había previsto.

---

## 2. Datadog como plataforma

Datadog es una plataforma de observabilidad que se ofrece como **SaaS**. En nuestras máquinas solo
se instalan **agentes**, que recogen los datos y los envían. Almacenamiento, procesado y consulta
ocurren en los servidores de Datadog. Nosotros usamos el site europeo, `datadoghq.eu`.

Dentro hay muchas herramientas, y la empresa sigue ampliándolas a un ritmo muy agresivo. Cada una
equivale a un producto de código abierto:

| Área | Datadog | Equivalente libre habitual |
|---|---|---|
| Métricas de infraestructura y de aplicación | Infrastructure, Metrics | Prometheus + Grafana |
| Logs | Log Management | ELK (Elasticsearch, Logstash, Kibana), Loki, OpenSearch |
| Trazas distribuidas | APM | Jaeger, OpenTelemetry |
| Experiencia del usuario en el navegador o el móvil | RUM, Session Replay | — |
| Pruebas automáticas con robots | Synthetic Monitoring | Selenium, Cypress, Playwright (fuera de producción) |
| Base de datos | Database Monitoring (DBM) | pg_stat_statements + paneles |
| Pipelines y tests | CI Visibility, Test Optimization | Paneles del propio CI |

**El valor no está en tener todos los datos en un mismo sitio, sino en poder pasar de unos a otros.**
Un recorrido típico de diagnóstico:

1. Un usuario ve un error en el navegador (RUM).
2. De ahí se salta a la petición que llegó al backend (traza).
3. Se ven los logs que generó esa petición (logs con el mismo `trace_id`).
4. Se ve el recorrido completo de la petición y dónde se fue el tiempo (spans).
5. Se ven CPU, memoria, disco y red del pod y del nodo en ese mismo instante (métricas).

Todo ese encadenamiento descansa en un mecanismo: el **etiquetado** (sección 6).

---

## 3. Los tipos de telemetría

### Métrica

Un **dato cuantitativo** asociado a un instante de tiempo, por ejemplo el uso de CPU, las peticiones
por segundo o los pedidos creados.

### Log

Un **registro de algo que ocurrió** en un momento dado. Normalmente es texto **estructurado o
semiestructurado** y sirve para dar contexto a lo que está pasando.

Aquí «log» no es el fichero, sino **cada línea**. Cada una lleva un timestamp y campos adicionales:
nivel, origen, etiquetas, etc.

> Una consulta a Postgres registrada en un log: la consulta es la actividad. La fecha, quién la
> lanzó, cuánto tardó y cómo terminó son atributos. Del tiempo de respuesta se puede sacar después
> una métrica.

### Traza

Agrupa todo lo que ocurrió en el sistema a causa de **una misma operación**, enlazado por un
identificador común, el `trace_id`.

Un usuario pulsa un botón en el frontal y se genera el `trace_id`. La petición llega a un endpoint
del backend, que lanza una consulta a la base de datos y deja un mensaje en Kafka. Media hora después,
un consumidor lee ese mensaje y sigue procesándolo. Todo lleva el mismo `trace_id`, así que se puede
reconstruir la secuencia completa y compararla con lo que pasaba en ese momento en la CPU, la memoria
o los servicios vecinos.

La traza se divide en **spans** (sección 11).

### Evento

También es algo que ocurre en un instante, pero se diferencia del log en dos cosas:

- **Frecuencia.** Los logs registran actividad de alta frecuencia. Los eventos son esporádicos.
- **Importancia.** Los eventos marcan sucesos relevantes que se quieren tener controlados, como un
  despliegue de la versión 1.2.7, un reinicio o el lanzamiento de una campaña promocional.

Los eventos sirven sobre todo para el **análisis de impacto**: ver qué pasó con la latencia, los
errores o la disponibilidad después de un cambio.

> **Complemento.** Datadog recoge dos tipos de datos más:
> - **Perfiles (Continuous Profiler).** Qué método o línea de código gasta CPU, memoria o tiempo de
>   bloqueo. En la tienda se activa con `DD_PROFILING_ENABLED=true`.
> - **Sesiones de RUM.** Vistas, acciones, errores y recursos cargados por el navegador del usuario
>   (sección 12).

---

## 4. Arquitectura: cómo llegan los datos a Datadog

```
 Navegador del usuario                 Clúster de Kubernetes
 ─────────────────────                 ──────────────────────────────────────────────────
 SDK de RUM                            App (shop-api)  ──trazas (8126)──┐
  · genera el trace_id ───cabeceras──▶  · tracer Java   ──métricas DogStatsD (8125)──┐
  · clics, vistas, errores              · logs por stdout ─┐                          │
         │                                                 ▼                          ▼
         │                             Agente de Datadog (uno por nodo, DaemonSet)
         │                              · lee los logs de los contenedores
         │                              · métricas del nodo, contenedores y procesos
         │                              · checks (http_check, postgres…)
         │                              · agrega, pone en cola, reintenta
         │                                        │
         ▼                                        ▼
 ───────────────────────────── Servidores de Datadog ──────────────────────────────
   Ingesta → pipelines de procesado (parseo, enriquecido, etiquetado) → índices y almacenamiento
```

### El agente

- En Kubernetes se despliega **un agente por nodo**, como DaemonSet.
- Recoge métricas del nodo y de los contenedores, lee los logs y recibe las trazas y métricas que
  le manda la aplicación.
- Puede **filtrar y agregar** antes de enviar. Así se manda menos a Datadog, que cobra por recibir
  y por procesar.
- Gestiona **colas y reintentos**: si se corta la conexión con Datadog, guarda los datos y los reenvía
  después.
- La aplicación le envía las métricas con un **cliente no bloqueante** (`NonBlockingStatsDClient`,
  UDP), para que el envío nunca frene la aplicación.

> **Complemento.** Hay más piezas en el despliegue de Kubernetes:
> - **Cluster Agent.** Un único pod por clúster. Habla con la API de Kubernetes en nombre de todos los
>   agentes de nodo, ejecuta los checks a nivel de clúster y sirve métricas para el autoescalado (HPA).
> - **kube-state-metrics.** Viene incluido en el chart de Helm y da el estado de los objetos: réplicas
>   deseadas y disponibles, reinicios, pods pendientes, etc.
> - **Autodiscovery.** El agente detecta los contenedores y les aplica la configuración que indican
>   las **anotaciones** del pod (`ad.datadoghq.com/<contenedor>.logs`, `.checks`). Variables como
>   `%%host%%` se sustituyen por la IP real del pod.
> - **Puertos.** DogStatsD (métricas propias) escucha en el **8125/UDP** y APM (trazas) en el **8126/TCP**.

### RUM no pasa por el agente

El SDK de RUM se ejecuta en el navegador y envía **directamente a Datadog**. No tenemos ningún
control sobre ese dispositivo: no sabemos cómo va de memoria ni vemos su consola.

### Observability Pipelines

Datadog cobra por recibir los datos y por procesarlos en sus pipelines de ingesta. Para reducir lo
que se envía se puede montar un **Observability Pipelines Worker** en nuestra infraestructura (por
ejemplo, en un namespace propio). Filtra, agrega, enmascara y enruta antes de enviar.

Ocupa el mismo lugar que Logstash, Data Prepper o un Fluentd con preprocesado.

---

## 5. El entorno del curso

- Clúster de Kubernetes de **5 nodos**, con un agente de Datadog en cada uno.
- Aplicación de demo, la **tienda**:
  - `shop-web`: frontal en JavaScript servido por nginx, con el SDK de RUM.
  - `shop-api`: backend en Java con Spring Boot, instrumentado con el tracer de Java (`-javaagent`).
  - `shop-db`: PostgreSQL, con Database Monitoring.
- `env`: `course`.
- Robot de carga: `tienda/generate-load.sh`.

Todos los asistentes trabajan en la misma organización de Datadog. Por eso se pone el **nombre propio
como prefijo** en todo lo que se crea: dashboards, monitores, SLOs y tests.

---

## 6. Etiquetado y Unified Service Tagging

Datadog usa **etiquetas (tags)** de forma intensiva. Cada métrica, log, traza o evento lleva etiquetas
como servicio, entorno, host, contenedor o usuario. Las etiquetas permiten filtrar, agrupar y, sobre
todo, **correlacionar**.

Podemos definir etiquetas propias, y suele interesar hacerlo. Pero hay tres reservadas que forman el
**Unified Service Tagging (UST)**:

| Etiqueta | Significado | En la tienda |
|---|---|---|
| `env` | Entorno | `course` |
| `service` | Componente **lógico** de la aplicación | `shop-web`, `shop-api`, `shop-db` |
| `version` | Versión del servicio | `1.0.5`, … |

Datadog usa estas tres en todas sus pantallas para enlazar datos. Si no coinciden entre métricas,
logs y trazas, el salto de un dato a otro deja de funcionar, y lo hace **sin dar error**.

Buena práctica: escribir los valores en **un solo sitio** (las labels `tags.datadoghq.com/*` del pod)
y que las variables `DD_ENV`, `DD_SERVICE` y `DD_VERSION` se lean de ahí. Así lo hace la tienda.

> **Complemento.** Más buenas prácticas de etiquetado:
> - Formato `clave:valor`, en minúsculas y sin espacios.
> - Pactar un vocabulario común (`team`, `domain`, `tier`…) y que nadie invente claves por su cuenta.
>   Una etiqueta con dos nombres equivale a dos etiquetas distintas.
> - Vigilar la **cardinalidad** (sección 8): nunca se etiqueta una métrica con identificadores únicos.

---

## 7. Versionado: qué versión es «la versión»

### SemVer

Formato `vA.B.C`:

| Parte | Sube cuando… |
|---|---|
| **A** (major) | Hay cambios que **rompen la compatibilidad** |
| **B** (minor) | Se añade funcionalidad compatible, o se marca algo como **obsoleto** (deprecated) |
| **C** (patch) | Se corrige un bug sin cambiar la interfaz |

### Infraestructura como código (IaC)

IaC no consiste en tener la infraestructura escrita en ficheros. Consiste en **tratarla como código**,
y lo primero es **someterla a control de versiones**.

> La aplicación v1.0.0 necesita una base de datos: es la infraestructura v1.0.0. La aplicación v2.0.0
> añade Redis como caché, y la infraestructura pasa a v1.1.0. La aplicación v1.0.0 funciona sobre las
> dos versiones de la infraestructura, pero la v2.0.0 solo funciona sobre la v1.1.0.

### Kubernetes

Orquestar contenedores es una parte pequeña de lo que hace Kubernetes. Lo fundamental es que permite
**definir y operar entornos de producción con lenguaje declarativo**.

Los manifiestos **son la infraestructura**, una infraestructura virtualizada:

- `Service`: balanceadores de carga.
- `Ingress`: reglas de proxy inverso.
- `NetworkPolicy`: reglas de cortafuegos.
- `Deployment`, `StatefulSet` y `DaemonSet`: plantillas de pods con sus límites de CPU, memoria y volúmenes.
- `ConfigMap`, `Secret` y `PVC`: la configuración y el almacenamiento.

En un entorno tradicional se versionan por separado la infraestructura, la aplicación y la
**configuración del despliegue**. Por ejemplo, cambiar de servidor de correo no toca la aplicación
ni la infraestructura, pero sí la configuración, y conviene poder dar marcha atrás.

En Kubernetes las tres piezas viven en los mismos manifiestos: la versión de la aplicación (el tag
de la imagen), la configuración y la infraestructura.

Con **Helm** (o **Terraform**), la versión de lo desplegado depende a la vez de la **versión del chart**
(o del script) y de la **versión de los parámetros** que recibe. Los parámetros cambian entre entornos:
otro Ingress, otra URL de un servicio externo en el ConfigMap…

### Qué versión se pone en la etiqueta `version`

Hay que decidirlo. Es una decisión de diseño:

- **Versión de la aplicación.** Permite comparar la misma versión entre entornos. No distingue dos
  despliegues de la misma versión, por ejemplo cuando solo se ha subido la memoria.
- **Versión del despliegue o de la infraestructura.** Distingue esos cambios, pero deja de identificar
  el código.

Recomendación:

- Guardar **todas** las versiones, cada una en su etiqueta: aplicación, despliegue e infraestructura.
- Elegir con criterio cuál ocupa `version`, que es la única que Datadog muestra en todas sus pantallas.
- Registrar cada despliegue como **evento** (sección 14). El evento aparece como una línea vertical
  en todas las gráficas y permite ver el antes y el después.

> **Complemento.** Un criterio habitual es poner en `version` la **versión de la imagen o el commit**
> que se despliega, porque es lo que usa APM para el seguimiento de despliegues: comparar errores y
> latencia entre versiones. Los cambios que no son de código (configuración, recursos) se marcan con
> eventos y con etiquetas propias, como `deploy_version` o `chart_version`.

---

## 8. El coste: almacenamiento, agregación y cardinalidad

**Datadog es caro**, y lo que más encarece es el volumen de datos.

### El almacenamiento en producción no es barato

Un disco doméstico de 2 TB cuesta unos 95 €. En una empresa el coste se multiplica:

- Hace falta calidad de servidor, porque el uso es continuo: ×5.
- Cada dato se guarda en al menos 3 sitios: ×3.
- Se hacen copias de seguridad: ×3.

En total sale del orden de **×45**, unos 4.000 € por esos mismos 2 TB, y con volúmenes de datos mucho
mayores que en casa. Datadog, como cualquier nube, cobra el almacenamiento en consecuencia.

### Datos exactos, muestreados o agregados

- **Exacto.** Una consulta tardó 345 ms.
- **Muestreado.** Se lee el heap cada 10 s. Los datos son exactos, pero se desconoce lo que pasó
  entre lectura y lectura.
- **Agregado en origen.** Se envía la media de cada intervalo. Ocupa mucho menos, pero **las medias
  no se pueden volver a agregar**:

  > Intervalo 1: media de 100 ms con 10 datos. Intervalo 2: media de 200 ms con 1 dato.
  > La media conjunta no es 150 ms, sino (10·100 + 1·200) / 11 = **109,09 ms**. Para calcularla hacen
  > falta los recuentos, o los datos sueltos.

Agregar en el agente abarata, pero **hay que entender qué análisis se pierden**.

> **Complemento.** La **cardinalidad** es el mayor factor de coste en métricas.
>
> Datadog factura las métricas propias por **combinación única de nombre de métrica y valores de
> etiqueta**. Por ejemplo, `shop.orders.created` con `category` (5 valores) y `status` (3 valores)
> son hasta 15 series. Si se añade `customer_id` con 10.000 clientes, pasan a ser 150.000 series.
>
> Regla: en las métricas, solo etiquetas con **pocos valores posibles**. Los identificadores (cliente,
> pedido, petición) van en **trazas y logs**, que no se facturan por cardinalidad.
> La tienda lo hace así: `category` en la métrica y `usr.name` en el span.
>
> El mismo criterio aplica a logs y trazas. Se paga por **ingerir** y por **indexar o retener**, y son
> conceptos distintos (secciones 10 y 11).

---

## 9. Métricas

### De dónde salen

- **Automáticas.** El agente del nodo aporta CPU, memoria y red de nodos y contenedores. El tracer de
  Java aporta peticiones, errores, latencia, heap y GC. Las integraciones (Postgres, nginx…) aportan
  las suyas.
- **Propias (custom).** Las métricas de negocio las tiene que pedir alguien y programarlas un
  desarrollador. Datadog no sabe qué es un pedido pagado. Se envían por DogStatsD, como en
  [`Metrics.java`](../tienda/app/src/main/java/com/course/shop/service/Metrics.java).

### Dónde se instrumentan

Las métricas, los logs y los eventos **de negocio** van en la **capa de servicio**, donde vive la
lógica de negocio. No van en los controladores, ni en los repositorios, ni en un aspecto genérico.

### Tipos de métrica

| Tipo | Llamada | Qué representa | ¿Se puede sumar a lo largo del tiempo? | Ejemplo de la tienda |
|---|---|---|---|---|
| **Count** | `incrementCounter` | Cuántas veces ocurre algo en un intervalo | Sí, en todas las dimensiones | `shop.orders.created` por `category` y `status` |
| **Gauge** | `gauge` | Un valor en un instante; se guarda el último del intervalo | **No** a lo largo del tiempo; sí en otras dimensiones | `shop.stock.units` por `product` |
| **Histogram** | `histogram` | Distribución de valores, resumida **en el agente** | Solo los agregados calculados | `shop.payment.duration` |
| **Distribution** | `distribution` | Distribución de valores, resumida **en el servidor** a nivel global | Percentiles exactos sobre cualquier agrupación | `shop.orders.value` |

**Count.** Con el número de pedidos etiquetado por fecha, producto y cliente se puede preguntar
cuántos pedidos hubo por intervalo, por producto o por cliente.

**Gauge.** No tiene sentido sumar el stock del día 17 con el del día 18. Sí tiene sentido sumar el
stock de un mismo producto en todos los almacenes en un instante dado.

### Histogram y distribution

Supongamos los tiempos de diez pagos: 2,5 · 3,1 · 1,8 · 2,2 · 3,0 · 2,7 · 2,9 · 3,2 · 2,6 · 3,3 segundos.

- **Histogram.** El agente agrupa los valores de cada intervalo de envío (10 s por defecto) y manda
  **solo unos agregados fijos**, cada uno como una métrica aparte: `.avg`, `.count`, `.median`,
  `.95percentile` y `.max`. Ya no se puede calcular otro percentil, ni el p95 de todos los hosts juntos.
  Combinar los p95 de varios agentes no da el p95 global: es el mismo problema que el de las medias.
- **Distribution.** El agente resume los valores en una estructura estadística (un *sketch*) que se
  combina **en el servidor**. Así se pueden calcular percentiles **globales** sobre cualquier
  combinación de etiquetas y en cualquier ventana de tiempo.

> **Precisión.** En clase se explicó que la *distribution* guarda cada punto individual. No es
> exactamente así: guarda un resumen compacto (DDSketch) con un error relativo garantizado de
> alrededor del 1 %. Para el análisis el efecto es el mismo, porque cualquier percentil es fiable a
> nivel global. Lo que no permite es recuperar los valores uno a uno.
>
> Los percentiles de una distribution hay que **activarlos** en la configuración de la métrica, y
> cada agregación y combinación de etiquetas cuenta para la factura.

> **Precisión.** En la tienda, `payment.duration` se envía como métrica por motivos didácticos, para
> tener un ejemplo de histogram. Conceptualmente es un **span**, y APM ya calcula su latencia.

> **Complemento.** DogStatsD tiene dos tipos más:
> - **Set**: cuenta **valores únicos** en el intervalo. Sirve, por ejemplo, para los «usuarios únicos
>   activos» que salieron en el diseño del dashboard de operaciones.
> - **Rate**: un count normalizado por segundo.
>
> Las métricas se conservan 15 meses.

---

## 10. Logs

### Logs en contenedores

En un contenedor **no hay fichero de log**. El log es la **salida estándar y la salida de error del
proceso principal**, el que tiene PID 1 y cuya vida marca la del contenedor. Muchas imágenes redirigen
sus ficheros de log a stdout para que el agente los recoja.

El agente lee lo que escribe cada contenedor. La anotación del pod le indica de qué tipo es el log
(`source`), y con eso elige el pipeline de parseo:

```yaml
ad.datadoghq.com/shop-api.logs: '[{"source":"java"}]'
```

Las trazas de pila de Java ocupan varias líneas. Para que lleguen como un solo log se usa una regla
**multilínea**: «empieza un log nuevo cuando la línea empieza por una fecha».

```yaml
ad.datadoghq.com/showroom-service.logs: |-
  [{
    "source": "showroom-service",
    "service": "showroom-service",
    "log_processing_rules": [{
      "type": "multi_line",
      "name": "log_start_with_date",
      "pattern": "\\d{4}-(0?[1-9]|1[012])-(0?[1-9]|[12][0-9]|3[01])"
    }]
  }]
```

### Logs sin pasar por disco

Cuando no queda más remedio que escribir en fichero (fuera de contenedores o con herramientas
heredadas), escribir en disco tiene dos problemas:

- La escritura es lenta.
- Si el disco se llena hay que rotar, y si se rota antes de enviar, **se pierden logs**.

El patrón recomendado es este:

1. La aplicación escribe en un volumen en **memoria**: un `emptyDir` con `medium: Memory`, montado
   en la ruta de logs.
2. Un recolector lo lee y lo envía (Fluentd, Filebeat, el agente de Datadog).

La aplicación recibe la confirmación enseguida y se olvida del envío.

### Estandarizar los logs: un requisito, no una decisión del desarrollador

Hoy nadie decide qué sale en los logs. El desarrollador escribe lo que le sirve para depurar, y eso
está bien para él. Pero los logs son también fuente de **información de negocio**, y de ella salen
los dashboards:

- Nueva venta.
- Registro de usuario.
- Inicio de sesión.
- Pago fallido.
- Carrito abandonado.

Por eso, entre los **requisitos no funcionales**:

- **Qué** logs de negocio se generan.
- **Con qué estructura**, como un contrato o una API. Si el formato cambia, el pipeline de ingesta
  se rompe.

Cada línea lleva tres cosas:

- Los datos propios del hecho.
- Las etiquetas UST y los identificadores de traza, inyectados automáticamente con
  `DD_LOGS_INJECTION=true`.
- Etiquetas específicas de ese registro.

Formato de la tienda:

```
2024-06-15 10:00:00.123 INFO  [http-nio-8080-exec-1] [dd.service=shop-api dd.env=course dd.version=1.0.5 dd.trace_id=… dd.span_id=…] c.c.s.service.OrderService - Pedido creado …
```

### Pipelines de ingesta

Los logs se procesan en Datadog: se parsean, se extraen atributos, se reasignan el estado y la fecha,
y se enriquecen. Regla de *Grok Parser* para el formato de la tienda:

```
shop_line %{date("yyyy-MM-dd HH:mm:ss.SSS"):timestamp} %{word:level}\s+\[%{notSpace:logger.thread_name}\] \[dd.service=%{notSpace:dd.service} dd.env=%{notSpace:dd.env} dd.version=%{notSpace:dd.version} dd.trace_id=%{regex("[^ ]*"):dd.trace_id} dd.span_id=%{regex("[^ \\]]*"):dd.span_id}\] %{notSpace:logger.name} - %{data:msg}
```

Después del Grok Parser se añaden remapeadores para que Datadog use los campos extraídos:

- *Date Remapper* sobre `timestamp`.
- *Status Remapper* sobre `level`.
- *Trace Id Remapper* sobre `dd.trace_id`.
- *Message Remapper* sobre `msg`.

> **Complemento.** Para trabajar con logs en Datadog:
> - **Atributos, facets y measures.** Un atributo extraído solo sirve para filtrar y agrupar si se
>   declara como **facet** (cualitativo) o como **measure** (cuantitativo, con unidad). Es la
>   distinción estadística de la sección 15 aplicada a los logs.
> - **Ingerir e indexar son cosas distintas** («Logging without Limits»). Se puede ingerir todo y
>   **indexar** solo una parte con filtros de exclusión, por ejemplo descartar los DEBUG o los
>   healthchecks. Se paga mucho más por indexar.
> - **Métricas a partir de logs.** Se pueden generar métricas desde los logs **antes** de indexarlos:
>   se cuentan los pagos fallidos aunque esos logs no se guarden, y la métrica se conserva 15 meses.
> - **Archivos.** Los logs se pueden copiar a un almacenamiento barato (S3, GCS, Azure Blob) y
>   recuperarlos (*rehydrate*) cuando hagan falta.
> - **Datos sensibles.** El *Sensitive Data Scanner* enmascara tarjetas, correos o DNIs en la ingesta.
>   Mejor todavía es no escribirlos en el log.

### Del dato operativo al análisis de negocio

Los logs y las métricas de negocio sirven para la operación inmediata. El análisis histórico de
negocio sigue su propio camino:

```
BD de producción → ETL → data lake → ETL → data warehouse → BI / reporting
```

---

## 11. Trazas y APM

### Conceptos

- **Traza.** El intervalo de tiempo durante el cual se sigue una petición o transacción a través de
  los componentes del sistema. Se identifica con un `trace_id`.
- **Span.** Una unidad de trabajo dentro de la traza: un endpoint, un método de servicio, una consulta.
  Tiene su `span_id`, nombre, duración y metadatos. Los spans forman un **árbol**, de modo que un span
  tiene spans hijos.

```
Navegador (RUM)   T1 ──────────────────────────────────────── T2   traza
Controlador            T1 ───────────────────────────── T2         span
Servicio                  T1 ────────── T2  T1 ─────── T2          spans
Repositorio                  T1 ──── T2                            span
```

La estructura la decide desarrollo. Las trazas son una herramienta sobre todo **técnica**: a negocio
no le interesan. Se colocan spans en controlador, servicio y repositorio según dónde se quiera
analizar el tiempo.

### Propagación

1. El SDK de RUM genera el `trace_id` y lo envía en las cabeceras de la petición. Lo hace solo para
   las URL incluidas en `allowedTracingUrls`.
2. El backend continúa la misma traza.
3. Si el backend consulta la base de datos, el `trace_id` viaja como **comentario en el SQL**
   (`DD_DBM_PROPAGATION_MODE=full`). Así DBM enlaza cada consulta con la traza que la lanzó.
4. Los logs llevan el `trace_id` en cada línea (`DD_LOGS_INJECTION=true`). Por eso se puede pasar de
   una traza a sus logs.

### Instrumentación

- **Automática.** El tracer de Java (`-javaagent:dd-java-agent.jar`) traza las peticiones HTTP, JDBC
  y los clientes HTTP sin tocar el código.
- **Manual.** Un paso de negocio como span propio, con `@Trace(operationName = "payment.charge")`, y
  etiquetas de negocio en el span con `Span.current().setAttribute(...)`, usando la API de
  OpenTelemetry.

> **Complemento.**
> - **Conceptos de APM.** Un **service** contiene **operaciones** (`servlet.request`,
>   `postgresql.query`…), y cada operación tiene **recursos**: el endpoint concreto
>   (`POST /api/orders`) o la consulta normalizada.
> - **Métricas de traza.** APM calcula `hits`, `errors` y latencia (`trace.<operación>.*`) sobre el
>   **100 % del tráfico**, aunque luego no se guarden todas las trazas. Son la base de los SLOs de
>   disponibilidad y latencia del backend.
> - **Muestreo.** Hay dos niveles: lo que se **ingiere** (en el tracer, con `DD_TRACE_SAMPLE_RATE`
>   o reglas) y lo que se **retiene** e indexa durante 15 días (filtros de retención). En la demo se
>   ingiere el 100 %. En producción se ajusta según volumen y coste, y Datadog conserva siempre
>   las trazas con error y las poco frecuentes.
> - **Seguimiento de despliegues.** Con la etiqueta `version` bien puesta, APM compara errores y
>   latencia entre versiones automáticamente.

---

## 12. RUM: la experiencia del usuario real

Parte de la aplicación se ejecuta en el dispositivo del usuario (móvil, portátil, tablet), sobre el
que no tenemos control. **RUM** (Real User Monitoring) es un SDK en JavaScript que la propia página
carga. Captura:

- **Vistas** (páginas o pantallas) y su rendimiento: tiempos de carga y Core Web Vitals.
- **Acciones** del usuario, como los clics. Se les pone nombre legible con `data-dd-action-name`.
- **Errores** de JavaScript y **recursos** cargados.
- El **usuario**, con `DD_RUM.setUser(...)`.
- **Session Replay**: la reconstrucción de lo que el usuario vio en pantalla.

El SDK envía directamente a Datadog y **genera el `trace_id`** que enlaza el frontal con el backend.

**Limitación clave.** Si la web no carga, el script de RUM tampoco se ejecuta, y no queda constancia
de los usuarios que no pudieron entrar. Por eso **la disponibilidad del frontal no se mide con RUM,
sino con tests sintéticos**. RUM mide **el impacto en los usuarios reales**, por ejemplo con vistas
sin errores.

> **Complemento.**
> - **Privacidad.** `defaultPrivacyLevel` controla qué se graba en Session Replay. Con `mask` o
>   `mask-user-input` no se envían los datos tecleados. Es un punto a revisar con protección de datos
>   (RGPD), igual que el consentimiento de cookies.
> - **Muestreo.** `sessionSampleRate` y `sessionReplaySampleRate` controlan qué porcentaje de
>   sesiones se graba. RUM se factura por sesión y el replay se paga aparte.

---

## 13. Tests sintéticos

Son robots que ejecutan operaciones contra el sistema **en producción y de forma continua**: «un
robot comprando un coche de pega».

Responden a la pregunta de si **la operación funciona**, que es distinta de si está ocurriendo.
Ver que se venden coches es una medida indirecta y pobre. Si no se vende ninguno, no se sabe si es
porque el proceso falla o porque nadie compra.

Hay solape con las pruebas de sistema que se escriben antes de pasar a producción (Selenium, Cypress,
Playwright). Interesa reutilizar los tests de Datadog también en el pipeline de CI/CD.

> **Complemento.** Tipos de test:
> - **API**: HTTP, SSL, DNS, TCP, gRPC… Comprueban códigos de respuesta, contenido y tiempos.
> - **API multipaso**: encadenan peticiones y reutilizan valores, como un token de login.
> - **Browser**: un navegador real recorre la web. Sirven, por ejemplo, para un login con
>   redirecciones a un IAM: frontal → 302 al IAM → formulario → 302 de vuelta al frontal.
> - **Ubicaciones**: gestionadas por Datadog (en varias regiones) o **privadas**, para probar
>   servicios internos sin exponerlos.
> - **En CI**: `datadog-ci synthetics run-tests` ejecuta los tests en el pipeline y lo detiene si fallan.

### Healthcheck del backend: quién lo comprueba

El endpoint `/actuator/health` (que incluye el estado de Postgres) puede comprobarse desde tres sitios:

| Quién | Por dónde entra | Qué detecta |
|---|---|---|
| Test sintético | Por el Ingress y el balanceador | Si el servicio responde **para el usuario** |
| Kubernetes (sondas liveness/readiness) | Directo al pod | Lo usa para reiniciar el pod o sacarlo del balanceo |
| Agente de Datadog (`http_check`) | Directo **a cada pod**, desde su nodo | Si **cada réplica** está sana |

Configuración del `http_check` mediante una anotación del pod:

```yaml
ad.datadoghq.com/shop-api.checks: |
  {
    "http_check": {
      "init_config": {},
      "instances": [{
        "name": "shop-api health",
        "url": "http://%%host%%:8081/actuator/health",
        "method": "GET",
        "timeout": 2,
        "http_response_status_code": "200",
        "content_match": "\"status\":\"UP\"",
        "min_collection_interval": 15,
        "tags": ["env:course", "service:shop-api"]
      }]
    }
  }
```

**Cuidado con la alta disponibilidad.** Si de 3 réplicas una no arranca, por ejemplo por falta de
recursos en el clúster, el test sintético sigue en verde: el balanceador lo manda a una réplica sana.
Las trazas tampoco lo ven, porque hay réplicas respondiendo bien. El sistema funciona, pero **sin
margen**: si cae otro pod o un nodo, deja de funcionar. Para verlo hay que comparar **pods deseados
con pods disponibles** (kube-state-metrics) y nodos esperados con nodos activos.

---

## 14. Eventos

Un evento es algo relevante que ocurre en la aplicación, la infraestructura o el negocio, y que
queremos **destacar**.

- Se pueden **monitorizar**.
- Se pintan en las gráficas como **líneas verticales** (*event overlays*).
- Se pueden **contar** y representar como serie temporal, por ejemplo los reinicios de pods por hora,
  en vez de una línea por cada uno.

### Orígenes

- **Automáticos de la infraestructura**: reinicios, escalados, eventos de Kubernetes.
- **Monitores**: cada cambio de estado (OK, WARN, ALERT, NO DATA) genera un evento. Un monitor lanza
  eventos, y un evento puede vigilarse con un monitor.
- **Propios**:
  - Desde la aplicación, con el cliente DogStatsD (`recordEvent`). Para negocio: nueva campaña,
    nueva oferta.
  - Por API REST.
  - Desde la línea de comandos en el pipeline de despliegue.

Los eventos pueden encadenarse en cascada, y eso dificulta encontrar la causa raíz.

### Eventos que interesa tener controlados

- Despliegues de versión.
- Reinicios de pods y escalados.
- Copias de seguridad. Nivel 1: ¿ha fallado? Nivel 2: ¿explica una bajada de rendimiento puntual?
- Hitos de negocio: campañas, ofertas.

### Evento de despliegue desde el pipeline

Con el CLI `dog`:

```sh
dog --api_host https://api.datadoghq.eu \
    --api-key "$DD_API_KEY" --application-key "$DD_APP_KEY" \
    event post \
    --alert_type info --no_host \
    --tags "env:course,service:shop-api,service:shop-web,version:$CI_COMMIT_TAG,evento:despliegue" \
    "Despliegue de la tienda $CI_COMMIT_TAG" \
    "Pipeline #$CI_PIPELINE_ID ($CI_PIPELINE_URL), commit $CI_COMMIT_SHORT_SHA, por $GITLAB_USER_NAME"
```

Con `curl` contra la API:

```sh
curl -sf -X POST "https://api.datadoghq.eu/api/v1/events" \
  -H "DD-API-KEY: $DD_API_KEY" -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "title": "Despliegue de la tienda $CI_COMMIT_TAG",
  "text": "%%% \nPipeline: [#$CI_PIPELINE_ID]($CI_PIPELINE_URL) · commit \`$CI_COMMIT_SHORT_SHA\` · por $GITLAB_USER_NAME\n %%%",
  "alert_type": "info",
  "source_type_name": "gitlab",
  "tags": ["env:course", "service:shop-api", "service:shop-web",
           "version:$CI_COMMIT_TAG", "evento:despliegue"]
}
EOF
```

### De un error en el log a un evento

Un log no se convierte en evento por sí mismo. Se define un **monitor de logs** (por ejemplo, «hay
logs con `status:error` en `service:shop-api`»), y su cambio de estado genera el evento.

> **Complemento.** Para los despliegues existe también `datadog-ci`, más moderno que `dog`.
> `datadog-ci dora deployment` registra el despliegue para las métricas DORA (sección 19).

---

## 15. Estadística para construir dashboards

**Tener los datos no es lo mismo que entenderlos.** Si nos pasan las 20.000 nóminas de una empresa,
tenemos todos los datos y no sabemos nada. Para entenderlos hay que **resumirlos**, y la estadística
aporta las técnicas para hacerlo.

### Tipos de variable

Los tipos informáticos (número, texto, fecha, booleano) **no sirven** para diseñar un dashboard.
Sirven los estadísticos:

| Tipo | Subtipo | Para qué sirve | Operaciones | En Datadog |
|---|---|---|---|---|
| **Cualitativa** | Nominal | Clasificar | = ≠ | Etiquetas y facets |
| | Ordinal | Clasificar y ordenar | = ≠ < > | Nivel de log: DEBUG < INFO < WARN < ERROR < FATAL |
| **Cuantitativa** (con unidad de medida) | De intervalo (sin cero absoluto) | Además, contar y restar | + − | Fechas, temperatura en °C |
| | De razón (con cero absoluto) | Además, proporciones | + − × ÷ | Milisegundos, bytes, nº de pedidos |

- Toda ordinal es también nominal, y toda cuantitativa es también ordinal.
- Un **código postal** es un número, pero no es cuantitativo: no tiene unidad de medida.
- Una **fecha** puede usarse como cualitativa (para filtrar) o como cuantitativa (días transcurridos
  desde un origen). En «errores de un día concreto» lo que se mide son los errores: la fecha solo
  **filtra**.
- No tiene sentido decir que 10 °C es «la mitad» que 20 °C, porque 0 °C no es ausencia de temperatura.

### Una variable

**Tabla de frecuencias.** Se puede hacer con cualquier tipo de variable. Basta con **clasificar**.

| Código HTTP | Frecuencia | % |
|---|---|---|
| 2XX | 317 | 89,55 % |
| 3XX | 21 | 5,93 % |
| 4XX | 12 | 3,39 % |
| 5XX | 4 | 1,13 % |

Si una variable cuantitativa tiene muchos valores distintos, la tabla apenas resume. Entonces se
agrupa en **intervalos**, que es convertirla en ordinal.

**Gráficos:**

- Cualitativas: **barras** o **tarta**.
- Cuantitativas: **histograma** o **diagrama de caja y bigotes** (boxplot).
- Diferencia entre barras e histograma: en el histograma el eje X es una **escala continua con
  unidad**. Las barras pueden ir en cualquier orden y omitir categorías vacías. En el histograma
  los intervalos vacíos deben aparecer, aunque sea con altura cero.

**Indicadores:**

| Familia | Indicador | Requiere | Comentario |
|---|---|---|---|
| Tendencia central | **Moda** | Clasificar (cualquier variable) | El valor más frecuente |
| | **Mediana** | Ordenar (ordinal o cuantitativa) | El valor central. Robusta frente a valores extremos |
| | **Media** | Operar (cuantitativa) | Lo que aportaría cada sujeto **si todos aportaran igual**. Muy sensible a los extremos |
| Posición | Percentiles, cuartiles, deciles | Ordenar | P50 = mediana. Los más usados en latencias |
| Dispersión | **Desviación típica** | Acompaña a la media | |
| | **Rango intercuartílico** | Acompaña a la mediana | |

**Nunca debe darse una medida de tendencia central sin su medida de dispersión.**

> **Precisión.** El **rango intercuartílico (IQR)** es Q3 − Q1. El **rango semi-intercuartílico** es
> (Q3 − Q1) / 2, y es el que se interpreta como análogo a la desviación típica alrededor de la mediana.

**La media engaña.**

- *Media frente a mediana.* En Villarriba, 9 vecinos contaminan 5 g de CO al día y Manolo, 1.000 g.
  La media es 104,5 g y la mediana, 5 g. La media es un dato real, pero no es real que todos aporten
  por igual.
- *Misma media, distinta dispersión.* Cinco portales con altura media y mediana de 170 cm tienen
  desviaciones típicas de 0; 7,07; 10; 15,81 y 14,14 cm. La media sola no los distingue.

**Regla de Chebyshev.** Al menos 1 − 1/k² de los datos están a menos de k desviaciones típicas de la
media, para cualquier distribución. Si la distribución es aproximadamente normal, la regla empírica
dice que el 68 % está a una desviación, el 95 % a dos y el 99,7 % a tres. Solo tiene sentido si la
media es representativa del colectivo.

**Aplicado a latencias.** No se usa la media. Se usa P50 si interesa la mayoría de las peticiones y
P90, P95 o P99 si interesa casi todas. Los valores aislados muy altos (un switch saturado, un fallo
puntual) no deben dirigir la decisión.

### Varias variables

Lo útil es combinar variables. **Un dato es información aproximada sobre muchas cosas, y al combinar
datos esa información gana precisión.** Que alguien pese 150 kg dice mucho de su talla de ropa. Si
además se sabe que mide 1,75 m o 2,20 m, la estimación mejora mucho.

| Combinación | Técnica | Gráficos |
|---|---|---|
| Nominal × nominal | Tabla de contingencia (doble entrada) | Barras apiladas o agrupadas, mapa de calor, mosaico, Sankey |
| Nominal × ordinal | Lo anterior, más comparación de medianas | Barras |
| Nominal × cuantitativa | Comparar medias o percentiles entre grupos | Histogramas apilados o superpuestos, boxplots por grupo |
| Cuantitativa × cuantitativa | Correlación | **Diagrama de dispersión** (scatter plot) |

Siempre hay una cuantitativa disponible: **el tiempo**. El histograma sobre el tiempo es lo que Datadog
llama **timeseries**.

> «Errores de app1 frente a errores de app2» no cruza una nominal con una ordinal. Es **una sola
> variable cuantitativa** (número de errores) medida en dos grupos. Sirve para **priorizar** el trabajo.

**Construir un dashboard es un proceso sistemático:** el tipo de variable determina el resumen y el
resumen determina el gráfico.

> **Complemento.** Correspondencia con los widgets de Datadog:
>
> | Necesidad | Widget |
> |---|---|
> | Un valor actual frente a un umbral | *Query Value* (con colores condicionales) |
> | Evolución temporal, comparación con ayer o la semana pasada | *Timeseries* (con *event overlays* y funciones `timeshift`) |
> | Tabla de frecuencias, ranking | *Top List*, *Table* |
> | Proporciones | *Pie*, barras apiladas en *Timeseries* |
> | Distribución de una cuantitativa | *Distribution* |
> | Nominal × nominal | *Heatmap*, *Table* agrupada, *Sankey* (RUM) |
> | Cuantitativa × cuantitativa | *Scatter Plot* |
> | Estado de muchas entidades | *Host Map* (hexágonos), *Check Status*, *Monitor Summary* |
> | Objetivos | *SLO* |

---

## 16. Diseño de dashboards

### Empezar por las preguntas

Antes de cargar datos hay que definir **a qué preguntas debe responder** el dashboard. Si se hace al
final, sobran datos y faltan los que de verdad hacían falta.

**No hay un dashboard único para todos.** Cada interlocutor tiene necesidades distintas y su propio
dashboard. El dashboard debe responder **de un vistazo** a sus preguntas, porque nadie tiene media
hora al día para analizar una pantalla.

### Estructura en cascada (pestañas)

1. **Primera pestaña: ¿va bien o mal? ¿Tengo que seguir mirando?** Si todo está en verde, se sigue
   con otra cosa.
2. **Segundas pestañas: si hay un problema, ¿cuál es?** Sirven para saber a quién avisar: a
   infraestructura o a desarrollo.
3. **Terceras pestañas: ¿por qué ocurre?** Son muy técnicas y las usa el especialista.

### Cómo se sabe si un valor es bueno o malo: referencias

«P95 = 278 ms» no dice nada sin una referencia:

- **Umbrales**, representados con colores. Responden sí o no.
- **Comparación histórica**: ayer, la semana pasada, antes y después de un despliegue (eventos).
  Responde cuánto, y eso cambia la actuación.

El orden de trabajo es: primero el umbral (¿P95 < 200 ms?); si falla, situarse con las referencias;
y después buscar el porqué.

### Dashboard de operaciones y desarrollo: primera pestaña

| Pregunta | Qué se muestra |
|---|---|
| ¿Está arriba cada servicio? | Healthchecks: total frente a OK. Si coinciden, verde. El detalle por endpoint va en otra pestaña |
| ¿Funciona **bien**? | Errores y warnings (logs y APM), latencias P50/P95/P99 (actual, umbral, tendencia), colas como el lag de Kafka |
| ¿Pasa algo raro? | Reinicios, caídas, anomalías |
| ¿Tengo la redundancia prevista? | Pods deseados frente a disponibles, nodos activos (Host Map). Responde sí o no |
| ¿Hay margen para crecer? | Memoria, CPU, disco y red del clúster: uso frente a capacidad, y tendencia |
| ¿Cuántos usuarios hay activos? | Valor actual y tendencia. No es un count acumulable y ningún indicador de tendencia central aporta nada. Es una serie temporal (métrica de tipo *set* o recuento de sesiones de RUM) |

Con los logs, lo importante no es si ayer hubo 3 errores y hoy 2. Lo importante es que **hoy hay 2 y
hay que mirarlos**. El volumen total de logs depende del uso, así que dice poco por sí solo.

El SLA, el SLO y el SLI **no van en la primera pestaña** de operaciones. Sirven para decisiones a
más largo plazo, como cuánto riesgo asumir en el siguiente sprint.

### Dashboard de negocio

| Público | Horizonte | ¿SLO? |
|---|---|---|
| Product Owner | Producto y servicio | Sí |
| Operaciones de negocio | Decisiones inmediatas sobre datos del momento | No |
| Dirección | Medio plazo, sobre datos históricos | Menos |

### Otros usos

Dashboards de testing, desarrollo y despliegue, que muestran cómo va el proyecto (sección 19).

### Cómo se evalúa un dashboard

Un dashboard sirve si **ayuda a decidir** al nivel al que va dirigido. La prueba objetiva es **el uso**:
si la gente entra a verlo, aporta algo; si nadie lo abre, hay que replantearlo.

### Fuentes de datos

Los widgets se alimentan de **métricas, logs, trazas, eventos, RUM, SLOs, monitores**, entre otras
fuentes. Se pueden combinar en un mismo widget.

### Ejemplo: agregar memoria por tipo de pod

Con 2 pods de API y 1 de base de datos, se quiere ver la memoria de la base de datos, la de la API y
el total. Es una **cuantitativa** (RAM) cruzada con una **nominal** (tipo de pod). La consulta suma
la métrica de memoria del contenedor agrupando por la etiqueta de servicio o de deployment:

```
sum:kubernetes.memory.usage{env:course} by {service}
sum:kubernetes.memory.usage{env:course}
```

---

## 17. Monitores, notificaciones y automatización

Un **monitor** compara un dato de Datadog con una **condición o umbral** y, cuando se cumple, tiene
**consecuencias**, normalmente una notificación.

> **Complemento.** Tipos de monitor más habituales:
>
> | Tipo | Para |
> |---|---|
> | Metric (umbral) | Valor por encima o por debajo de un límite |
> | Anomaly / Outlier / Forecast | Desviación del comportamiento habitual, un host distinto al resto, previsión de agotamiento |
> | Logs | Número de logs que cumplen una consulta, por ejemplo errores |
> | APM | Tasa de error o latencia de un servicio o recurso |
> | Synthetic | Resultado de un test |
> | Service check / Integration | Por ejemplo, `http_check` |
> | SLO | Presupuesto de error y tasa de consumo (sección 18) |
> | Composite | Combinación lógica de otros monitores (A **y** B) para reducir el ruido |
>
> Configuración que conviene conocer:
> - **Umbrales de WARN y ALERT**, y umbrales de recuperación para evitar alertas intermitentes.
> - **NO DATA**: qué hacer si deja de llegar el dato. Muchas veces es la peor señal posible.
> - **Multi alert**: un monitor que alerta por separado para cada `service`, `pod`, etc.
> - **Mensaje con variables**: `{{#is_alert}}…{{/is_alert}}`, `{{value}}`, `{{service.name}}`, y
>   destinatarios con `@correo`, `@slack-canal`, `@teams-canal`, `@webhook-nombre`, `@jira-…`.
> - **Re-notificación** si la alerta sigue abierta, y **downtimes** para silenciar ventanas de
>   mantenimiento planificadas.
> - Todo monitor debe responder a **qué hace quien lo recibe**. Si la respuesta es «nada», sobra.

### Acciones automáticas

Notificaciones posibles: correo, Teams o Slack, webhook, issue en Jira, o un **Workflow** de Datadog.

El criterio es evitar el **acoplamiento entre sistemas**:

- Que Datadog borre pods de Kubernetes es técnicamente posible y una mala idea. Las acciones sobre
  sistemas son trabajo de la herramienta de automatización (**Ansible**).
- Hacia fuera, Datadog solo debe **disparar**: llamar a un webhook que lance un playbook, o crear un
  issue en Jira.
- Los Workflows tienen sentido para tareas **dentro de Datadog**. Ante una incidencia, por ejemplo,
  avisar al equipo y crear un *notebook* donde documentarla.

> En clase salió que no hay integración directa con el controlador de Ansible. La vía es un webhook
> contra la API del controlador, por ejemplo para lanzar una plantilla de trabajo de AWX o AAP.

---

## 18. SLI, SLO, SLA y presupuesto de error

| | Qué es | Ejemplo |
|---|---|---|
| **SLA** | Acuerdo con el cliente, con consecuencias si se incumple | 95 % de disponibilidad |
| **SLO** | Objetivo **interno**, más exigente que el SLA | No bajar del 97 % |
| **SLI** | El indicador medido en cada momento | Ahora mismo, 98 % |

**SLI = eventos buenos / eventos totales × 100**

Puede no haber SLA. El SLO y el SLI se definen igual.

### Presupuesto de error (error budget)

- El **presupuesto** es lo que se puede fallar: **100 % − SLO**.
- Lo **consumido** es lo que se ha fallado, **100 % − SLI**, dividido entre el presupuesto.
- Lo **restante** (*budget left*) es 100 % menos lo consumido.

| SLO | SLI | Presupuesto | Fallado | Consumido | Restante |
|---|---|---|---|---|---|
| 95 % | 98 % | 5 % | 2 % | 2/5 = **40 %** | **60 %** |
| 95 % | 93,03 % | 5 % | 6,97 % | 6,97/5 = 139 % | **−39 %** (SLO incumplido) |

### Qué se monitoriza

1. **Valor absoluto del presupuesto consumido.** Por ejemplo, aviso al 50 % (SLI = 97,5 %) y alerta
   fuerte al 90 % (SLI = 95,5 %). Al 100 % se incumple el SLO.
2. **Velocidad de consumo (burn rate).** Si en 2 días de un mes ya se ha consumido el 80 %, el valor
   absoluto aún no alerta, pero vamos fatal.

> **Complemento.** El **burn rate** es el cociente entre la velocidad de consumo real y la sostenible.
> Burn rate 1 significa gastar exactamente el presupuesto al final de la ventana. Burn rate 14,4 en
> una ventana de 30 días significa gastar el 2 % del presupuesto en 1 hora.
>
> La práctica recomendada (Google SRE Workbook) combina dos ventanas, una larga y una corta. Por
> ejemplo, alertar si el burn rate supera 14,4 **en la última hora y en los últimos 5 minutos**. Así
> se detecta rápido y la alerta se apaga sola cuando el problema termina. Datadog lo ofrece como
> **monitor de burn rate** sobre el SLO.

> **Complemento.** Tipos de SLO en Datadog:
> - **Basado en métricas**: cuenta eventos buenos entre totales, por ejemplo peticiones sin error
>   entre peticiones.
> - **Basado en monitores**: porcentaje de **tiempo** que el monitor ha estado en OK.
> - **Por intervalos de tiempo (time slice)**: porcentaje de intervalos, por ejemplo de 5 minutos,
>   que cumplen una condición sobre una métrica, como P95 < 200 ms. Es el SLO de latencia de abajo.

### SLOs trabajados en el curso

| SLO | SLI (buenos / totales) | Fuente |
|---|---|---|
| Disponibilidad del backend | Peticiones sin error / peticiones. Alternativas: healthchecks OK / totales, o pods listos / esperados | Métricas de traza (APM), `http_check`, kube-state-metrics |
| Disponibilidad del frontal | Tiempo con el test en OK / tiempo total | Test sintético → monitor → SLO basado en monitor |
| Impacto en usuarios reales | Vistas sin error / vistas | RUM (`rum.measure.view`, `rum.measure.view.error_free`) |
| Latencia del backend | Intervalos con P95 < 200 ms / intervalos | Métricas de traza, SLO por intervalos |
| Compras correctas | Compras OK / compras | Métrica de negocio `shop.orders.created` por `status` |

La disponibilidad del frontal se construye en cuatro pasos:

1. El **test** dice OK o NOK.
2. Un **monitor** sobre el test: se activa con NOK.
3. El **SLO**: % de tiempo con el monitor sin activar. Objetivo, por ejemplo, 95 %.
4. Un **monitor sobre el SLO**: presupuesto consumido y burn rate.

Que el backend responda no garantiza el servicio: Spring puede estar bien con la base de datos o
Kafka caídos. Por eso el healthcheck debe incluir las dependencias, y el SLO debe medir lo que ve
el usuario.

Hay degradaciones que no rompen la disponibilidad. Si de 2 pods se cae 1, se sigue dando servicio,
pero probablemente más lento hasta que se recupere. Esto lo detecta el SLO de **latencia**, no el
de disponibilidad.

---

## 19. CI/CD, DORA y plataforma de desarrollo

### DevOps

- **Construcción automática** del artefacto a partir del código.
- **Integración continua (CI)**: tener siempre en el entorno de integración la última versión,
  **sometida a pruebas automáticas**. Su producto es un **informe de pruebas en tiempo real**: tests
  unitarios con cobertura, análisis estático (SonarQube), pruebas de integración y de sistema.
- **Despliegue continuo (CD)**.

Del Manifiesto Ágil: «el software funcionando es la medida principal de progreso». Quien dice que el
software funciona son **los tests**, así que el indicador de progreso del proyecto son los tests
definidos y superados.

Un CI como GitHub Actions o GitLab deja ese informe repartido en muchos ficheros guardados como
artefactos: JUnit, JaCoCo, Sonar…

### CI Visibility y Test Optimization en Datadog

- Visibilidad de las ejecuciones de los pipelines: cuánto tardan, qué falla, con qué frecuencia se
  despliega.
- Integración a nivel de test (JUnit): detectar **tests inestables** (*flaky*), ponerlos en cuarentena
  y ejecutar solo los tests afectados por un cambio.
- Asociar problemas de producción a despliegues concretos.

### Métricas DORA

| Métrica | Mide |
|---|---|
| **Deployment Frequency** | Con qué frecuencia se despliega a producción |
| **Lead Time for Changes** | Cuánto tarda un cambio desde el commit hasta producción |
| **Change Failure Rate** | % de despliegues que provocan un fallo en producción |
| **Mean Time to Recovery (MTTR)** | Cuánto se tarda en recuperarse de un fallo |

> **Precisión.** En los informes DORA recientes, MTTR pasa a llamarse **Failed Deployment Recovery
> Time** y se centra en recuperarse de fallos **causados por despliegues**. Datadog calcula las
> métricas DORA a partir de los eventos de despliegue (`datadog-ci dora deployment`) y de las
> incidencias.

### Internal Developer Portal e Internal Developer Platform

- **Internal Developer Portal**: el punto de entrada diario de los desarrolladores. En Datadog es el
  **Software Catalog**: qué servicios hay, de quién es cada uno, dónde están sus dashboards, runbooks
  y SLOs, y si cumplen los estándares (*scorecards*).
- **Internal Developer Platform (IdP)**: la plataforma de autoservicio. Es el terreno de la
  **ingeniería de plataformas**, el paso siguiente a DevOps.

---

## 20. Memoria en aplicaciones Java sobre Kubernetes

- En los pods de backend, el **request y el limit de memoria deben ser iguales**. Así el pod no cuenta
  con memoria que el nodo quizá no tenga, y no lo matan cuando el nodo va justo.
- La JVM tiene su propia memoria asignada: `-Xms` (inicial) y `-Xmx` (máxima), que **conviene igualar**
  para evitar redimensionados del heap.
- Zonas de memoria de la JVM:
  - **Heap**: los objetos, es decir, los datos.
  - **Metaspace**: clases y metadatos, es decir, el código.
  - **Stacks**: uno por hilo, con las llamadas en curso.

> **Precisión.** En clase se habló de *PermGen* (PERM). Desde Java 8 ya no existe: la sustituye el
> **Metaspace**, que vive en memoria nativa fuera del heap.
>
> Consecuencia práctica: la memoria del contenedor tiene que cubrir **heap + metaspace + stacks de
> los hilos + code cache + buffers directos + el propio proceso**. Si `-Xmx` es igual al límite del
> pod, Kubernetes matará el contenedor (OOMKilled) sin que la JVM lance un `OutOfMemoryError`.
> Lo habitual es fijar el heap en proporción al contenedor, con `-XX:MaxRAMPercentage=75`, y dejar
> el resto de margen.
>
> En Datadog: `jvm.heap_memory` y `jvm.heap_memory_max` (del tracer) frente a
> `kubernetes.memory.usage` y `kubernetes.memory.limits` (del agente). Si el uso de memoria del
> contenedor se acerca al límite y el heap no, el problema está fuera del heap.

---

## 21. Glosario

| Término | Definición |
|---|---|
| **Agente** | Proceso de Datadog en cada nodo que recoge, agrega y envía la telemetría |
| **APM** | Application Performance Monitoring: trazas y métricas de rendimiento de la aplicación |
| **Autodiscovery** | Configuración del agente por contenedor mediante anotaciones del pod |
| **Burn rate** | Velocidad a la que se consume el presupuesto de error, relativa a la sostenible |
| **Cardinalidad** | Número de combinaciones distintas de valores de etiqueta. Determina el coste de las métricas |
| **DBM** | Database Monitoring: consultas, planes de ejecución y su relación con las trazas |
| **DogStatsD** | Protocolo y servidor del agente para recibir métricas y eventos propios (8125/UDP) |
| **DORA** | Las cuatro métricas de rendimiento de entrega de software |
| **Error budget** | Presupuesto de error: 100 % − SLO |
| **Evento** | Suceso relevante y esporádico, representable como línea vertical en las gráficas |
| **Facet / Measure** | Atributo de log o span declarado como cualitativo o cuantitativo para filtrar o agregar |
| **IaC** | Infraestructura como código: tratar la infraestructura como código, empezando por versionarla |
| **Log** | Cada línea de registro de una actividad, con su timestamp y sus atributos |
| **Monitor** | Regla que compara un dato con una condición y notifica |
| **Observability Pipelines** | Procesado de la telemetría en nuestra infraestructura antes de enviarla |
| **RUM** | Real User Monitoring: telemetría del navegador o la app del usuario real |
| **SemVer** | Versionado `MAJOR.MINOR.PATCH` |
| **SLA / SLO / SLI** | Acuerdo / objetivo / indicador de nivel de servicio |
| **Span** | Unidad de trabajo dentro de una traza |
| **Synthetic test** | Robot que ejecuta una operación periódicamente para comprobar que funciona |
| **Traza** | Conjunto de spans de una misma operación, enlazados por el `trace_id` |
| **UST** | Unified Service Tagging: las etiquetas `env`, `service` y `version` |
