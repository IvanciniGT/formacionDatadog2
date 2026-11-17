
# Nuestro entorno para el curso.

Tenemos un cluster de kubernetes 5 nodos. En cada nodo hay un agente de Datadog instalado.

Dentro del cluster tenemos un application desplegada que queremos monitorizar con Datadog.

La app tiene un frontal (JS) y un backend (JAVA/Springboot).
Usa Postgres como base de datos.

Frontal: https://datadog.ivanosuna.com
Backend: https://datadog.ivanosuna.com/api


## Qué pasa por detrás de la cortina

 USUARIO - Navegador        
  > https://datadog.ivanosuna.com
  Se carga la Web
  Se ejecuta el JS
  Como parte de ese JS:
  - Se genera un TRACE_ID
  - Eso se hace con un sdk
    que ofrece datadog (RUM)
  - Además se captura información sobre 
    la interacción del usuario con
    la aplicación (clics, navegación, errores, etc.)


    El JS que se ejecuta ------------ TRACE_ID ------------->  Backend 
                                                            Toma el traceID y genera lo que se llama un SPAN (SPAN_ID)
                                                            SPAN = Segmento de la traza
                                                            Esos segmentos tienen una estructura jerárquica, donde cada SPAN puede tener SPANs hijos, representando sub-operaciones dentro de la misma traza.
                                                            Yo luego podré controlar los tiempos de cada SPAN y, por ende, de toda la traza, lo que me permite analizar el rendimiento y detectar cuellos de botella en la aplicación.

                                                            Si nuestra app lanza una query a BBDD, el trace_id se propaga a esa operación, permitiendo que la traza incluya también el tiempo y los detalles de la interacción con la base de datos.
                                                            En la BBDD llega como un comentario.
    ------------------------                     ---------------------------------------------------------------------
          |                                                 |                                |
          |                                       logs/métricas(nodo/contenedores)       Métricas / Eventos / Trazas propias de la App
    Habla directamente con los                              v                                v
    servidores de datadog                          Agente (se monta por nodo donde ejecutamos programas que queramos monitorizar)
          |                                         En kubernetes se monta por NODO DE KUBERNETES
          v                                                             |       Este agente puede realizar algunos trabajos.
         €€€                                                            v               Filtrado / Agregación
          |                                                            €€€€€
          v                                                             v                           Loki
        --------------------------------------------------------------------------------------------------
                                                Servidores de Datadog

                                                    Pipelines de Ingesta donde aplico transformaciones, filtrado y agregación de los datos antes de almacenarlos o analizarlos.
                                                    El problema es que me cobran:
                                                    - Por el procesamiento
                                                    - Por haber recibido los datos.
                                                    Hay una cosa que podemos montar que son los Observability Pipelines (a nivel del agente/namespacepropio-Worker), que nos permiten procesar los datos antes de enviarlos a Datadog, reduciendo así los costes asociados al envío, procesamiento y la ingesta de datos.

                                                    INGESTA: Cosas típicas:
                                                    - Análisis y extracción de datos de los logs
                                                       - Etiquetado de los logs para facilitar su filtrado y análisis posterior.
                                                       - Tracing de las solicitudes para correlacionar logs con trazas y métricas.
                                                         TRACE_ID, SPAN_ID
                                                    - Métricas




---

RUM (Real User Monitoring) es la herramienta que ofrece Datadog para monitorizar la experiencia del usuario final en la web en su entorno. Permite capturar trazas, errores y métricas directamente desde el navegador del usuario.

Nosotros tenemos un agente en nuestro cluster que se encarga de recopilar métricas, trazas y logs de nuestras aplicaciones (backend, BBDD) y del propio cluster. Este agente se comunica con Datadog para enviar toda la información recopilada, permitiéndonos monitorizar tanto la infraestructura como las aplicaciones desplegadas.

Pero, en paralelo, parte de la app se ejecuta en el navegador del usuario, y es ahí donde entra en juego RUM (Teléfono, Portátil, Tablet, cualquier dispositivo que use el usuario para acceder a la app). A priori no tengo control sobre ese dispositivo.
No se cómo está allí la memoria, ni si hay errores en el navegador del usuario (los podría ver en la consola del navegador... no tengo acceso a ella).

El SDK de RUM se encarga de capturar información sobre la interacción del usuario con la aplicación, generando trazas y métricas que luego se envían a Datadog para su análisis.
Podemos llegar a hacer un REPLAY de lo que un usuario ha hecho y ha ido viendo en su pantalla.


---

# LOGS en contenedores

Cuando trabajamos con contenedores, NO HAY PROPIAMENTE UN ARCHIVO DE LOG, como si trabajo con instalaciones basadas en Máquitas virtuales o instalaciones a hierro (sobre el propio SO).

Qué es un log en un contenedor?
A priori en un contenedor el LOG es la salida estandar del proceso principal que corre en el contenedor.
Un contenedor siempre corre un proceso principal (puede correr otros adicionales). La vida del contenedor queda vinculada a la vida de ese procesos principal. De hecho ,m dentro del contenedor ese proceso toma el id 1.
La salida estandar y la salida de error del proceso principal se consideran los logs del contenedor. Estos logs pueden ser capturados por herramientas de monitorización como Datadog para su análisis y almacenamiento.

En muchas herramientas lo que se hace es redireccionar los ficheros de logs a la salida estándar del contenedor, para que puedan ser capturados y gestionados por el sistema de monitorización.


---

Datadog hace muchas cosas... Es realmente muchas herramientas en 1.
- Métricas : Prometheus/Grafana
- Logs : ELK Stack (Elasticsearch, Logstash, Kibana), Loki, OpenSearch/OpenSearch dashboards
- Tracing : Jaeger, OpenTelemetry
- RUM : Real User Monitoring (experiencia del usuario final en la web)

Que aporta datadog?
La integración de todo eso en una única plataforma nos permite correlacionar métricas, logs, trazas y la experiencia del usuario final, facilitando la identificación y resolución de problemas de manera más eficiente.

La gracia no es que tenga todos los datos en una plataforma, y que acceda a ellos a través de un menú.
La gracia es poder saltar de unos datos a otros.
- Ver un error que le ha dado a un ususario en su nevagador,
- De ahí saltar a las peticiones que se han hecho en backend
- Ver los logs relacionados con esas peticiones en backendque generaron el error al usuario en su frontal
- Ver las trazas relacionadas con esas peticiones en backend, para entender el flujo completo de la solicitud y detectar posibles cuellos de botella o errores.
- Ver las métricas de hardware y rendimiento del sistema, como CPU, memoria, disco y red, para identificar posibles cuellos de botella o problemas de capacida, en el momento en que ocurrió ese error.

Y toda esa integración se basa en un concepto: ETIQUETADO.

Datadog ahce un uso intensivo de TAGS para poder correlacionar toda la información que recoge. Cada métrica, log, traza o evento puede estar etiquetado con información relevante como el servicio, el entorno, el host, el contenedor, el usuario, entre otros. Esto permite filtrar, agrupar y relacionar los datos de manera eficiente, facilitando el análisis y la resolución de problemas.

Hay que llevar mucho control de esas etiquetas.
Yo puedo definir mis propias etiquetas.. y me suele interesar hacerlo. Pero! Datadog trae un conjunto de etiquetas muy especial que necesitamos conocer bien: UST (Unified Service Tag). Estas etiquetas unificadas permiten identificar de manera consistente los servicios y sus componentes a lo largo de toda la plataforma, facilitando la correlación y el análisis de los datos.

Son 3:
- env           Entorno al que se asocia (por ejemplo, producción, staging, desarrollo)     En nuestro lab: course
- service       Componente LOGICO de una app o sistema a la que se asocia una mética/log... En nuestro caso: shop-web, shop-api, shop-db
- version       Versión del servicio o componente al que se asocia la métrica/log. En nuestro caso: 1.0.0, 2.1.3, etc.


Aquí hay una cosa.

---

# Cómo se hace el Versionado (semVer):

vA.B.C

                Cúando suben?
A = major       Breaking changes (cambios que rompen compatibilidad)
B = minor       Nuevas funcionalidades
                Cuando marco una funcionalidad como obsoleta (deprecada)
C = patch       Cuando arreglamos un bug

## Qué versión controlo?

Qué es la versión que pongo en la etiqueta "version"?
Sobre qué controlo versiones?
- shop-api -> Versión
- shop-web -> Versión
- shop-db -> Versión
Además de eso, tendré versiones de otras cosas?

- IaC

---

# IaC: Infraestructura como Código

Infraestructura como código no es tener la infra en ficheros....Al menos no solo.. y de hecho NO ES LO IMPORTANTE!

IaC va de TRATAR LA INFRAESTRUCTURA COMO CÓDIGO, lo primero SOMETIENDOLA A CONTROL DE VERSIONES.

v1.0.0 app1             Y esa app necesita para operar una BBDD
Prepararé una infra para esa versión de la app:   v1.0.0 de la INFRA!

Sale la v2.0.0 nueva de la app... donde hemos metido soporte para REDIS, para que actue de cache y no tener que ir a BBDD.
Necesito actualizar la infra a una nueva version v1.1.0.

    v1.0.0 de la app puede funcionar sobre v1.0.0 de la infra y también sobre v1.1.0 de la infra.
    En cambio la v2.0.0 de la app necesita la v1.1.0 de la infra para funcionar correctamente.

En nuestro caso, estamos en Kubernetes.

## Qué es Kubernetes?

Orquestador de contenedores que automatiza el despliegue, escalado y operación de aplicaciones en contenedores.

Realmente eso es un 2% de lo que hace kubernetes... y lo menos importante de kubernetes.
Kubernetes es una herramienta para definir/operar entornos de producción con lenguaje declarativo (entornos basados en contenedores)…

- En los archivos de manifiesto de kubernetes:
  - Services: Balanceadores de carga internos o externos para exponer los pods.
  - Ingress:  Reglas de proxy reverso
  - Network Policies: Rglas de firewall
  - ...
  - Deployment/Statefulset/Daemonse (al final son plantillas de pods)... donde establecemos limitaciones de HW: cpu, ram, volumes

ESO ES LA INFRA!

El archivo de despliegue de Kubernetes es la INFRA! Infra "VIRTUALIZADA"
Ese archivo debe tener su versión... y es/ representa la versión de la infraestructura que define.
Aunque es más raro...

En un entorno tradicional hay otro concepto:
- Infra     - versión
- App       - versión
- Configuración de despliegue - versión
  - Si uso un servidor de email u otro (eso no es un cambio en la "infra" desde un punto de vista tradicional)
  - Ni es un cambio en la app
  - Pero sí es un cambio en la configuración de despliegue

Que me puede interesar a todas luces tener controlado... y poder dar marcha atrás (ROLLBACK)

En kubernetes, eso queda embebido todo dentro de los archivos de manifiesto:
- Version de la app (tag de la imagen)                      \
- La configuracion (configMaps, secrets, pvcs...)            >  VERSION
- La infraestructura (bbdd, kafka, memoria, cpu...)         /

Que versión pongo en la etiqueta "tag" dedatadog? ESTO ES UNA PREGUNTA A LA QUE TENGO QUE RESPONDER!

    En producción la versión de la infra es distinta a la versión de desarrollo

---

HELM - Chart (version) Esta es la versión del programa que genera el empaquetado de los manifiestos de Kubernetes
Version del empaquetado. Depende de:
    - Version del chart
    - Versión de los parámetros que se pasan al chart
        - Ingress (2)
        - Configmap: Servicio Web            http://otro.servicio.com/api/v1 <- produccion
                     Otro servicio web       http://otro.servicio.com/api/v2 <- desarrollo   

Control de configuración:
    - Versiones de muchas cosas linkadas entre si!

---

La version que elijo en datadog puede ser:
- Versión de la app:
  - GUAY! si quiero comparar la versión de la app entre entornos 
  - Pero no me sirve para comparar un nuevo despliegue de lamisma versión de la app en producción, con respecto al anterior: HE SUBIDO MEMORIA 

Normalmente lo que si me interesde todas todas es GUARDAR TODAS LAS VERSIONES.. en tags diferentes.
    - Versión de la app
    - Versión del despliegue                PARAMETROS de configuración 
    - Versión de la infraestructura?        CPU, RAM, Cambio de versión de un componente de infra (BBDD)

---
Terraform 
    - Versión del script ( equivalente al CHART de HELM)    \
    - Versión Parametros                                    / Versión del despliegue de la infra

El problema gordo en datadog es que aunque yo puedo tener 50 etiquetas diferentes... HAY UNA llamada version que datadog es la que saca en todas las pantallas.

---

Una solución un poco "cutre" a este tema es tirar de eventos
Y muchos cambios de versión (por ejemplo de dspliegue los marco como eventos)

Esto me ayuda con una cosa: En las gráficas ver esos eventos (que aparecen como lineas verticales partiendo la gráfica)
El día 17 de noviembre a las 13:45 se hizo deploy de versión donde cambiamos tales cosas.

Y en las gráficas se verá una línea vertical en el momento exacto del despliegue, indicando que se realizó un cambio de versión y permitiendo correlacionar ese evento con cualquier cambio en las métricas.

---

Servicio de generador de precios. Tu tienes tu versión de tu generador y de tu despliegue.

            /api/v1/generarPrecio    <-- Recibe la configuración del cliente

            Configmap -> Versión (TAG)


---

A nivel del backend vamos a configurar o a generar para envío:
- Métricas
- Logs
- Eventos

## Métricas en datadog:

```java
    public Metrics() {
        // DD_AGENT_HOST / DD_DOGSTATSD_PORT are read by the client automatically;
        // we only set the prefix and the constant tags. Service/env/version
        // come from DD_SERVICE, DD_ENV and DD_VERSION (Unified Service Tagging).
        this.client = new NonBlockingStatsDClientBuilder()
                .prefix("shop")
                .hostname(System.getenv().getOrDefault("DD_AGENT_HOST", "localhost"))
                .port(Integer.parseInt(System.getenv().getOrDefault("DD_DOGSTATSD_PORT", "8125")))
                .build();
    }

    public void orderCreated(String category, String status) {
        client.incrementCounter("orders.created", "category:" + category, "status:" + status);
    }

    public void orderValue(double euros, String category) {
        client.distribution("orders.value", euros, "category:" + category);
    }

    public void paymentDuration(long millis, boolean ok) {
        client.histogram("payment.duration", millis, "status:" + (ok ? "ok" : "failed"));
    } // Esta que hay aqui no debería estar aquí!
    // No debería tratarse como una métrica... conceptualmente es una traza!
    // Pero necesitaba un ejemplo apra incluir los histogramas.

    public void stockLevel(String productName, int stock) {
        client.gauge("stock.units", stock, "product:" + productName);
    }
```


---


Código mio ----> Agente -----> Datadog

           ------http/rest --> 

La comunicación es más eficiente y confiable cuando se realiza a través del agente, ya que este se encarga de manejar la conexión con Datadog, el reintento de envíos fallidos y la agregación de métricas antes de enviarlas.

El agente además me gestiona colas. Si en un momento dado no hay conexión con Datadog, las métricas se almacenan temporalmente en el agente y se reintentan enviar cuando la conexión se restablece. Esto asegura que no se pierdan datos importantes durante interrupciones temporales de la red.

Lo que quieres además es que ese proceso no sea bloqueante, de manera que tu aplicación pueda seguir funcionando sin esperar a que las métricas se envíen a Datadog. Esto es precisamente lo que logra el cliente no bloqueante (`NonBlockingStatsDClient`) que se muestra en el ejemplo de código anterior.

---

En nuestro ejemplo tenemos los 4 tipos de métricas que Datadog soporta:

- Contadores (`incrementCounter`)
    Dato numérico que es agregable en base a todas las dimensiones (etiquetas, y otros) que se le apliquen.

    - Número de pedidos que se hacen en la tienda. Dimensiones:
      - Fecha del pedido
      - Producto
      - Cliente

    Luego puedo agregar:
        - Dame el número de pedidos por intervalo de fechas
        - Dame el número de pedidos por producto
        - Dame el número de pedidos por cliente

- Medidores (`gauge`)
    Datos numericos que no son agregables en base a todas als dimensiones (pueden serlo para algunas dimensiones específicas). 

    - Nivel de stock de un producto. Dimensiones:
      - Producto
      - Fecha   
      - Ubicación del almacén

    Luego NO puedo agregar por ciertas dimensiones
        - Dame el total de stock por intervalo de fechas (NO ES UN DATO QUE PUEDA SUMAR)
          - Stock día 17 + Stock día 18 + ... (NO ES UN DATO QUE PUEDA SUMAR)
    Si puedo agregar por otras dimensiones, como por producto o por ubicación del almacén:
        - Dame el nivel de stoke que tengo entre todos los almacenes para un producto específico SI SE PUEDE 

- Distribuciones (`distribution`)
- Histogramas (`histogram`)

### Distribuciones e histogramas

Similares... pero la cantidad de información que recopilan es diferente... y esto condiciona 2 cosas:
- La pasta que me van a cobrar por guardar estas métricas, ya que recopilan más información y pueden ser más costosas.
- La forma en que puedo agregarlas y analizarlas, ya que la granularidad de los datos afecta las operaciones de agregación que puedo realizar.

- En las distribuciones se guarda toda la información de cada punto de datos individual:
  - Genera muchos valores
  - Me permite hacer cualquier tipo de agregación o análisis sobre los datos, ya que tengo acceso a cada punto individual.
- En los histogramas, en cambio, se guarda información agregada en intervalos o "bins":
  - Eso lo hace el agente de Datadog, que agrupa los datos en intervalos predefinidos:
  - Genera menos valores individuales, pero no permite obtener ciertas estadísticas agregadas como promedios, percentiles, etc.
  - Solo tenemos las que se han calculado a priori... en el momento de la agregación

> Tiempo que tarda en hacerse un pago (ejecutar una parte de un proceso de compra)

Variable cuantitativa continua de razon (tiene un cero absoluto y puede tomar cualquier valor dentro de un rango continuo).

Cada petición de pago que se procesa tendra su valor:
    P1: 2.5 segundos
    P2: 3.1 segundos
    P3: 1.8 segundos
    P4: 2.2 segundos
    P5: 3.0 segundos
    P6: 2.7 segundos
    P7: 2.9 segundos
    P8: 3.2 segundos
    P9: 2.6 segundos
    P10: 3.3 segundos

Si tengo todos esos valores puedo calcular lo que quiera: Media, Mediana, Percentiles, Desviación estándar, etc.
Puedo también representarlos en un histograma (time series) con buckets (intervalos) del ancho que yo defin (agrupa por días, por horas, minutos, segundos)

Eso sería una mética capturada como "distribution".
Si la capturo como "histogram", entonces no tendré acceso a cada valor individual, los datos se agrupan por el agente antes de mandarlos. Por ejemplo cada 5 segundos:
                                                            Se calculan agregados:
    P1: 2.5 segundos                                            Media: 2.5 + 3.1 + 1.8 /3 = 2.4667
    P2: 3.1 segundos                                            P50, P95, P99 ...
    P3: 1.8 segundos                            
    --------------------Primeros 5 segundos
    P4: 2.2 segundos                                            Media: 2.2 + 3.0 + 2.7 + 2.9 + 3.2 / 5 = 2.8
    P5: 3.0 segundos
    P6: 2.7 segundos
    P7: 2.9 segundos
    P8: 3.2 segundos
    --------------------Siguientes 5 segundos
    P9: 2.6 segundos                                            Media: 2.6 + 3.3 / 2 = 2.95
    P10: 3.3 segundos
    --------------------Siguientes 5 segundos

Lo que se mandan son los agregados... Y claro, es mucha menos información.
Lo que pasa es que :
- Tengo las medias que tengo, los percentiles que tengo, pero no tengo acceso a cada valor individual, por lo que no puedo calcular otras estadísticas que no se hayan agregado previamente.
- Si pinto un histograma, solo veré la distribución de los agregados en los intervalos definidos, no los valores individuales.

---

## Eventos

Los eventos hay varias formas de crearlos, por ejemplo:
- Vía el cliente de datadog desde mi app. Eventos de negocio.
    - Nueva campaña promocional que activo en la app, con unos vales descuento... 
    - Registro evento de esa campaña promocional
- Cliente HTTP
- Cliente de tipo cli (Command Line Interface)
  - Este lo usamos muchos en los pipelines de CI/CD. Por ejemplo para marcar un evento de despliegue o de ejecución de un job.
    Aquí hay algo que hace en automático la parte de APM 

--- 

## Logs

Los logs no los generamos con el cliente de Datadog desde la app.
En mi app tendré una herramienta de logging que se encargará de capturar los logs generados por la aplicación y enviarlos a Datadog.
Y lo único que hago es escupir lineas de texto al sistema de logging de mi aplicación, que luego se encargará de enviarlas a Datadog.

Esas lineas luego hay que procesarlas para extraer la información relevante, como niveles de severidad, mensajes, timestamps, y cualquier otro dato que queramos analizar o visualizar en Datadog.

> Ejemplo

2024-06-15 10:00:00    INFO   [quien generó el evento]  Usuario registrado: user123 - negocio
TIMESTAMP              LEVEL   QUIEN                    MENSAJE    

En el mensaje tendré que poner:
- Los datos propios que quiera registrar
- Tags e información adicional de datadog: por ejemplo, `env:production`, `service:my-app`, `version:1.0.0`
- Normalmente los inyectamos en automático:
   [dd.env=production dd.service=my-app dd.version=1.0.0]
- Además tendré tags específicos de ese registro particular que estoy haciendo.

### Problemas con los logs

Los logs NO DEBEN REGISTRAR SOLAMENTE información relevante para desarrolladores. 
También deben contener información útil para el monitoreo y análisis de la aplicación en producción: eventos importantes del negocio.

De ahí salen cuadros de mando: DASHBOARDS.
Los desarrolladores loguean SUS MIERDAS.. y es perfecto para ellos.

Desde el punto de vista de negocio es IMPRESCINDIBLE loguear otras cosas que permitan entender el comportamiento de los usuarios, el estado de las transacciones y cualquier evento crítico para la operación del negocio:
- Nueva venta
- Registro de usuario
- Inicio de sesión
- Pago fallido
- Usuario que abandonó el carrito de compras

Requisitos NO FUNCIONALES:
- ...
- Qué logs se generan para negocio
- Y qué estructura deben tener esos logs (no quiero a un desarrollador inventando estructuras sobre la marcha) -> Contrato/API

Esto es lo que me permite luego montar PIPELINES DE INGESTA que sean capaces de extraer todos esos datos.

IMPORTANTISIMO: ESTANDARIZAR LOS LOGS. No pueden quedar a criterio del desarrollador.
---


BBDD PRODUCCION -> ETL --> DATA LAKE --> ETL --> DATA WAREHOUSE
                                                    BI (Business Intelligence)
                                                    Reporting

---

Ese log no va a un fichero... podría ir... pero no tiene sentido:
- Esperar a la escritura de la entrada
- Si se llena el HDD? Que pasa? ROTACION... pero si roto antes de que se manden los datos a otro sitio: se pierden los logs.

---

APP
        v
    Escribe log en memoria
        ^
Alguien que lee  > Lo manda a QUIEN SEA (DATADOG, ES, LOKI)
        FluentD, Filebeat (preprocesamiento / filtrado en origen)   | Logstash, DataPepper, Observability Pipelines

No pasa por disco, y la confirmación es solo: OK ya lo tengo yo.
Es una responsabilidad que le quito a la app.

Ahí usamos mucho VOLUEMENES de KUBERNETES de tipo EMPTY DIR: {medium: "Memory"}
Y el volumen lo monto enruta física del filesystem donde la aplicación escribe los logs.
La app escribe en un fichero con soporte en RAM, no en HDD, uso un tropzo de RAM como HDD... el rendimiento es brutal!

---

# Traza:

Es un intervalo de tiempo durante el cual se sigue la ejecución de una solicitud o transacción a través de los diferentes componentes de la aplicación.

Una traza tiene un identificador único que permite correlacionar todos los eventos y logs generados durante la ejecución de esa solicitud o transacción.

Las trazas a su vez se dividen en Spans, que representan unidades individuales de trabajo dentro de la traza. Cada span tiene un identificador único y puede contener información como el nombre de la operación, la duración, los metadatos y los logs asociados.

Las trazas también pueden llevar metadatos adicionales.

Y lo que se nos monta es una estructura jerárquica donde una traza contiene múltiples spans, y cada span puede contener sub-spans, formando un árbol que refleja la ejecución de la solicitud o transacción a través de los diferentes componentes de la aplicación.

Esa estructura la definimos nosotros (desarrollo) en la app.

Dónde irán los logs de negocio, las métricas de negocio y los eventos de negocio? Dentro del código?
En nuestro sistemas, (BACKEND) tendremos un huevo de clases/Interfaces...
En cuál metemos esto?
- AdviceControllers - AOP
- Repositorios
- Servicios         <<<< CAPA SERVICIO: Lógica de negocio (métricas de negocio, eventos de negocio, logs de negocio)
- Controladores

Las trazas son otra cosita... Y van principalmente orientadas a desarrollo. A negocio se las trae al peiro.
Las metemos a varios niveles (Controlador, Servicio, Repositorio) dependiendo de dónde queramos analizar la información de la ejecución.

Se genera en cliente                                                    T1 ------------------------------------------T2  TRAZA
Me puede interesar tener un span a nivel de controlador                        T1--------------------------------T2      SPAN
Me puede interesar tener un span a nivel del servicio... o varios                T1------------T2 T1-----------T2
Me puede interesar tener un span a nivel de repositorio... o varios                   T1----T2 

Datad0g.2026$


---


# Test Sistema

Los creo para pasar la app a producción. -> Producción v1
Defino en datadog test nuevos para verificar que las cosas funcionan en producción con el paso del tiempo.

Ya que tengo estos tests definidos... porque no usarlos cuando vuelva a hacer un paso a producción.

Hay cierto solape... y me puede interesar acabar definiendo los test dentro de datadog.. y actiavrlos en el pipeline de CI/CD
- Selenium / Cypress / Playwright