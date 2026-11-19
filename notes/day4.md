# Usos de los dashboards:

- Operaciones/desarrollo
- Negocio... medio plazo. Nivel estratégico.
- Testing/Desarrollo/Despliegue... cómo estamos?


---

# DEVOPS

- Pipeline de Agile development         -> Contruir el artefacto en base al código en automático
- Pipelines CI                                  |        
    CI = Continuous Integration                 v
    Tener CONTINUAMENTE en el entorno de INTEGRACIÓN la última versión del sistema construida sometida a pruebas automatizadas.
    Objetivo: PRODUCTO: UN INFORME DE PRUEBAS EN TIEMPO REAL
        Unitarios + Cobertura
        Estáticas (SonarQube)
        Integración 
        Sistema

- Pipelines CD (Continuous Deployment)  -> 

> El software funcionando es la MEDIDA principal de progreso.     Define un indicador para un cuadro de mando.

La MEDIDA principal de progreso es el "software funcionando".
La forma en la que voy a medir que tal vamos con el proyecto es mediante el concepto : "SOFTWARE FUNCIONANDO"

Quién dice que el software funciona? TEST

La forma en la que voy a medir que tal vamos con el proyecto es mediante los test queestán siendo definidos/superados.
    ^^^^
INFORME DE PRUEBAS EN TIEMPO REAL

Github Actions. Esto me genera un informe de pruebas en tiempo real? MASO
    - El resultado de la ejecución , en que etapa cayó 
    - JUNIT -> Informe de pruebas con los test
    - JACOCO -> Informe de cobertura de pruebas unitarias
                      v 
    - SONAR -> Informe de análisis estático de código

Acabo con 50 informes (ficheros) ... que los guardamos como artefactos.

---
# CI/CD en datadog

Lo primero que queremos es tener visibilidad de las ejecuciones de los pipelines.
Es un agragador de información sobre las ejecuciones de los pipelines, permitiéndonos tener visibilidad en tiempo real de los resultados de las pruebas y del estado de los despliegues.

- INFORMES de cómo se comportan los pipelines:
  - Qué tarda
  - Que falla
  - Cada cuanto tenemos despliegues

- Una segunda parte: DORA
  - DORA (DevOps Research and Assessment) es un conjunto de métricas que nos permiten evaluar el desempeño de nuestros equipos de desarrollo y operaciones.
  - Métricas clave:
    - Lead Time for Changes: Tiempo que tarda un cambio en ir desde el desarrollo hasta producción.
    - Deployment Frequency: Frecuencia de despliegues.
    - Mean Time to Recovery (MTTR): Tiempo medio de recuperación ante fallos.
    - Change Failure Rate: Porcentaje de cambios que provocan fallos en producción.
 
Gracias a esta integración, podemos identificar / Asociar problemas a despliegues.

- Integración a más bvajo nivel con incluso los test a nivel de JUNIT  y que Datadgo pueda activar/desactivar suites o tests que estén dando problemas. Y avisarme cuales son.



---

# Internal Developer Portal

Para que los desarrollares entren y trabajen en el día a día

# IdP = Internal Developer Platform

Esto tiene que ver con Ingeniería de plataformas, que es el siguiente paso a Devops.


---

## Monitores

Monitor:
- Métrica
- Umbral / Condición aníomala ante la que quiero ACTIVAR el monitor
- Como consecuencia de esa activación (TRIGGER) mandamos una notificación!

Notificación:
- Email 
- Llamar a un webhook
- Ejecutar un script dentro de Datadog : Workflows

Si uso Datadog como herramienta de monitorización tiene sentido definir acciones automatizadas que tienen que ejecutarse cuando ocurre algo.
Qué tipo de acciones me interesa autoamtizar?

- Mandar un correo
- Mandar una notificación a un canal de teams
- Crear un issue en jira!

- Quiero a datadog borrando un POD de kubernetes? Es una locura!

El problema es ACOPLAMIENTO ENTRE SISTEMAS.
Lo normal es todo ese trabajo más de sistemas: ANSIBLE

De hecho ocurre algo curioso:
- Podemos borrar un pod de kubernetes
- Pero no hay integración con ansible controller. WEBHOOKS.

> Sobre los workflows:

Tiene sentido en caso de una incidencia:
- Mandar un email al equipo pertinente
- Y voy a crear dentro de datadog un notebook para documentar la incidencia.
Más para cosas internas en datadog... 
Hacía fuera solo deberían ser DISPARADORES:
- Lanzar un playbook
- Crear un issue en jira
- GUAY!

---

SLI es un indicador que definimos con una fórmula muy concreta:

SLI = (Número de eventos exitosos / Número total de eventos) * 100

Los usamos para nivel de servicio y calidad de servicio.

El SLO es mi objetivo de nivel de servicio, es decir, el valor que quiero alcanzar o mantener para un SLI determinado.

Habrá un SLA o no. El SLA es el acuerdo formal que define el nivel de servicio que se espera cumplir, basado en los SLIs establecidos.

Nosotros podemos esta MONITORizando el SLI, para ver a cánto estamos del SLO definido.
La diferencia entre SLO - SLI es el margen que tenemos para cumplir nuestro objetivo de nivel de servicio. PRESUPUESTO. Budget.

SLO: 95%
SLI: 93.03%
Budget: -39%
 ^^^^^
 Presupuesto es lo que queda de cagarla... El margen que tengo para cumplir el SLO.
 Pero se mide sobre 100% - SLO.

 En nuestro caso el SLO = 95%
 Suponiendo que todo va bien, que debería, puedo cagarla en un 5% de las peticiones.
 Pero en nuestro caso la hemos cagado en un 6.97% de las peticiones.
 Nos hemos pasado en -1.97% de las peticione / 5% = -39.4%

SLO: 95% Tengo que atender por objetivos al menos al 95% de las peticiones.
SLI: 98% Ahora mismo ya he fallado en un 2% de las peticiones. He cumplido con el 98%.
Yo debería cumplir con todas: 100%. Según SLO puedo cagarlas en un 5% = 100% - 95%
He cagado en un 2%.
Me queda del presupuesto de cagarla: 3% :5%-2% = 3%
Pero lo estimo sobre el total que puedo cagarla: 5%
3/5 = 60%
De lo que la puedo cagar, aun me queda el 60% para cagarla.


Me queda ese 3% de margen para cumplir el SLO.
3/5 = 60% del presupuesto.

Una vez definido el SLO, defino una monitorización sobre él.

Voy a monitorizar el -40%, el 60%... "Budget Left"
Hay 2 formas... 
- En valor absoluto: Si me he comido el 100% TRIGGER (FATAL!) -> SLI = 95%
                     Si me comido el 50% TRIGGER (WARNING)    -> SLI = 97.5%
- Cómo de rápido lo estoy consumiendo:
  Tengo un 5% de presupuesto de cagarla. SLO: 95%
  El SLI está en 98%
  He consumido el 2% del presupuesto de cagarla. Aún estoy bien... De hecho ni siquiera saltaría aún el WARNING.

---

SLI mide lo que atendemos BIEN en % sobre el TOTAL.
    SLI del 98% significa que he atendido bien al 98% de las peticiones
    Por ende la he cagado en un 2% de las peticiones. -> 100% - 98% = 2%
El presupuesto es lo que me permito atender mal! en % sobre el total = 100% - SLO
    SLO es el porcentaje mínimo objetivo de peticiones que debo atender correctamente 95%
    Y esto me genera un presupuesto de fallo: 100% - SLO = 5%
Y ahora comparo lo que la ha cagado con el presupuesto de cagarla:
    2%/5% = 0.4 = 40% del presupuesto consumido.

Lo que defino es el SLI y el SLO. La fórmula para calcular el 97, 98% (buenos/total) + OBJETIVO (SLO) >95%
Pero lo que monitorizo en datadog es lo que me queda de presupuesto de cagarla 5% - 2% = 3% 
Se monitoriza medido sobre (dividido entre) el total del presupuesto de fallo 5%: 3% / 5% = 60% <-- Budget Left
Lo que monitori realmente es 100% - Budget Left = 100% - 60% = TASA DE ERROR SOBRE EL PRESUPUESTO!

    Defino un SLO de 95%.
    El SLI está al 98%
    Qué % de presupuesto me queda? 60%
    La he cagado 40% de lo permitido <- 
        Al 100% de lo permitido es cuando llego al SLO: PROBLEMON
            Si llego al 90% YA QUIERO ALARMAS GRANDES!    -> SLI = 95.5%
            Si llego al 50% VETE CONTÁNDOME!              -> SLI = 97.5%
    Pero resulta que ha pasado solo 1 día del mes para el que tengo el presupuesto. Cómo vamos? COMO EL CULO!
        Necesito aquñi una alerte.. no es sobre el valor absoluto. Es sobre la incremento de la tasa de error sobre el presupuesto.
        En 2 días estoy al 80% del presupuesto ... Estoy quemando presupuesto muy rápido. NECESITO AVISO!

---

- Disponibilidad del backend.
   Número de peticiones exitosas / Número total de peticiones.
    ??? De donde sale? Métricas APM! TRAZAS!
   Cuantos healthchecks han sido exitosos frente al total de healthchecks realizados. 
   Pods esperados vs ready

   Puedo tener bien el Pod de Spring(Backend) y mal la BBDD, KAFKA

- Disponibilidad del Frontal
  - Usuarios sintéticos -> Si en algún momento algo no estuvo operativo    <---- TEST 
    - Si está accesible o no
  - Usuarios reales     -> El impacto que tuvo eso en usuarios.
    - En RUM aparece el concepto de VIEW, que representa una interacción del usuario con la aplicación.
      - VIEWS sin errores rum.measure.view
                          rum.measure.view.error_free

- Latencia del backend
  Peticiones que se entregan a tiempo / Número total de peticiones. 200ms

- Compras que terminan bien
  Número de compras exitosas / Número total de compras.


---

Usuario   ---> Frontal                      IAM
         <--- 300 REDIRECT al IAM
         -------------------------------->
         <--- 200 OK FORMULARIO
         -------------------------------->
         <--- 300 OK REDIRECT AL FRONTAL
         ----> Frontal

---

# Disponibilidad del Frontal

  - Usuarios sintéticos -> Si en algún momento algo no estuvo operativo    <---- TEST 
    - Si está accesible o no

Esto lo estamos midiendo sobre usuarios sintéticos.
La pregunta es : PUEDO HACER ESTO CON USUARIOS REALES? NO es posible.

De usuarios reales yo mido gracias al RUM. 
Que es RUM? A bajo nivel? Un script cutre que se ejecuta en el navegador del usuario.
Quien solicita la carga de ese script? Mi web... en el HTML es quien arranca RUM
Y ese scriopt (RUM) va mandando datos a mi Datadog (DIRECTO).

Si el usuario no ha posido cargar la web porque no está disponible, no hay RUM para mandar datos de que aquello no funciona!
No me queda constancia de que haya usuarios que hayan intentado acceder y no hayan podido.


1. Definimos test
   DICE: OK | NOK
2. Definimos monitor para el TEST
   SE ACTIVA | NO SE ACTIVA
     ^                  ^
   TEST_NOK         TEST_OK
3. SLO
   % de eventos buenos/eventos totales * 100
   evento bueno = Monitor NO SE ACTIVA
   evento malo  = Monitor SE ACTIVA
   eventos totales = evento bueno + evento malo
4. Monitor para el SLO
   % de presupuesto disponible
    - 100% He consumido el 100% del presupuesto disponible
    - 50%  He consumido el 50% del presupuesto disponible

% de tiempo que la web está ok | y debemos tenerla ok 95%

---

# Latencia del backend < 200ms / Calidad del servicio
    
    Métrica que sale de las Trazas
    P95 < 200ms

    Definimos objetivo: 95 de las peticiones que se han hecho durante un periodo cumplan eso!
    Defio el indicador SLI: Cuantas intervalos de tiempo tienen P95 < 200ms respecto al total de intervalos de tiempo donde he medido.

Reinicios de pods: Tengo un deployment con 2 pods y se cae uno
- Sigo dando servicio? SI
  Pero es muy posible que me vaya más lento hasta que el pod vuelva a estar operativo.

---

# Evento

Es algo que ocurre en nuestro sistema (aplicación, infra, negocio) y que queremos destacar!.
Podemos monitorizarlos.
Otra cosa interesante es que puedo representarlos en gráficas, como lineas verticales.

Eventos que capturamos:
- Por un lado, datadog captura eventos automáticamente de la infraestructura.
- Por otro lado.. los monitores. Un monitor cambia de estado: OK, NO DATA, WARNING, ALERT.
  Asociado a cada cambio de estado se lanza un evento.
- Yo puedo lanzar mis propios eventos vía api rest. NUEVA VERSION DESPLEGADA DE MI APP.


    MONITOR -> lanza EVENTOS
    EVENTO <- que quiero monitorizar (y defino un MONITOR)


Muchas veces nos pasa que hay eventos que se lanzan en cascada, es decir, un evento puede provocar que se generen otros eventos relacionados. Esto puede dificultar la identificación de la causa raíz de un problema.

Los eventos a su vez generan métricas que puedo usar en los dashboards (no pintando discretamente eventos como lineas verticales), sino contabilizandolo:
> Time series que mire todos los reinios de pods que ha habido. No quiero que cada reinicio se marque como una linea vertical.
> Lo quiero representar como un histograma.

Eventos que nos interesan un huevo tener controlados:
- Reinicios de pods
- Escalados
- Despliegues de versiones
    Lo meteríamos en el pipeline de despliegue (en el Github actions):
    - `dog` cliente de Datadog, que permite entre muchas cosas lanzar eventos desde el pipeline de despliegue.
```sh
     dog --api_host https://api.datadoghq.eu
        --api-key "$DD_API_KEY" --application-key "$DD_APP_KEY"
        event post
        --alert_type info --no_host
        --tags "env:course,service:shop-api,service:shop-web,version:$CI_COMMIT_TAG,evento:despliegue"
        "Despliegue de la tienda $CI_COMMIT_TAG"
        "Pipeline #$CI_PIPELINE_ID ($CI_PIPELINE_URL), commit $CI_COMMIT_SHORT_SHA, por $GITLAB_USER_NAME"
```

    - `curl` para lanzar eventos vía API REST de Datadog.
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

- Backup

    Una cosa que me interesa es saber si el backup ha fallado o no. Esto es nivel 1
    Me puede interesar saber que una bajada de rendimiento ha ocurrido por un backup que se estaba haciendo.. y no le doy importancia. Esto es nivel 2

- Negocio
  Desde la app! Con el api del cliente del agente de datadog.
  También desde API REST
  - Nueva campaña
  - Nueva oferta




---
Como convierto un mensaje de log en un evento
- ERROR EN LOG -> EVENTO?
- Monitor (que mire los errores en el log) -> lanza EVENTO si detecta un error

---

Ingress -> dns !
    datadog.iochannel.tech    DNS -> IP???

Las IPs en mi casa son dinámicas, suelen ser muy estables...
ME toca entrar a mi dns (IONOS)  cambiar todos los registros A cada vez que cambie la IP de mi casa.
Tengo un programa : CRONJOB se ejecuta con X frecuencia y si ha cambiado la IP, entra en IONOS actualiza los registros A de mi DNS automáticamente.