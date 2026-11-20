

# Datadog y Tests y CI/CD

Habitualmente vamos definiendo tests para la app:
- unitarios             \
- de integración        /   Rama feature + dev

- sistema               dev -> release -> main

Los test de sistema, una parte de ellos es la que defino con herramientas tipo:
- Postman/Soapui/Readyapi/karate   Servicios
- Selenium/Playwright   UI

Los pipelines de CI hacen uso de ellos.
Y luego los de CD.. pero la D solo Delivery, no Deployment.
En un pipeline de CDeployment no metemos los test de sistema (menos aún los unitarios o los de integración)

Habitualmente en un pipeline de CDeployment lo que si meto es otro tipo de test: Smoke tests, que son pruebas rápidas para verificar que la aplicación funciona en el entorno de destino antes de proceder con el despliegue completo.
Pero, más lo que pruebo es el DESPLIEGUE no la app.

Aquí sale un tema.

Datadog me permite definir test que a priori serían SMOKE TEST y además me permite definir TEST para MONITORIZACIÓN (HEALTH CHECKS).
Pero me invita a otras cosas:
- Test de UI más extensos (que ya debeían ser extensivos... pero la realidad es que no lo son tanto)
-

Aquí hay algo que hace DATADOG que ya no es solo MONITORIZAR (es una de esas expansiones horizontales de funcionalidad).
- Tiene su propio sistema de pruebas a nivel de UI. Que se usaban inicialmente para SMOKE y para MONITORIZACIÓN (HEALTH CHECKS)
  Pero ahora se pueden usar para pruebas más extensas de la UI. Por qué querría? Si ya tengo Selenium, playwright u otras herramientas de automatización de UI.
  La clave es RUM (Real User Monitoring), que permite capturar la interacción real de los usuarios con la aplicación, proporcionando información valiosa sobre cómo se comporta la UI en condiciones reales y ayudando a identificar flujos críticos que deben ser probados.
  Esta información SOLO LA TENGO DESPUES DE PONER EL SISTEMA EN PRODUCCION!

Yo creo mi sistema.
BACKEND. Le hago pruebas extensivas... Y SOY CAPAZ DE PROBARLO GENIAL! Porque es stateless.
FRONTAL. Le hago las pruebas que se me ocurren. Nunca puedo llegar a cubrir todos los flujos posibles que un usuario puede seguir en la UI. YO NO SOY EL USUARIO.
    Entonces... pruebo los flujos que a mi se me ocurren, pero nunca puedo garantizar que estoy cubriendo todos los posibles caminos que un usuario puede seguir en la UI. Y TIRO PARA DELANTE! Esta es una de las limitaciones grandes del TESTING!

TIRO PARA DELANTE:
Subo a producción, le pongo un poco de perejil a San Pancracio... y a ver que pasa!

Lo que pasa es que cuando a producción y los usuarios empiezan a usar el sistema:
- Empiezan a surgir errores que no habíamos previsto.
- Puedo obtener información muy valiosa sobre cómo los usuarios interactúan con la aplicación y qué flujos son críticos o problemáticos.
    RUM

Con esta información, puedo generar nuevos tests, que antes no podría haber planteado. O al menos no se me habían ocurrido.
Cuándo querría yo ejecutar esos tests? En qué momentos?
- Antes del despliegue: CI, CDelivery... al menos en esos.
---
- Pero ya que tengo las pruebas: Por qué no usarlas como Smoke tests en producción? y por qué no usarlas como health checks en producción?
  Mi sistema, con las arquitecturas que manejamos a día de hoy... que ya no son MONOLITOS, se compone de múltiples servicios independientes que interactúan entre sí. Y muchos de ellos quedan fuera de mi control! Sonen el mejor caso de otros dptos/equipos de mi empresa...A lo peor sin operados por empresas externas, de las que no tengo control.
  Y mi sistema llama para un determinado flujo a un servicio externo.. Y usa su respuesta.
  Y si me cambian el sistema externo sin previo aviso, mi sistema deja de funcionar! Y COMO ME ENTERO?
  Por eso, hoy en día es importante y nos planteamos aplicar todas estas pruebas también en los entornos de producción.
  - YA NO VALE UN TRISTE HEALTH CHECK, /actuator/health

El hecho de usarlas antes del despliegue, pruebas que salen como consecuencia de haber hecho un despliegue (RUM) es lo que llamamos Continuous Testing.

Continuous Testing: Definir pruebas en base a la RUM (Real User Monitoring), y ejecutarlas antes del siguiente despliegue.

---
# Ahora viene otra... Continua el INTRUSISMO!

Ya que datadog se ha metido de pleno NO SOLO EN LA MONITORIZACION, sino también en las PRUEBAS (TEST).

Y aquí hay otro solape. No es solo que esté en la fase de test... es que puedo usarlo para monitorizar los pipelines de CI/CD:
    - Visibilidad de los Pipelines y agregados. Cuántos despliegues, con que frecuencia, Cuanto tardan
    - REPORTING:
      - Qué test son los que están fallando? USO 50 herramientas de testing:
        - JUNIT
        - SELENIUM (PY)
        - Postman
        - JMeter
        - SonarQube
        - Jacoco
       Cada herramienta megenera su informe. No quiero entrar a 50 herramientas por separado = LOCURA!
       Necesito integrar todas esas fuentes de información y generar un informe unificado que me permita ver de manera centralizada qué tests están fallando y por qué. Esto a día de hoy me lo curro yo! Esta papeleta es la que me resuelve DATADOG!

Qué más puede hacer por mi?
- Identifique que test están fallando y por qué, integrando la información de todas las herramientas de testing que utilizo.
- Lo mire en contexto! -> IDENTIFIQUE FLAKY TESTS = tests que fallan de manera intermitente y no consistente, para poder abordarlos de manera efectiva.
- Me puede interesar no solo identificarlos, que ya es un paso, sino GESTIONARLOS!
  - Por ejemplo, desactivarlos temporalmente (Meterlos en cuarentena) . Esto desde el punto de vista de gestión es muy DIFERENTE DE QUITARLOS.
  - CUARENTENA => MONITORIZACIÓN

Datadog me ofrece un INTERCEPTOR,... algo así como un MAN-IN-THE-MIDDLE para los tests. Pongo a datadog controlando QUE TEST DEBEN EJECUTARSE.. por ejemplo vía JUNIT en BACKEND.

    MAVEN -> SUREFIRE -> JUNIT -> Ejecute pruebas
                      ^^
                    Datadog
                    Por ejemplo, no quiero que ejecutes estos 10 tests... o si... pero que NO MARQUES EL JOB como fallido si los test fallan
    
Y puedo ir a más... Si integro Datadog con mi herramienta de CI/CD, puedo hacer que datadog esté:
- Monitorizando el pipeline
- Si detecta que han fallado algunos test de esos cabroncetes que a veces si / a veces no
- Decida meterlos en cuarentena
- Y solicitar a la herramienta de CI/CD que reejecute el pipeline sin esos tests.

Y ya nos volvemos locos del todo!

Esto ya es MONITORIZACION? SI... pero no!
Esto solo puede hacer una herramienta como DATADOG.. porque se necesita para todo esto INFORMACION DE MONITORIZACIÓN EN TIEMPO REAL.

AQUI ES DONDE DATADOG BRILLA! O uno de los sitios.

---

End2End no es solo probar desde la UI.
Probar el backend es también End2End.

En Backend puedo usar JUNIT para end2end testing.
JUNIT tiene un nombre muy malo. No es una librería de Pruebas UNITARIAS.
Es un framework de pruebas. UNITARIAS, DE INTEGRACION y END2END.

    Una prueba en PRODUCCION / INTEGRACION del backend puede estar usando un servicio externo... que puede estar disponible o no... y no depende de mi!
    Y si la prueba falla, mi app no pasa a producción, pero no por un fallo mío, sino porque el servicio externo no está disponible!
    FLAKY TEST!

    La prueba de BACKEND no puede pasar por PLAYWRIGHT, ya que PLAYWRIGHT es una herramienta para pruebas de UI en el frontend.
    Si quiero subir solo la versión de backend, no necesito pasar por PLAYWRIGHT, ya que es una herramienta de frontend.O podría hacerlo... par asegurarme que el frontal sigue operativo con el cambio de versión.
    BACKEND 1.2.4 -> 1.3.0 ESTO A FRONTAL NO LE APLICA.. y no quiero pruebas de frontal (que podré hacerlas...)
    Eso si, el backend le tengo que probar.. integrado con sus servicios externos REALES!
    Y es prueba de sistema en backend.
        NO USO JUNIT (OK) usa postman/Readyapi para pruebas de sistema en backend.
        Y pueden fallar por culpa de un externo (KAFKA ESTA CAIDO)
        Pero eso no tiene porque limitar que yo despliegue mi backend, ya que los fallos por servicios externos no son culpa mía.
        Y ese test me está jodiendo. FLAKY TEST! -> CUARENTENA: Quiero ejecutarlos, quiero monitorizarlos, pero no quiero que jodan el despliegue de mi backend.

    JUNIT ha cambiado mucho en el tiempo. JUNIT 5: JUPITER no es solo un framework de pruebas (de todo tipo).
    Es un agregador de pruebas. JUNIT PLATFORM.
    Puedo ejecutar pruebas de JMETER, CUCUMBER, SPock, y cualquier otro framework de pruebas compatible con JUNIT PLATFORM.

    Las lanzo desde maven -> surefire -> JUNIT (PLATFORM) -> JMETER
                                                          -> ...
        mvn test -> Ejecutando un huevo de pruebas!
        Y para eso maven, en su ciclo de vida que gestiona tienen diferentes fases:
            - test
            - integration-test
            - verify
            - report -> JACOCO

---

Cobertura de tests

- A nivel de Backend es muy fácil medir la cobertura y probar caminos / flujos que sigue una petición (son muy lineales)
  Antiguamente montábamos apps statefull y la cobertura era más complicada de medir, ya que dependía del estado interno de la aplicación y de cómo se gestionaban las sesiones y los datos persistentes.
  Hoy en día montamos apps stateless en servido (REST, microservicios, serverless), lo que facilita medir la cobertura y probar los flujos de las peticiones, ya que no dependemos del estado interno de la aplicación ni de cómo se gestionan las sesiones y los datos persistentes.
  Generamos informes de cobertura = GUAY (JACOCO, cobertura de código en Java)
  Pero no es solo la cobertura. La cobertura mide caminos dentro del código. SOLO DENTRO DEL CODIGO
  No mide los flujo que sigue el usuario. Pero en backen son lineales y no hay problema (stateless)

- A nivel de Frontend, en cambio, la cobertura de código no garantiza que estemos probando todos los flujos que sigue el usuario, ya que la interacción con la UI puede ser mucho más compleja y dependiente del estado de la aplicación en el navegador.

La apps de frontal tienen el STATE en el navegador. En angular puedo gestionarlo:
- Servicio (rxjs)
- Store (NgRx) REDUX

Es muy dificil, por o decir IMPOSIBLE TOTALMENTE que yo pruebe realmente todos los FLUJOS que un usuario puede seguir en la UI, debido a la complejidad y variabilidad del estado en el navegador.


---

# LOGS


Log : Entrada que se ha generado por un sistema en un momento determinado:
    - Tags                  BUSQUEDAS:     tag:valor                                --> De un tag puedo generar una faceta
    - Mensaje   
        -> Tags
        -> Atributos        BUSQUEDAS:     @atributo:valor                          --> De un atributo puedo generar una faceta

FACETAS:
Son indexaciones que hace datadog de un atributo o tag para poder realizar búsquedas eficientes.
Esas facetas se pueden usar:
    - Panel lateral de Datadog para filtrar y explorar logs por facetas
    - Dashboards
    - Monitores

Para que undato de un log pueda usarlo en un dashboard, debe estar indexado como una faceta en Datadog.
Hay 2 tipos:
- Measures: Datos cuantitativos                             Podré hacer muchas más operaciones con él!
- Facet:    Datos cualitativos: NOMINALES / ORDINALES       Contar

---
Puedo tener muchos atributos que voy leyendo de logs de distintas apps que signifiquen lo mismo!
Alias FACETA A LA QUE ASIGNO UN ATRIBUTO 

Un atributo puedo ponerle un alias... Y eso lo vincula a una faceta que exista.
Cuando creo una faceta asociada a un atributo, el atributo ya queda vinculado a esa faceta y se puede utilizar en búsquedas y dashboards a través de la faceta.

Pero en otra app puede ser que ese mismo DATO venga con OTRO NOMBRE... pero quiero vincularlo a la MISMA FACETA -> ALIAS

---

BUSQUEDAS EN LA BARRA DE LOG:
    - Tag:       tag:valor
    - Atributo: @atributo:valor
      - Si tengo un atributo con estructura jerárquica, puedo buscarlo usando la notación de puntos, por ejemplo: @usr.name:valor
    - CONTENIDO DEL MENSAJE (en automático busca TROZOS, no hay que ponerle los *)

    valor?
    - valor exacto    tag:valor   @atributo:valor
    - valor con operador relacional
      - tag:>valor        @atributo:>valor
      - @http.status_code:[200 TO 299]

    OPERADORES LOGICOS:
    - AND:     tag:valor AND @atributo:valor
    - OR:      tag:valor OR @atributo:valor
    - NOT:     NOT tag:valor    -tag:valor
    - Paréntesis para agrupar: (tag:valor OR @atributo:valor) AND @otro:valor

    COMODINES:
        - *: reemplaza cualquier número de caracteres
        - Ejemplo:
          - tag:val*       @atributo:val*
          - tag:*val*      @atributo:*val*        ESTO ES MUCHO MAS INEFICIENTE
        - @atributo:*       \
          tag:*             / Que el atributo exista

    COSAS CON LAS QUE DEBEMOS TENER CUIDADO:
     - No hay operador =, se debe usar : para asignar valores a tags y atributos
     - Si hay >= <= > <   TO
     - NO SE PONE ESPACIO DESPUES DE LOS : rompe la búsqueda
       El espacio separa condiciones de búsqueda
        @attr1:valor tag:valor     ESO SEPARA DOS CONDICIONES DE BÚSQUEDA
            NOTA: ^^^^ ESO ES LO MISMO QUE    @attr1:valor AND tag:valor

        @att1: VALOR               ? EIN?

     - Hay caracteres reservados que deben escaparse con \ si se quieren usar literalmente, como: + - = && || > < ! ( ) { } [ ] ^ " ~ * ? : \ /
        Menchu García
            @persona:Menchu\ García        también valen comillas:      @persona:"Menchu García"
     - AND, NOT, OR en mayúsculas!   

     - Buscar un atributo vacio: @atributo:""
---

@data      "El día 17 de Enero hubo una Venta de coches en Madrid"

    BUSQUEDA 
        @data:*Venta\ de\ coches*


---

env:course service:shop-api AND @dd.service:shop-api @total:>50 AND @product:Monitor\ 27\"

Order created id=161898 customer=lucia product=Monitor 27" quantity=1 total=249.00 status=PAID
Order created id=161794 customer=marta product=Webcam quantity=1 total=79.00 status=PAID

```json
    {
    "dd": {
        "service": "shop-api"
    },
    "id": 161794,
    "level": "INFO",
    "product": "Webcam",
    "quantity": 1,
    "status": "PAID",
    "timestamp": 1795176267439,
    "total": 79,
    "usr": {
        "name": "marta"
    }
    }
```
            env:course
            cluster_name:iochannel-cluster
            container_id:e4bad8409b7fb1d34d8749189de9612025c0d2af9876b1f1e773de9b2d791c03
            container_name:shop-api
            course:datadog
            datadog.index:main
            datadog.submission_auth:api_key
            dirname:/var/log/pods/datadog-curso_shop-api-7b9fd69d8b-fd78s_b7261f39-1461-43bb-a682-b97990eeab34/shop-api
            display_container_name:shop-api_shop-api-7b9fd69d8b-fd78s
            filename:0.log
            image_id:registry.ivanosuna.com/curso/shop-api@sha256:4aa59f7a97fa6c50ae6e2aadc76390e2cfd113f2c54349f3743c46090e7cc334
            image_name:registry.ivanosuna.com/curso/shop-api
            image_tag:c9e2572c
            kube_app:shop-api
            kube_cluster_name:iochannel-cluster
            kube_container_name:shop-api
            kube_deployment:shop-api
            kube_namespace:datadog-curso
            kube_node_role:control-plane
            kube_node:worker2
            kube_ownerref_kind:replicaset
            kube_ownerref_name:shop-api-7b9fd69d8b
            kube_qos:burstable
            kube_replica_set:shop-api-7b9fd69d8b
            kube_service:shop-api
            node_name:worker2
            orch_cluster_id:66761399-d78c-4006-82c9-715e455fb5c6
            pod_name:shop-api-7b9fd69d8b-fd78s
            pod_phase:running
            service:shop-api
            short_image:shop-api
            source:java
            team:training
            version:1.1.2
