# Dashboards

## Operaciones / Desarrollo

    1º PESTAÑA: SI VA BIEN O MAL EL SISTEMA/SERVICIO/APP?
        El objetivo es que al entrar aquí sepa si me tengo que ocupar de algo o no! Si hay algún problema que requiera mi atención. Si no, tengo más cosas que hacer.

        5 minutos a pensar qué ponemos!
            SLA / SLO / SLI?        NO A priori no es un dato relevante para la operación actual/inmediata del sistema
                                       Puede ser relevante para la toma de ciertas decisiones. Qué metemos en el siguiente sprint! Me arriesgo más o menos.
            - Disponibilidad de cada servicio    (ESTA ARRIBA O NO)
            - FUNCIONA .. ok PERO FUNCIONA COMO DEBE? FUNCIONA BIEN?
              - Errores/Warnings  <- Logs     Primero quizás si hay errores. Luego entro en detalle
              - Latencia / Rendimiento    <- Métricas de tiempo de respuesta, carga, etc.
              - Como está la cola del kafka
            - Cosas raras / anomalías que estén pasando (Reinicio, caídas inesperadas, comportamientos extraños)
            - Estado de los hosts / cosas de infra ? CLARO!
              - Tengo todos los pods que necesito/están previstos   \
              - Tengo todos los nodos arriba                        /   Alta disponibilidad      BOOLEANO (Diagrama con exágonos, indicando nodos activos / inactivos)
                - Estado de cada nodo (activo/inactivo)                                                 Host Map

                    Tengo un deplyment con 3 réplicas, con su Service ClusterIP por delante (BALANCEADOR de carga).
                    Pero solamente hay 2 activos... un pod no llegó a arrancar... no hay espacio en el cluster.
                    El sistema funciona, los tiempo pueden ser buenos... pero estoy jugando con fuego...como se caiga un nodo o un pod, el sistema puede dejar de funcionar correctamente.

                    Esto mismo a nivel de NODOS.
              - La potencial escalabilidad del sistema (capacidad de crecer y manejar más carga)
                - Como estamos de RAM, CPU y otros recursos críticos del cluster

              Cúantos usuarios unicos tenemos haciendo cosas. BIEN!
                ^^^^^
                Cuantitativa: Estadísticos de tendencia central (media, mediana, moda, percentiles).   Me aporta alguno de ellos algo? NADA
                              En este caso es un dato que cambia con el tiempo. No agregable. -> Descarta usar "Counter"

                              Qué otra cosa podemos hacer? - Sacar el valor actual. (MEDIDA MAS RECIENTE)
                                                             El valor necesito ponerlo en contexto (tendencia)
                                                                Tendencia (+-) Tasa de variación (+-%)
                                                                HISTOGRAMA con respecto al tiempo! TIME SERIES


    2ºs pestañas.. que me ayuden a entender SI HAY UN PROBLEMA, CUAL ES EL PROBLEMA > Me sirve para decir al tio de infra que tiene que entrar a mirar
                                                                                    > O al de desarrollo
    3ºs pestañas.. que me ayuden a entender PORQUE SE ESTA PRODUCIENDO ESE PROBLEMA <<< Muy técnicas (Entra el tio de infra a mirar...)




## Negocio

    1º PESTAÑA: SI VA BIEN O MAL EL NEGOCIO?
        PO (Product Owner)
            SLA / SLO / SLI?        SI
        Negocio negocio Si vendo o no vendo         OPERACIONES         Toma decisiones ya sobre los datos de ya, para que tengan impacto ya!
            SLA / SLO / SLI?        NO
        Negocio negocio Si vendo o no vendo         GERENCIA            Toma decisiones a medio plazo sobre los datos históricos, para que tengan impacto en el futuro!
            SLA / SLO / SLI?        MENOS

Montar cuadros / Dashboards es muy complejo... sobre todo por qué nadie a priori sabe lo que necesita.
El objetivo del cuadro de mando / dashboard es proporcionar información clara que ayude a la toma de decisiones al nivel que corresponda.
Evaluar un cuadro de mando es dificil.. porque es subjetivo y depende del nivel de decisión al que esté dirigido. Ayuda ese dashboard o no a la toma de decisiones al nivel correspondiente?
La forma de ver si un cuadro funciona o no.. es por el uso que tiene. ENTRA LA GENTE A VERLO? SI... Guay.. algo estará aportando!
Si nadie lo usa, probablemente no esté aportando valor y haya que replantearlo.

---

Toda la información que voy a poner en estos cuadros de mando / dashboards de donde sale? Sale de datos que tengo guardados en datadog.
Puedo usar métricas, logs, traces y eventos para construir mis dashboards y cuadros de mando.
Esos son algunos ORIGENES DE DATOS... pero hay muchos otros.


---

SLA: Acuerdo entre un proveedor de servicios y un cliente que define el nivel de servicio esperado.   95% de disponibilidad, por ejemplo.
SLO: Objetivo de nivel de servicio, una métrica específica que se espera cumplir dentro del SLA.      Internamente mi objetivo es no bajar del 97%
SLI: Indicador de nivel de servicio, la métrica real que se mide para evaluar si se cumple el SLO.    Como estoy ahora (indicado por el SLI)

    Monitor SL -> Me da el SLI (en cada momento del tiempo)
                  Luego lo comparo, con el SLO para ver si voy bien o no.

---

Queremos mirar si nuestro backend está operativo.
Tenemos un HEALTHCHECK que nos indica si el backend está operativo o no.
https://datadog.iochannel.tech/actuator/health                      NOS VALE?  SI

Hay que llamar a esa ruta y verificar si nos devuelve un 200 o no!

Quién queremos que llame a esa url?
    - Un robot (test-sintético) que definamos en datadog
     
    - Kubernetes llama ya a esa ruta? Más o menos.
        - https://IP_POD/actuator/health                            NOS VALE?  SI
        ??? Esta comprobación quién la hace? Controller-manager
            TRAZA! APM (METRICA)

    - Agente de datadog que puede hacer la comprobación desde el nodo donde está corriendo.
        - https://IP_POD/actuator/health                            NOS VALE?  SI
            La configuración se hace a nivel del Pod del mio.
            Se usa una ANOTACION en el pod:
                  annotations:

```yaml                  
        # "source" picks the Java log pipeline; the service comes from the label above
        ad.datadoghq.com/shop-api.logs: '[{"source":"java"}]'
        # Health check FROM the Datadog agent of the node, against this pod (not via the ingress).
        # /actuator/health and not /readiness: the full health includes Postgres.
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

MONITOR (contrastación entre un dato que tiene datadog y un UMBRAL, valor de referencia, condición) -> CONSECUENCIAS.



---

```yaml
annotations:
   ad.datadoghq.com/showroom-service.logs: |-
      [{
        "source": "showroom-service",
        "service": "showroom-service",
        "log_processing_rules": [{
          "type": "multi_line",
          "name": "log_start_with_date",
          "pattern" : "\\d{4}-(0?[1-9]|1[012])-(0?[1-9]|[12][0-9]|3[01])"
        }]
      }]
```

JSON!



---

Con 2 o 3 pods, si uno no arranca:
- Si lo miro desde Synthetic Test no hay probloema... Entra por balanceador y me lleva a uno bueno.. Contesta OK
    Lo que hemos hecho no identifica el problema
- Si lo miro en base a las trazas, tampoco hay problema ... no lo identificaría:
    Tengo uno que SI ESTA CONTESTANDO... si hay datos y no son erroneos. 



---

shop_line %{date("yyyy-MM-dd HH:mm:ss.SSS"):timestamp} %{word:level}\s+\[%{notSpace:logger.thread_name}\] \[dd.service=%{notSpace:dd.service} dd.env=%{notSpace:dd.env} dd.version=%{notSpace:dd.version} dd.trace_id=%{regex("[^ ]*"):dd.trace_id} dd.span_id=%{regex("[^ \\]]*"):dd.span_id}\] %{notSpace:logger.name} - %{data:msg}




PODs api  x 2
PODs bbdd x 1

Quiero agregado:
- Cuanta RAM BBDD
- Cuanta RAM API
- Cuanta RAM TOTAL

INFRA
- RAM                       Cuantitativa
- TIPO POD (api, bbdd)      Nominal

---

Memoria en uso de los pods de backend
Memoria límite de los pods de backend = Memoria request de los pods de backend (QUE DEBERIAN SER IGUALES!!!!!!!!)

Mi backend está creado con JAVA.. Y un programa java rueda dentro de una jVM
La jVM tiene una Memoria Asignada
Cuánta hay en uso?

java -Xms<memoria_inicial> -Xmx<memoria_maxima>
                ^^^^^^^^^^^^^^^^^^^^
                    IGUALES!

En la memoria de la JVM, tengo: HEAP, PERM, STACK
- HEAP: memoria para objetos dinámicos                  DATOS
- PERM: memoria para clases y metadatos                 CODIGO
- STACK: memoria para hilos y llamadas de métodos       HILOS