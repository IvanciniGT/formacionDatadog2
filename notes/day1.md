
# Datadog

Es una herramienta de observabilidad y monitoring.

Se ofrece como SaaS (Software as a Service).
En local montamos agentes que recopilan métricas y logs de nuestros sistemas y aplicaciones.

Aunque hablamos de una herramienta, dentro hay muchas cosas (muchas herramientas):
- Monitoreo de infraestructura
- Monitoreo de aplicaciones
- Gestión de logs
- APM
- RUM + Test sintético (agentes robot) No solo previo paso a producción , sino también en producción
- ...

Datadog ha crecido mucho... y tiene una política de expansión en horizontal MUY agresiva.

## Monitorización vs Observabilidad

- **Monitorización**:  CONOCIMIENTO A PRIORI!

    A priori decido / establezco qué cosas creo que pueden ir mal y que son importantes.. Y entonces me centro en monitorizar esas cosas.
    - Medir cosas que considero importantes a lo largo del tiempo
    - Configurar alertas sobre esas cosas (normalmente trabajamos con umbrales):
      - HEAP > 80%
      - GC de nivel 2 (no solo el de eden, también el de old) no entre con una frecuencia alta
      - Peticiones HTTP con 5XX, 4XX
      - 5XX > 3%

    Responder a una pregunta: QUÉ ESTÁ ROTO? 

- **Observabilidad**:  CONOCIMIENTO A POSTERIORI!

    Es entender en tiempo real qué está pasando en nuestro sistema, incluso si no habíamos previsto que algo podría ir mal.

    Responder a la pregunta: POR QUÉ ESTÁ/SE HA ROTO? 

En general decimos que la Monitorización es un subconjunto de la Observabilidad. La monitorización nos permite detectar problemas conocidos, mientras que la observabilidad nos permite entender y diagnosticar problemas incluso si no los habíamos previsto.

---

# Dentro de datadog vamos a estar recopilando muchos tipos de información

- Métrica

            Es un dato cuantitativo, normalmente (por no decir siempre) asociado a un instante del tiempo.

- Log / Registro (de algo que ocurre en un momento dado del tiempo... se solapa ciertamente con el concepto de EVENTO)

            Normalmente es un dato de texto, ESTRUCTURADO o SEMI-ESTRUCTURADO.
            Nos ayuda a entender (dar contexto) lo que está ocurriendo en nuestro sistema

            Nuestros sistemas generan logs (registran las actividades que ocurren en ellos).
            Asociado a cada log hay un timestamp que indica cuándo ocurrió la actividad que se está registrando.
            Y además, tendremos una serie de campos adicionales que nos proporcionan contexto sobre el log, como el nivel de severidad, la fuente del log, etiquetas asociadas, entre otros.

            A este nivel, no nos referimos con la palabra log al fichero donde se van registrando las actividades.
            Para nosotros log es qué? CADA LINEA de esos ficheros.

    > Query a mi postgres. Qué registro?
        QUERY ... esta la actividad que se está registrando en ese log.
        FECHA/MOMENTO            < Etiqueta
        Quién                   < Etiqueta
        Tiempo que tarda        < Etiqueta. De esta etiqueta podré sacar una métrica de tiempo de respuesta.
        Estado de respuesta     < Etiqueta

- Traza     Es un grupo de registros/metricas que agrupamos por un concepto (TRACE_ID)... pero que conceptualmente nos muestran el flujo completo de una operación o transacción a través de nuestro sistema.

    > Un usuario accede a mi sistema vía el frontal (SE GENERA UN TRACE_ID)
    A partir de ahí, lo que queremos es que toda operación que ocurra en el sistema quede asociada a ese TRACE_ID, de manera que podamos reconstruir el flujo completo de la transacción.
    Conceptualmente el trace_id es una etiqueta más, a la que datadog le va a dar un tratamiento especial para poder reconstruir el flujo completo de la transacción.

        Yo quiero saber que ese usuario, como consecuencia de una operación que ha hecho en el frontal, se acaba accediendo al backend, a tal endpoint.
        Que allí dentro se llama a la BBDD.. y se tira una query... y se deja un mensaje en un sistema de mensajería como KAFKA.
        Que a la media hora se lee el mensaje del sistema de mensajería desde un consumidor... que sigue trabajando asíncronamente con el flujo de la transacción.

        Quiero poder ver TODO LO QUE ACONTECIÓ en mi sistema asociado a ese TRACE_ID, a esa operación que inició el usuario en el frontal.
        Tendré muchos logs, generados por muchas partes de mi sistema, pero todos asociados al mismo TRACE_ID.
        Y además, cada log ocurre en un momento determinado del tiempo, lo que nos permite reconstruir la secuencia temporal de los eventos dentro de la traza.

        Aquí es donde Datadog aporta un huevo!
        Porque además podrá contrastar eso que ha ocurrido con otros datos:
        - Cómo estaba la RAM en ese momento, la CPU...
        - Qué estaba ocurriendo en otros servicios relacionados
        - Qué métricas de negocio estaban afectadas en ese momento

- Evento    También es algo que ocurre en un momento dado del tiempo.

Pero... es conceptualmente diferente de un log... sobre todo por 2 motivos:
- La frecuencia con la que ocurre. Los logs los reservamos para actividades/acciones que ocurren con alta frecuencia, mientras que los eventos son más esporádicos.
- Los eventos queremos tenerlos muy controlados y registrados, ya que suelen representar sucesos importantes o críticos dentro del sistema:
  - Paso a producción de la versión 1.2.7 de mi backend / Reinicio / Campaña promocional de mi producto
    Quiero saber que consecuencias tuvo un cambio en el sistema, qué paso con los tiempos, con los errores, con la disponibilidad

La clave es el análisis de IMPACTO que tendremos como consecuencia de los eventos importantes que ocurren en nuestro sistema.

# Dashboards

Por qué necesitamos dashboards?

Una cosa es TENER LOS DATOS y otra cosa muy diferente es ENTENDER LOS DATOS!

> Imaginad que yo quiero ir a trabajar a Mercedes!

Voy a hablar con RRHH y me pasan las nónimas de todos los empleados (saltándose todas las leyes de protección de datos) 20k nóminas.
No hay más datos , con respecto a lo que allí cobra la gente.
TENER LOS DATOS NO ES LO MISMO QUE ENTENDERLOS.

Aquí es donde la estadística como ciencia nos echa una mano. Qué he de hacer para entender los datos? RESUMIRLOS
Y la estadística es lo que me ofrece, formas / técnicas para resumir la información.

- Cuál es la más básica? TABLA DE FRECUENCIAS

Tengo peticiones y cada petición acaba con un HTTP status code: 2XX, 3XX, 4XX, 5XX

| HTTP Status Code | Cuántos    | %                         |
|------------------|------------|---------------------------|
| 2XX              |    317     | 317/354 * 100 = 89.55%    |
| 3XX              |     21     | 21/354 * 100 = 5.93%      |
| 4XX              |     12     | 12/354 * 100 = 3.39%      |
| 5XX              |      4     | 4/354 * 100 = 1.13%       |

Cuántos = FRECUENCIA

¿Qué necesito para poder hacer esta tabla de frecuencias? es CLASIFICAR las peticiones en base a un concepto (HTTP Status Code), puedo calcular 
la tabla de frecuencias.

En base a qué tipo de variable puedo hacer una tabla de frecuencias? DE TODAS.
De aquí salen todos los demás.

Aunque para algunos tipos de variables no compensa. por ejemplo: Si tengo una variable con muchos potenciales valores posibles (normalmente lo encuentro -aunque no solo-) en variables cuantitativas, la tabla de frecuencias puede volverse muy extensa y poco útil = RESUMO POCO

| SALARIO  | FRECUENCIA |
|----------|------------|
| 1765.87  | 1          |
| 1770.00  | 2          |

RESUMO POCO!.

En estos casos qué hago? INTERVALOS/RANGO = realmente es: Convertir la variable CUANTITATIVA en una variable ORDINAL

| RANGO      | FRECUENCIA |
|------------|------------|
| <1500      | 1273       |    Poco
| 1500-1999  | 845        |    Algo
| 2000-2499  | 432        |    Lo normal 
| 2500-2999  | 210        |    Bastante
| 3000+      | 98         |    Montonón

Esa tabla de frecuencias luego puedo representarla como tabla, o como un gráfico: BARRAS, TARTA

Esto sirve para variables CUALITATIVAS y para variables CUANTITATIVAS con pocos valores distintos. Me refiero a las tablas.
Los gráficos... cambia la cosa.
Cuando tengo variable CUALITATIVA: Tarta / Barras
Si tengo variable CUANTITATIVA?    HISTOGRAMA, BOXPLOT (caja y bigotes)

Diferencia ente histograma y BARRAS? El eje X. En un histograma hay una escala en base a la UNIDAD DE MEDIDA. En un barras, el eje X representa categorías. No es continuo, ni hay una unidad de medida asociada. Tiro barras... que puedo poner en el orden que me de la gana.
Si una categoria no tiene datos, directamente no represento esa barra en el gráfico.
Esto nunca puedo hacerlo con un histograma. El orden está cerrado (el eje X representa un rango continuo de valores). Si un intervalo no tiene valores, tampoco puedo fumarmelo, la barra debe aparecer aunque sea con altura cero.

Hay otro gráfico que usamos mucho.. aunque en datadog nos cuesta representarlo: 

Esto es lo más básico. A partir de aquñi, qué más podemos hacer en estadística. El objetivo es resumir la información.
Podemos resumirla más: LA PODEMOS DEJAR EN UN TRISTE NUMERO: Indicadores Estadísticos:

- Indicadores de tendencia central: Me dice "por donde van los tiros". Groso modo: "Por donde caen los valores"
  - Moda            El valor con frecuencia más alta, que más veces se repite.
                    El que está de MODA! Le usamos poco. Para calcularlo, qué necesito? TABLA DE FRECUENCIAS
                    Necesito CLASIFICAR LOS DATOS: La puedo calcular sobre CUALQUIER TIPO DE VARIABLE
    170cm  170    170     170
  - Mediana         El valor central cuando los datos están ordenados. El del medio.
                    Necesito ORDENAR LOS DATOS: La puedo calcular sobre VARIABLES ORDINALES O CUANTITATIVAS.
  - Media           La media atiende a una fórmula matemática: Sumar todos los valores y dividir entre el número de valores.
                    Se definición sería "CUANTO CONTRIBUYE CADA SUJETO DE ANALISIS AL TOTAL SI TODOS CONTRIBUYEN POR IGUAL". 
                    La media es muy sensible a valores extremos! ES MUY MENTIROSA! Y ADEMAS NO LA INTERPRETAMOS BIEN.
                    Necesito SUMAR LOS DATOS Y DIVIDIR ENTRE EL NÚMERO DE DATOS: La puedo calcular sobre VARIABLES CUANTITATIVAS.
- Indicadores de posición:
  - Percentiles     Los valores que dejan por bajo un determinado % de los datos.
  - Cuartiles       Los valores que dejan por debajo del 25%, 50% y 75% de los datos.
  - Deciles         Los valores que dejan por debajo del 10%, 20%, ..., 90% de los datos.   
  - Mediana         Lo valores que dejan por debajo del 50% de los datos.
  Los usamos mucho


- Indicadores de dispersión. NUNCA JAMAS debería poner una MEDIDA DE TENDENCIA CENTRAL ofrecer su MEDIDA DE DISPERSION ASOCIADA.
    - Desviación estándar o típica. Me informan de CUANTO CAMBIAN LOS DATOS con respecto al "POR DONDE VAN LOS TIROS"

        170cm con desviación de 20cm. Cómo lo interpreto?
         INTERVALO 150-190.. Puedo tener valores fuera de 150-190 o no? SI..
         Ese intervalo es donde se encuentra un determinado % (el más representativo) de los datos.
         Cuál es el %? Lo ofrece la regla de Chebyshev.
            % >= 1 - 1/k^2, donde k es el número de desviaciones estándar desde la media.
            Depende de la forma de la distribución de los datos. Si es aproximadamente normal, podemos usar la regla empírica: aproximadamente el 68% de los datos están dentro de 1 desviación estándar, el 95% dentro de 2 y el 99.7% dentro de 3.

        El problema es que se refiere a la MEDIA. Si la media no es representativa del colectivo (ver a MANOLO)... la desviación típica no lo será... y no vale.
            Solo calculo la desviación típica si la media es representativa del colectivo.
    - Si opto por usar la mediana para carecterizar al colectivo , usaré medidas de dispersión asociadas como el rango semi intercuartílico (IQR) en lugar de la desviación típica. = Q3-Q1 /2 
    - Estya media tiene una interpretación SIMILAR a la desviación típica, pero aplicada a la mediana.

> Tiempos que tarda un servicio en contestar. Qué indicador uso?
   MEDIA? PROBLEMON!    Primero: No todos los datos contribuyen por igual y además es muy habitual tener outliers (valores atípicos) que distorsionan la media.
   Qué tendría más sentido: P95, P90, P50=Mediana
    Me importa cuánto tarda la mayor parte de las peticiones: Mediana
    ME importa cuánto tardan CASI TODAS LAS PETICIONES: P95, P90
    NO ME IMPORTAR si alguna petición tarda mucho más que las demás (puede se run switch saturado... o un problema puntual que no refleja el comportamiento general).


>> VillaArriba de Arriba: 10 vecinos con coches. 
  Contaminan: 5gCO/dia    5 5      10 10 10 10      15 15 15 
  Media:      10 gCO/dia
  Mediana?    10 gCO/dia

>> VillaArriba de Abajo: 10 vecinos con coches. 
  Contaminan: 5gCO/dia    5 5 5 5 5 5 5 5 5 5 Menos Manolo: 1000gCO/dia
  Media:      104.5 gCO/dia
  Mediana:    5 gCO/dia

  A la vista de ese indicador, podríamos pensar que VillaArriba de Abajo están mucho menos sensibilizados conel medio ambiente.. todo lo contrario.
  104,5 es lo que aportaría cada vecino al total si todos contribuyeran por igual.
    La media es un dato real... pero lo que no es real es que todo contribuyera por igual.

> La interpretamos mal

PORTAL de vecinos A

    170  170    170     170
                                Media:      170cm <<
                                Mediana:    170cm
                                
    0   0       0       0       Puntuación diferencial = Media - Valor
                                Media de las puntuaciones diferenciales: 0 
                                Media de los valores absolutos de las puntuaciones diferenciales: 0 < DESVIACION MEDIA
    0   0       0       0      Cuadrado de las puntuaciones diferenciales: 0
                                MEdia del cuadrado de las puntuaciones diferenciales: 0 
                                Raiz varianza para comernos el cuadrado: 0cm

PORTAL de vecinos B

    160cm  170    170     180
                                Media: 170cm
                                Mediana: 170cm
    10cm   0     0        10

                                Media de las puntuaciones diferenciales: 0
                                Media de los valores absolutos de las puntuaciones diferenciales: 5
    100cm2  0     0         100    
                                Media del cuadrado de las puntuaciones diferenciales: 50cm2    VARIANZA
                                Raiz varianza para comernos el cuadrado: 7.07cm


                                
PORTAL de vecinos C

    160  160    180     180
                                Media: 170cm
                                Mediana: 170cm  
    10   10    10     10
                                Media de las puntuaciones diferenciales: 0
                                Media de los valores absolutos de las puntuaciones diferenciales: 10
    100  100    100     100
                                Media del cuadrado de las puntuaciones diferenciales: 100
                                Raiz varianza para comernos el cuadrado: 10cm
    
                                
PORTAL de vecinosD

    150  160    180     190
                                Media: 170cm
                                Mediana: 170cm
    20   10    10     20
                                Media de las puntuaciones diferenciales: 0
                                Media de los valores absolutos de las puntuaciones diferenciales: 15
    400  100    100     400
                                Media del cuadrado de las puntuaciones diferenciales: 250
                                Raiz varianza para comernos el cuadrado: 15.81cm


PORTAL de vecinosE

    150  170    170     190
                                Media: 170cm
                                Mediana: 170cm
    20    0    0     20
                                Media de las puntuaciones diferenciales: 0
                                Media de los valores absolutos de las puntuaciones diferenciales: 10
    400  0    0     400
                                Media del cuadrado de las puntuaciones diferenciales: 200
                                Raiz varianza para comernos el cuadrado: 14.14cm

Se aprecen en algo esos portales en cuanto a la altura de sus vecinos? EN NADA... Aquí no es un problema de outliers (valores atípicos) sino de dispersión de los datos.

El objetivo es RESUMIR LOS DATOS PARA ENTENDERLOS MEJOR.
Nos está ayudando la media a entender los datos mejor? NO

RESUMIENDO:
    - Tablas de frecuencias -> Gráficos de barras o tarta
      - Solo con variables cuantitativas -> Histogramas
    - Indicadores:
      - Tendencia central:
        - Mediana     + Rango semi intercuartílico (IQR)
        - Media       + Desviación típica
      - Medidas de posición:
        - Percentiles

Pero claro.. esto es cuando analizo VARIABLE A VARIABLE! 1 variable.
Eso es útil.. pero no tanto.
NORMALMENTE QUERREMOS HACER ESTUDIOS MULTIVARIABLE. ESTO ES LO REALMENTE UTIL.
Aquí sale otro concepto: Diferencia entre DATO vs INFORMACIÓN

Qué una persona pese 150kgs qué es? UN DATO
Qué información me ofrece ese dato? MUCHA!
- Me ofrece información acerca de su peso... con gran exactitud.
- Me ofrece información acerca de su talla de ropa? EVIDENTEMENTE SI!
  - Sé que la persona NI DE COÑA tiene una talla S, ni XS, ni M, ni L, ni XL.
    Quizás no se si usa 2XL o 3X o 4XL... no tengo información EXACTA... pero si tengo INFORMACION
- Me ofrece información de sus tendencias de consumo de alimntación? MUCHA: Sé que la eprsona cn come menos de 3000 Kcal

Lo que pasa es que mucha de esa infromación no es EXACTA... Son estimaciones que hago...
Claro. Lo que pasa es que mi capacidad de estimar ( la exactitud de esas infromaciones) puede aumentar significativamente según junto variables.

Por ejemplo: 
- Si se que la persona mide 175cms... Esta rechonchete
- Si la persona mide 220cms... Me lo replanteo
- Si sé que diariamente dica 3 horas al día a hacer deporte o que decida 0 horas al día a hacer deporte.
Cuando junto datos es cuando soy capaz de EXPRIMIR, EXTRAER INFORMACIÓN VALIOSA y con cierto nivel de exactitud de los datos que tengo.

Y Aquí la cosa se empieza a complicar, cuando analizo los datos:

Si junto 2 variables:

## 2 variables nominal

TABLA DE CONTINGENCIA (como una tabla de frecuencias, pero con doble entrada)

            Entorno             Desarrollo     Pre      Pro
            HTTP StatusCode
            2XX                     187         184     12203
            3XX                     21          12       512
            4XX                     10          5         2
            5XX                     3           1         0

Otra cosa es cómo representarla en pantalla:
- Como tabla
- Estos 3, trabajan (son representaciones directas) de la tabla de frecuencias
  - Barras apiladas/agrupadas
  - Mapa térmico... es la tabla , pero las celdas las pongo en color. La intensidad es proporcional a los valores que contienen.
  - Diagrama de mosaico (mosaic plot)... es una representación gráfica de la tabla de contingencia donde el área de cada celda es proporcional a su valor.
- Diagrama de Sankey
  Estos diagramas nos ayudan a visualizar flujos y relaciones entre categorías de manera más intuitiva que una tabla de contingencia.

## 1 variable nominal y 1 variable ordinal

De entrada, como la ordinal , por definición es a su vez NOMINAL, puedo hacer lo mismo que arriba.
Pero si tengo en cuenta la capacidad ORDINAL de la variable:
- Puedo hacer un estudio de comparación de medianas
  Que puedo representar mediante un diagrama de barras

Variable ORDINAL que manejamos habitualmente en apps? NIVEL DE LOG:     DEBUG < INFO < WARN < ERROR < FATAL
    Mediana de nivel de log que tengo entre distintas apps
        En App1 -> INFO
        En App2 -> WARN

- Otra cosa que podremos hacer... pero esto ya va con truco.

    Puedo mirar el número de errores que tengo en app1, vs número de errores que tengo en app2. 
        Para qué es importante este dato? PRIORIZAR TRABAJOS!
    Lo que pasa es que realmente aí lo que estoy analizando no es una variable NOMINAL(app1/app2) y una ordinal(niveles de log),
    sino 2 variables CUANTITATIVAS:
    - Número de errores en app1
    - Número de errores en app2
    De hecho, ni siquiera son 2 variables. Es una variable: NUMERO DE ERRORES, medida en 2 colectivos diferentes: APP1, APP2 

## 1 variable nominal y 1 variable cuantitativa

Si la cuantitativa la trato como NOMINAL (que también es) , lo mismo que con 2 variables nominales.
Si la cuantitativa la trato como ORDINAL, puedo hacer comparaciones de medianas y representarlas gráficamente mediante diagramas de barras.
Si uso el poder cuantitativo de la variable (su capacidad de hacer operaciones matématicas) puedo calcular PERCENTILES y MEDIA... y puedo hacer estudios de comparación entre colectivos.

Y Qué graficas adicionales me salen aquí?
- Histograma APILADO/SUPERPUESTOS

Qué variable de CUANTITATIVA VAMOS A TENER SIEMPRE TIEMPO / FECHA?
- Lo que pasa es que al histograma de la avriable TIEMPO , datadog le da un nombre especial? TimeSeries

## 2 ordinales

Lo mismo que nominal x ordinal y que nominal x nominal

## 1 variable ordinal y 1 variable cuantitativa
Aquí poca poesia... más de lo mismo de arriba

## 2 variables cuantitativas

Qué aparece aquí nuevo? Un nuevo gráfico: Scatter plot (diagrama de dispersión)


La construcción de dashboards es SOTA, CABALLO y REY. No hay inventiva, no hay arte... Es un proceso totalmente sistemático en base a los tipos de datos que voy a representar.

# Estadística

Tipos de datos?
- Numéricos
- Texto
- Fechas
- Booleano
- ...
Esto no vale! No vale al hablar/Al plantear un dashboard.

Esos tipos de dato, son tipos de datos desde un punto de vista INFORMATICO.

Pero para montar un dashboard, hacemos uso de conceptos estadísticos.
Y en estadística los datos los clasificamos de manera diferente:

- Datos cualitativos. No son cantidades. Representan cualidades o características.                                      <- TAGS
  - Nominales. Nombres o etiquetas asociadas a nuestros datos.. Para qué sirven: CLASIFICAR
    - TIPO DE ERROR: NOMINAL
    - ENTORNO: NOMINAL
    - APLICACION QUE GENERA UN EVENTO: NOMINAL
  - Ordinales. Nombre o etiquetas asociadas a nuestros datos, pero con un orden implícito o explícito. Para qué sirven: CLASIFICAR Y ORDENAR
     Todo dato ORDINAL es por definición NOMINAL.
- Datos cuantitativos. Son cantidades.. y por ende tienen: UNIDAD DE MEDIDA, que es lo que me permite contabilizar.     <- METRICAS
     Qué puedo hacer con variables CUANTITATIVAS. Para qué sirven? CLASIFICAR y ORDENAR. Además sirven para CONTAR... Y Eso tiene una implicación: Puedo hacer ciertas operaciones matemáticas con ellas. Qué operaciones puedo hacer? Y depende del subtipo
     Cualquier variable CUANTITATIVA, por definición es a su vez ORDINAL... y por ende NOMINAL.
        Seguimos usando nombres:
         Peso: 2Kg, 3Kg, 3.17Kg

  - De razón        Tienen un cero absoluto. +, -, *, /
        Tengo 2 familias: Una tiene 2 hijos, y la otra 4.
        Es correcto decir...
        - La familia A tiene 2 hijos menos que la B? SI      RESTA
        - Entre las 2 familias tienen 6 hijos? SI      SUMA
        - Que la familia a tiene la mitad de hijos que la B? SI      MULTIPLICACION / DIVISION
        - O que la familia B tiene el doble de hijos que la A? SI      MULTIPLICACION / DIVISION
  - De intervalo    No tienen cero absoluto. +, -.. y ya!
        - Fechas (No tienen 0 absoluto... a no ser que mida desde el BIGBANG!)
          Tal y como las medimos, no hay un 0 absoluto.. De hecho hay valores negativos. 
        - Temperatura medida en grados Celsius.
          No tiene cero absoluto, ya que 0°C no significa ausencia de temperatura.
            Madrid está a 10 grados
            Barcelona está a 20 grados

            Tiene sentido decir:
            - Madrid tiene 10 grados menos que Barcelona? SI      RESTA
            - Y Que hace la mitad de temperatura que Barcelona? NO      NO
              - Cambiar las cifras:
                - Madrid -10
                - Barcelona 20
                  - Aquí qué digo, que madrid está a menos la mitad de temperatura que Barcelona? NO

                    Matemáticamente puedo hacer: 20/10 = 2
                    También puedo hacer 20/-10 = -2              Eso tiene sentido conceptual?

 - Número de hijos que tiene una familia: Ud de medida? hijo

## Ejemplos

- Código postal: Numérico, pero no es cuantitativo, no tiene unidad de medida que permita contabilizarlo.
- Aplicación que estoy monitorizando: Cualitativo
- Cantidad de veces que tenemos un HTTP status 500: Cuantitativo
- Fecha en la que ocurre algo? Una fecha en la que ocurre un http 500.
  - Cualitativo
  - Cuantitativo <<<< Y TIENE UNIDAD DE MEDIDA: DIAS QUE HAN PASADO desde el día 1 de enero del año 1
        DD / MM / YYYY 
            Las representamos así.. porque es más conveniente que decir: el día 387.294 desde el año 1
            Y entonces agrupamos al dar la fecha: 17-7-2014


Cuántos errores han aparecido en una fecha concreta:
    Lo que estás midiendo son CANTIDAD DE ERRORES: Cuantitativo
    Estás midiéndolo sobre un SUBCONJUNTO DE LOS DATOS, FILTRANDO POR FECHA. La variable fecha la estás usando para FILTRAR, no para operar.


---

# Envío de métricas a datadog.

Cuando mandamos datos, hay veces que son exactos:
- Log QUERY A BBDD -> 345ms en ejecutarse. Ese dato es exacto.

Pero esto no siempre pasa, especialmente con méticas:
Aquí hay 2 cosas:

- Número de peticiones que se han procesado en un intervalo de tiempo. Sin problema: Hacemos recuento previo en el servidor y mandamos el dato agregado.
  Ese dato es exacto
- A veces no hacemos esto.. hacemos otras cosa:
  - A veces mandamos solamente un muestreo. Mido el dato de HEAP cada 10 segundos... lo que ha pasado entre medias... lo desconozco.
    Los datos que recibo son exactos.. pero me faltan muchos datos... 
  - A veces los datos que se mandan agregados no puedo re-agregarlos
    Mido el tiempo que tarda una petición en procesarse. Pero no mando el dato.
    Los acumulo en un periodo de tiempo: 10 segundos.
    Y al final, mando la media de esos valores a datadog.
    Ese dato es exacto... pero no puedo contrastarlo tal cual / reagruparlo con otros intervalos

        Media en el instante 1 es de 100ms                  10 datos
        Y la media en el instante 2 es de 200ms              1 dato

        La media entre I1 + I2 = 150ms? No puedo decir esto. No puedo agruparlos.
        LA media de I1+I2 dependerá del número de valores que haya en cada intervalo. No puedo simplemente promediar las medias.

En datadog, esa agrupación la puede hacer el AGENTE que monto on premise, antes de enviar los datos al servidor.
ESTO ES GUAY... muchos menos datos que metemos en DATADOG... y muchos menos datos que PROCESAMOS en datadog... = MAS BARATO
Datadog es CARO! A RABIAR!

Está guay poder hacer cosas como esta... pero necesitamos entender el impacto que tiene luego.

    Podría optar por que me manden todos los datos sueltos!

Puedo manda al DATADOG: 
- 2 DATOS: I1: MEDIA 100MS
           I2: MEDIA 200MS

            Aquí no puedo calcular a posteriori la media total correctamente. No tengo la información

- 11 DATOS: 10 del I1 + 1 del I2

            Ahora sí puedo calcular la media total correctamente:
            (10 * 100ms + 1 * 200ms) / 11 = 109,09ms


El almacenamiento es caro o barato en los entornos de producción? DE LAS COSAS MAS CARAS QUE HAY!Tenemos la falsa creencia que el almacenamiento es barato.. porque lo comparamos con tiempos ancestrales.
HDD Commodore PC10 -> 50000 ptas . 300€     10 MB

Hoy en día digo... Voy al mediamarkt que no soy tonto y compro un disco de 2 Tbs por 90-100€
Ese HDD es de baja calidad. Los discos se degradas con cada lectura/escritura.
En casa que guardo 4 fotos/videos .. y los veo 2 veces al año.. me dura décadas.
En la empresa que leo / escribo de contiuo... me duran 2 semanas.                       450€

Acabamos de hacer un x5 en el precio.. y sigue siendo un HDD de calidad media.

T8 Oracle -> NVME 2tb -> 
En red pro de Wester: 550 €
Oracle lo vende por 3500€

Pero ni hemos empezado con el problema!
En producción cada dato en cuántos sitio lo guardo? Al menos en 3 lugares diferentes para garantizar la redundancia y la disponibilidad.
 x3 x5 = x15

Y ahora mete backups Que lo mismo es otro x3
x15 x3 = x45

    2Tbs que en casa cuestan 95€
    En la empresa me salen prácticamente x45 más caros = 95€ * 45 = 4275€

Y flipas... además teniendo en cuenta que n la empresa MANEJAS VOLUMENES DE DATOS MUCHO MAS GRANDES QUE EN CASA.

Es una locura el precio del almacenamiento en entornos de producción.

Datadog me cobra mucho por almacenamiento.. y cualquier cloud igual.


---


# Cuando nos ponemos a diseñar un dashboard, por dónde empezamos?

Identificar las preguntas a las que queremos contestar.
El problema es que esto lo solemos hgacer al final, cuando ya tenemos el sistema y los datos cargados.
Los datos que cargo serán los que necesito para responder a esas preguntas.
Muchas veces, cargamos datos de más.
Y en paralelo, me faltan datos que realmente necesito para responder a esas preguntas.

> Quién define lo que se muestra en los logs de la app?

La realidad es que NADIE... y de vez en cuando el desarrollador pone algunas cosas por que le vienen bien... que está teniendo algún problema y quiere depurarlo.

Y los logs, lo que sale, DEBEN SER UN REQUISITO del sistema < 

---

Pero esto tiene una derivada... Interlocutores disttintos tienen las mismas necesidades? NO

NO PUEDO TENER UN CUADRO DE MANDO UNICO para todo el mundo.
Cada interlocutor tendrá su propio dashboard adaptado a sus necesidades. CRITICO!

El objetivo del dashboard es ayudarme a entender de un vistazo lo que para mi es relevante... responder a mis preguntas de manera rápida y eficiente.
Yo no tengo media hora al día para mirar la pantalla y analizar. Necesito mirar la pantalla y que ahñi esté lo que necesito de manera inmediata.

> Desde vuestro punto de vista... A qué preguntas debería responder vuestro cuadro de mando?

- Si va todo bien? <<<< Esta la pregunta clave?
  Y en el cuadro de mando quiero aterrizarlo? Solo si va mal!

  Lo primero que necesito es que de un vistado me diga si va bien o si va mal!

  Solo si va mal.. tendré que empezar a mirar qué va mal... Y una vez que he identificado QUE VA MAL me pondré a identificar el POR QUÉ VA MAL.
    vvvv
    Si la app se va a quedar sin memoria/espacio     QUE VA MAL/POR QUÉ VA MAL

    En general la pregunta no es Si la app se va a quedar sin memoria.
    La pregunta es: ESTA LENTA la app? -> Puede ser que no tenga memoria suficiente y esté entrando mucho el GC... y me hunde el sistema

    Otra cosa es que la pregunta sea: TENGO RECURSOS SUFICIENTES COMO PARA QUE LA APP VAYA A SEGUIR FUNCIONANDO BIEN en el corto plazo?
    QUE VA MAL? No ahora... a medio plazo.

Más cosas.
Cómo sé si algo va mal?
- Tratar de hacer una operación y ver si funciona correctamente. Datos absolutos.
- REFERENCIAS! Contrastes/Comparaciones

Tendremos gráficas, tendremos indicadores, tendremos tablas.
Cómo sé si lo que sale ahí está bien o mal? con REFERENCIAS:
- Umbrales establecidos de antemano (cómo los represento: COLORES, ALERTA)
- Comparaciones con datos históricos (cómo ha evolucionado en el tiempo) Puede ser que interese meter EVENTOS
  Antes de un deploy / Despues del deploy

Entro al dashboard: 
- Y veo: P95% de transacción X del tiempo es 278ms
  Eso es bueno o malo?
    - UMBRAL. El umbral silo me dice SI / NO
    - Ver la evolución de ese P95% : Cómo estaba ayer,m Cómo estaba la última semana. Esto me da otra información adicional... Cúanto SI/Cúanto NO.
      Y las actuaciones serán distintas.

Lo que pasa es que vamos en CASCADA AL TRABAJAR.
Lo primero es saber si está bien o mal:
- UMBRAL (P95 < 200)
  Cuando ocurre que P95>200:
    - Lo primero es REFERENCIAS: Dónde estoy ?
    - A partir de ahí averiguar el por qué?


Al crear dashboards iremos teniendo PESTAÑAS... En una primera tendría que poder responder a la pregunta más básica: SI / NO tengo que seguir mirando?
El resto de pestañas acompaña, ampliando información caso que sea necesario.

Qué cosas metemos: Para saber si o no? Preguntas a contestar?
- HEALTHCHECKS.... En primera pestaña que pondría?
  - Quizás solamente:  TOTAL / OK  Si los 2 son iguales : TODO BIEN VERDE y no miro más.
  - Luego si hay problemas (ROJO) querré detalle: En otra prstaña: LISTADO DE ENPOINTS(SISTEMA) / HEALTHCHECKS
- Tiempos
    P99, P95, P50     Actuales, umbrales, tendencias
    ENDPOINT / OPERACION GRANDE / QUERY A BBDD?
        Empiezo por lo grande
- Recursos
  - Memoria             UMBRALES    TENDENCIA
     32Gbs  / 40Gbs      36Gbs         > Cuidao!
  - CPU
  - Almacenamiento
  - Tráfico de red
- LOGS???
  - Cuantos ERROR / WARNINGS por app/entorno    Valor absoluto / relativo
  - Cuantos logs (lo que pasa es que este dato está un poco contaminado por lo que esté ocurriendo el la realidad / USO DEL SISTEMA)

    TimeSries después... LO IPORTANTE AQUI NO ES SI AYER HUBO 3 errores y hoy 2.
    Lo importante es que hoy tengo 2.. y hay que mirar.

---

No me interesa saber si se estan vendiendo coches.. Me interesa saber si la operación de venta de coches funciona bien! Otra cosa, es que me invente una medida indirecta (y un tanto cutre por cierto) de cómo va la operación de venta de coches.. Y digo.. Si se están vendiendo es que la operación va bien...
Porque si no se están vendiendo, tengo respuesta a la pregunta?

QUE ENTRA AQUI? Para resolver todo estos problemas: UN MECANISMO DE TRABAJO? TEST SINTETICOS!
Tengo un robot comprando un coche de pegote.
Yo no trabajo con datos reales.