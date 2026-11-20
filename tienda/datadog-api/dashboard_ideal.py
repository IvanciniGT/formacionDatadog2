#!/usr/bin/env python3
"""
El dashboard ideal: se construye por pestañas, en clase y pieza a pieza, para enseñar qué es
hacer un dashboard. Cada widget se titula con la PREGUNTA a la que responde y lleva como
descripción el tipo de gráfico, porque lo que se enseña es elegir el gráfico a partir de la
pregunta y no al revés.

Crea o actualiza (por nombre) los monitores que usa, todos con la etiqueta uso:dashboard, y
después el dashboard. Necesita DD_API_KEY y DD_APP_KEY en el entorno.

  python3 dashboard_ideal.py
"""
import uuid

from create_reference import call

TITULO = "El dashboard ideal — tienda"
WEB = "https://datadog.iochannel.tech"
UBICACIONES = ["aws:eu-central-1", "aws:eu-west-1", "aws:eu-west-3"]
ETIQUETAS = ["uso:dashboard", "env:course", "owner:ivan", "managed-by:script"]

# Sin @destinatario: estos monitores son para mirarlos, no para despertar a nadie. A quién se
# avisa es otra lección.
AVISO = """{{#is_alert}}🔴 %s{{/is_alert}}
{{#is_recovery}}🟢 Recuperado{{/is_recovery}}"""


# ----------------------------------------------------------------------------- monitores
def sintetico(nombre, componente, servicio, ruta, aserciones, aviso):
    return {
        "name": nombre, "type": "api", "subtype": "http", "status": "live",
        "config": {"request": {"method": "GET", "url": WEB + ruta, "timeout": 10},
                   "assertions": [{"type": "statusCode", "operator": "is", "target": 200}] + aserciones},
        "locations": UBICACIONES,
        # Que fallen 2 de 3 ubicaciones y con un reintento: una sola sonda con mala red no es
        # una caída, y un monitor del vistazo que parpadea enseña a ignorarlo.
        "options": {"tick_every": 60, "min_location_failed": 2, "min_failure_duration": 0,
                    "retry": {"count": 1, "interval": 10000},
                    "monitor_options": {"renotify_interval": 0}},
        "message": AVISO % aviso,
        "tags": ETIQUETAS + ["componente:" + componente, "service:" + servicio],
    }


SINTETICOS = [
    sintetico("Web operativa", "web", "shop-web", "/",
              [{"type": "body", "operator": "contains", "target": "<title>Shop demo</title>"},
               {"type": "responseTime", "operator": "lessThan", "target": 3000}],
              "La tienda no carga para los clientes"),
    # readiness y no /actuator/health: ese incluye la base de datos, y entonces una caída de
    # Postgres pondría en rojo también el backend y el vistazo no diría cuál de los dos es.
    sintetico("Backend operativo", "backend", "shop-api", "/actuator/health/readiness",
              [{"type": "body", "operator": "validatesJSONPath",
                "target": {"jsonPath": "$.status", "operator": "is", "targetValue": "UP"}}],
              "El backend no está listo para atender peticiones"),
]

BBDD = {
    "name": "BBDD operativa", "type": "service check",
    # El service check del agente: intenta conectarse de verdad, cada 15 s. La base no está
    # expuesta a Internet, así que un sintético no llegaría.
    "query": '"postgres.can_connect".over("service:shop-db").by("*").last(2).count_by_status()',
    "message": AVISO % "El agente no consigue conectarse a Postgres",
    "tags": ETIQUETAS + ["componente:bbdd", "service:shop-db"],
    "options": {"thresholds": {"critical": 1, "ok": 1}, "notify_no_data": True, "no_data_timeframe": 5,
                "renotify_interval": 0},
}


def alta_disponibilidad(nombre, componente, servicio, deployment):
    f = "{kube_namespace:datadog-curso,kube_deployment:%s}" % deployment
    return {
        "name": "Alta disponibilidad: " + nombre, "type": "query alert",
        # Pods que faltan = deseados - disponibles. Con min() sobre 5 minutos solo salta si
        # falta alguno durante TODA la ventana: un despliegue rolling quita y pone pods y no es
        # una pérdida de disponibilidad.
        "query": "min(last_5m):avg:kubernetes_state.deployment.replicas_desired%s - "
                 "avg:kubernetes_state.deployment.replicas_available%s > 0" % (f, f),
        "message": AVISO % ("Faltan {{value}} pods de %s por estar disponibles" % deployment),
        "tags": ETIQUETAS + ["componente:" + componente, "service:" + servicio],
        "options": {"thresholds": {"critical": 0}, "notify_no_data": True, "no_data_timeframe": 10,
                    "require_full_window": False, "renotify_interval": 0},
    }


ALTA_DISPONIBILIDAD = [
    alta_disponibilidad("web", "web", "shop-web", "shop-web"),
    alta_disponibilidad("backend", "backend", "shop-api", "shop-api"),
    alta_disponibilidad("BBDD", "bbdd", "shop-db", "postgres"),
]


API = "env:course,service:shop-api"
SIN_HEALTH = ",!resource_name:get_/actuator/health,!resource_name:get_/actuator/health/"

CALIDAD = [
    {"name": "QoS: tiempo de respuesta del backend", "type": "query alert",
     # Sin los health checks: son 180 llamadas de 2 ms cada 5 minutos y bajan el p95 hasta
     # esconder que los clientes esperan.
     "query": "avg(last_5m):p95:trace.servlet.request{%s%s} > 0.2" % (API, SIN_HEALTH),
     "message": AVISO % "El 5 %% más lento de las peticiones tarda {{value}} s (umbral 200 ms)",
     "tags": ETIQUETAS + ["componente:backend", "service:shop-api"],
     "options": {"thresholds": {"critical": 0.2, "warning": 0.15}, "notify_no_data": False,
                 "require_full_window": False, "renotify_interval": 0}},
    {"name": "Fallos del backend (5xx)", "type": "query alert",
     # .errors de un span de servidor son las respuestas 5xx. Un fallo ya es malo: umbral > 0.
     # default_zero, porque sin fallos la serie no existe y el monitor quedaría en No Data.
     "query": "sum(last_5m):default_zero(sum:trace.servlet.request.errors{%s}.as_count()) > 0" % API,
     "message": AVISO % "{{value}} respuestas 5xx en 5 minutos",
     "tags": ETIQUETAS + ["componente:backend", "service:shop-api"],
     "options": {"thresholds": {"critical": 0}, "notify_no_data": False,
                 "require_full_window": False, "renotify_interval": 0}},
    {"name": "Fallos de la BBDD", "type": "trace-analytics alert",
     # Consultas SQL que fallan, vistas desde la aplicación: los spans postgresql.query con
     # error. Se cuentan spans y no una métrica porque la métrica .errors no existe mientras no
     # haya fallos, y un recuento de spans sin coincidencias sí da 0.
     "query": 'trace-analytics("env:course service:shop-api operation_name:postgresql.query status:error")'
              '.rollup("count").last("5m") > 0',
     "message": AVISO % "{{value}} consultas a la base de datos han fallado en 5 minutos",
     "tags": ETIQUETAS + ["componente:bbdd", "service:shop-db"],
     "options": {"thresholds": {"critical": 0}, "notify_no_data": False,
                 "require_full_window": False, "renotify_interval": 0}},
]


def asegurar_sinteticos():
    existentes = {t["name"]: t["public_id"] for t in (call("GET", "/api/v1/synthetics/tests") or {}).get("tests", [])}
    ids = []
    for t in SINTETICOS:
        if t["name"] in existentes:
            r = call("PUT", "/api/v1/synthetics/tests/api/" + existentes[t["name"]], t)
        else:
            r = call("POST", "/api/v1/synthetics/tests/api", t)
        print("  sintético", t["name"], r and r["public_id"], "monitor", r and r["monitor_id"])
        ids.append(r["monitor_id"])
    return ids


def asegurar_monitor(m):
    existentes = {x["name"]: x["id"] for x in (call("GET", "/api/v1/monitor?page_size=1000") or [])}
    if m["name"] in existentes:
        r = call("PUT", "/api/v1/monitor/%d" % existentes[m["name"]], m)
    else:
        r = call("POST", "/api/v1/monitor", m)
    print("  monitor", m["name"], r and r["id"])
    return r["id"]


# ----------------------------------------------------------------------------- widgets
def estado(pregunta, componente, ancho=3, alto=2):
    """Monitores, en lista y con su color. Se filtra por etiqueta y no por id para que el
    widget siga valiendo si un monitor se borra y se crea otra vez."""
    return {"definition": {
        "type": "manage_status", "title": pregunta, "description": "Monitor Summary",
        "query": "tag:uso:dashboard" + ("" if componente == "*" else " tag:componente:" + componente),
        "summary_type": "monitors", "display_format": "countsAndList", "color_preference": "background",
        "hide_zero_counts": True, "show_last_triggered": True, "show_priority": False,
        "sort": "status,asc", "count": 50, "start": 0},
        "layout": {"x": 0, "y": 0, "width": ancho, "height": alto}}


def mapa(pregunta, servicio, ancho=6, alto=6):
    return {"definition": {
        "type": "topology_map", "title": pregunta, "description": "Topology Map",
        "requests": [{"request_type": "topology",
                      "query": {"data_source": "service_map", "service": servicio, "filters": ["env:course"]}}]},
        "layout": {"x": 0, "y": 0, "width": ancho, "height": alto}}


def cifra(pregunta, consulta, unidad, ancho=4, alto=2):
    """Un número grande con la tendencia detrás. consulta es un dict de query de la API. Las
    métricas van con default_zero EN LA FÓRMULA (dentro de la consulta la API lo acepta pero la
    interfaz dice «invalid formula in query object»): sin datos el widget pinta «No data» en vez de 0 y entonces
    no se colorea, que es justo el caso que tiene que salir en rojo."""
    return {"definition": {
        "type": "query_value", "title": pregunta, "description": "Query Value",
        "autoscale": True, "precision": 0, "custom_unit": unidad,
        "timeseries_background": {"type": "area"},
        "requests": [{"response_format": "scalar", "queries": [consulta],
                      "formulas": [{"formula": "default_zero(a)" if consulta["data_source"] == "metrics" else "a"}],
                      # Cero peticiones es que la pieza no recibe tráfico: rojo. Cualquier otra
                      # cosa, verde. En el Query Value las reglas van en la request, no en la
                      # fórmula: ahí la API las acepta y la interfaz las ignora.
                      "conditional_formats": [
                          {"comparator": "<=", "value": 0, "palette": "white_on_red"},
                          {"comparator": ">", "value": 0, "palette": "white_on_green"}]}]},
        "layout": {"x": 0, "y": 0, "width": ancho, "height": alto}}


def metrica(consulta, agregador="sum"):
    return {"name": "a", "data_source": "metrics", "query": consulta, "aggregator": agregador}


def logs(busqueda):
    return {"name": "a", "data_source": "logs", "indexes": ["*"],
            "search": {"query": busqueda}, "compute": {"aggregation": "count"}}


CLUSTER = "kube_cluster_name:iochannel-cluster"
# Todo el namespace menos el propio Datadog: los agentes son la herramienta, no la tienda.
PODS = ("kube_namespace:datadog-curso,!kube_daemon_set:datadog,"
        "!kube_deployment:datadog-cluster-agent,!kube_deployment:datadog-clusterchecks")


def q(nombre, consulta, agregador="avg"):
    return {"name": nombre, "data_source": "metrics", "query": consulta, "aggregator": agregador}


def columna(formula, alias, unidad=None, barra=False, aviso=None, malo=None):
    c = {"formula": formula, "alias": alias}
    if barra:
        c["cell_display_mode"] = "bar"
    if unidad:
        c["number_format"] = {"unit": {"type": "canonical_unit", "unit_name": unidad}}
    if aviso is not None:
        c["conditional_formats"] = [{"comparator": ">=", "value": malo, "palette": "white_on_red"},
                                    {"comparator": ">=", "value": aviso, "palette": "white_on_yellow"},
                                    {"comparator": "<", "value": aviso, "palette": "white_on_green"}]
    return c


def tabla(pregunta, consultas, columnas, ancho=6, alto=5):
    return {"definition": {
        "type": "query_table", "title": pregunta, "description": "Table", "has_search_bar": "never",
        "requests": [{"response_format": "scalar", "queries": consultas, "formulas": columnas,
                      "sort": {"count": 50, "order_by": [{"type": "formula", "index": 0, "order": "desc"}]}}]},
        "layout": {"x": 0, "y": 0, "width": ancho, "height": alto}}


def mapa_hosts(pregunta, tipo, ambito, agrupar, relleno, tamano, ancho=6, alto=5):
    return {"definition": {
        "type": "hostmap", "title": pregunta, "description": "Host Map" if tipo == "host" else "Container Map",
        "node_type": tipo, "scope": ambito, "group": agrupar, "no_group_hosts": True, "no_metric_hosts": True,
        "requests": {"fill": {"q": relleno}, "size": {"q": tamano}},
        "style": {"palette": "green_to_orange", "palette_flip": False}},
        "layout": {"x": 0, "y": 0, "width": ancho, "height": alto}}


BACKEND = "kube_namespace:datadog-curso,kube_deployment:shop-api"


def linea(consulta, alias, paleta, trazo="solid"):
    return {"response_format": "timeseries", "display_type": "line",
            "queries": [{"name": "a", "data_source": "metrics", "query": consulta}],
            "formulas": [{"formula": "a", "alias": alias}],
            "style": {"palette": paleta, "line_type": trazo, "line_width": "normal"}}


# Las barras verticales de los despliegues de la tienda: lo primero que se pregunta ante un pico
# es si empezó con un despliegue.
DESPLIEGUES = [{"q": "source:kubernetes kube_namespace:datadog-curso kube_deployment IN (shop-api,shop-web,postgres)",
                "tags_execution": "and"},
               {"q": "evento:despliegue env:course source:change_tracking", "tags_execution": "and"}]


def serie(pregunta, peticiones, ancho=12, alto=4, marcadores=None, despliegues=False):
    d = {"type": "timeseries", "title": pregunta, "description": "Timeseries",
         "show_legend": True, "legend_layout": "horizontal", "legend_columns": ["avg", "max", "value"],
         "yaxis": {"include_zero": True}, "requests": peticiones}
    if marcadores:
        d["markers"] = marcadores
    if despliegues:
        d["events"] = DESPLIEGUES
    return {"definition": d, "layout": {"x": 0, "y": 0, "width": ancho, "height": alto}}


def peticion(consultas, formula, alias, paleta, tipo="line"):
    """Una request de serie temporal con varias consultas (a, b...) combinadas en una fórmula."""
    return {"response_format": "timeseries", "display_type": tipo,
            "queries": [{"name": n, "data_source": "metrics", "query": c} for n, c in consultas],
            "formulas": [{"formula": formula, "alias": alias}],
            "style": {"palette": paleta, "line_type": "solid", "line_width": "normal"}}


# Lo que ha pasado en la tienda: eventos de Kubernetes de sus deployments (despliegues,
# reinicios, OOM...) y los cambios de estado de los monitores del dashboard.
CAMBIOS = [{"q": "source:kubernetes kube_namespace:datadog-curso kube_deployment IN (shop-api,shop-web,postgres)",
            "tags_execution": "and"},
           {"q": "source:alert uso:dashboard", "tags_execution": "and"},
           # Los despliegues que anuncia la pipeline (job evento-version). Cada envio deja dos
           # eventos, el original y el de Change Tracking: con este basta una barra.
           {"q": "evento:despliegue env:course source:change_tracking", "tags_execution": "and"},
           # Los de negocio (botón de campaña): ¿se movió el tráfico por algo que hizo marketing?
           {"q": "evento:negocio env:course", "tags_execution": "and"}]


def cambios():
    w = serie("¿Qué ha cambiado, y ha afectado a los errores o a los tiempos?", [
        peticion([("a", "sum:trace.servlet.request.errors{%s} .as_count()".replace(" ", "") % API)],
                 "a", "Errores 5xx", "warm", "bars"),
        peticion([("a", "p95:trace.servlet.request{%s%s}" % (API, SIN_HEALTH))], "a", "p95 (s)", "cool"),
    ], ancho=6, alto=6)
    # Los tiempos a la derecha: segundos y número de errores en el mismo eje aplastan uno de los dos.
    w["definition"]["requests"][1]["on_right_yaxis"] = True
    w["definition"]["right_yaxis"] = {"include_zero": True}
    w["definition"]["events"] = CAMBIOS
    w["layout"].update({"x": 6, "y": 8, "fijo": True})
    return w


def calidad_del_servicio():
    sin_health = "{%s%s}" % (API, SIN_HEALTH)
    sinteticos = "{uso:dashboard%s} by {componente}"
    return grupo("Calidad del servicio", [
        serie("¿Cuánto tardan en responder las peticiones del backend?", [
            peticion([("a", "p50:trace.servlet.request" + sin_health)], "a", "Mediana", "cool"),
            peticion([("a", "p95:trace.servlet.request" + sin_health)], "a", "p95", "warm"),
            peticion([("a", "p99:trace.servlet.request" + sin_health)], "a", "p99", "orange"),
        ], ancho=6, alto=4, despliegues=True,
            marcadores=[{"value": "y = 0.2", "display_type": "error dashed", "label": "objetivo 200 ms"}]),
        # Por endpoint y no un total: para desarrollo la pregunta siguiente siempre es «¿cuál?».
        serie("¿Cuántos errores 5xx hay, y en qué endpoint?", [
            peticion([("a", "sum:trace.servlet.request.errors{%s} by {resource_name}.as_count()" % API)],
                     "a", "Errores", "warm", "bars"),
        ], ancho=6, alto=4, despliegues=True),
        # % de ejecuciones de los sintéticos que fallan: es la indisponibilidad vista desde
        # fuera, como la ve un cliente. La BBDD no está: no tiene sintético, solo service check.
        serie("¿Ha estado caída la web o el backend, y cuánto?", [
            peticion([("a", "sum:synthetics.test_runs" + sinteticos % ",status:failure" + ".as_count()"),
                      ("b", "sum:synthetics.test_runs" + sinteticos % "" + ".as_count()")],
                     "default_zero(a) / b * 100", "% de comprobaciones fallidas", "red", "bars"),
        ], ancho=6, alto=3),
        # restarts es un contador acumulado: monotonic_diff deja solo los reinicios nuevos de
        # cada intervalo, y no se lía cuando un pod nuevo empieza otra vez desde 0.
        serie("¿Se ha reiniciado algún pod?", [
            peticion([("a", "max:kubernetes.containers.restarts{%s} by {pod_name}" % PODS)],
                     "monotonic_diff(a)", "Reinicios", "purple", "bars"),
        ], ancho=6, alto=3, despliegues=True),
    ], color="vivid_green")


def maquinas_y_pods():
    nodo = "{%s} by {host}" % CLUSTER
    pod = "{%s} by {pod_name}" % PODS
    return grupo("Máquinas y pods", [
        mapa_hosts("¿Qué nodo está más cargado?", "host", [CLUSTER], [],
                   "avg:system.cpu.user{%s} by {host}" % CLUSTER,
                   "avg:system.mem.used{%s} by {host}" % CLUSTER),
        # Un hexágono por contenedor, sin sumar réplicas: es donde se ve si UN pod va distinto.
        # El scope del mapa no admite negaciones: los agentes se quitan en las consultas, y
        # no_metric_hosts esconde los contenedores que se quedan sin datos.
        mapa_hosts("¿Qué pod está más cargado?", "container", ["kube_namespace:datadog-curso"], ["kube_deployment"],
                   "avg:container.cpu.usage{%s} by {host}" % PODS,
                   "avg:container.memory.usage{%s} by {host}" % PODS),
        tabla("¿Le queda CPU, RAM y disco a cada nodo?",
              [q("a", "avg:system.cpu.idle" + nodo), q("b", "avg:system.mem.pct_usable" + nodo),
               q("c", "max:system.disk.in_use" + nodo, "max")],
              [columna("100 - a", "CPU %", "percent", True, 70, 90),
               columna("(1 - b) * 100", "RAM %", "percent", True, 80, 90),
               # El disco más lleno de cada nodo: es el que se llena primero.
               columna("c * 100", "Disco %", "percent", True, 80, 90)]),
        # Porcentajes sobre el LÍMITE del contenedor, que es donde Kubernetes estrangula la CPU
        # y mata por memoria; sobre el nodo no dirían nada del pod.
        tabla("¿Está cada pod cerca de sus límites?",
              [q("a", "sum:kubernetes.cpu.usage.total" + pod), q("b", "sum:kubernetes.cpu.limits" + pod),
               q("c", "sum:kubernetes.memory.working_set" + pod), q("d", "sum:kubernetes.memory.limits" + pod),
               q("e", "sum:kubernetes.ephemeral_storage.usage" + pod),
               q("f", "sum:kubernetes.containers.restarts" + pod, "last")],
              [columna("a / (b * 1000000000) * 100", "CPU % del límite", "percent", True, 70, 90),
               columna("c / d * 100", "RAM % del límite", "percent", True, 80, 90),
               # El PVC de Postgres va por NFS y el kubelet informa del disco ENTERO del servidor
               # (934 GB), no de la carpeta del pod: por eso aquí solo el disco efímero.
               columna("e", "Disco efímero", "byte"),
               columna("f", "Reinicios")]),
        # Las cinco medidas juntas porque se explican unas a otras: lo que el pod pide y su
        # techo, lo que gasta, y qué parte de eso es heap y qué no (metaspace, hilos, el
        # agente). Media por pod y no una línea por réplica: con dos réplicas ya eran ocho
        # líneas y no se leía. avg y no sum, para que se compare con el límite de UN pod.
        serie("¿Cómo se reparte la memoria del backend, y cuánto le queda?", [
            linea("avg:kubernetes.memory.limits{%s}" % BACKEND, "Límite", "warm", "dashed"),
            linea("avg:kubernetes.memory.requests{%s}" % BACKEND, "Request", "grey", "dotted"),
            linea("avg:kubernetes.memory.working_set{%s}" % BACKEND, "Uso del pod", "purple"),
            linea("avg:jvm.heap_memory{%s}" % API, "Heap", "cool"),
            linea("avg:jvm.non_heap_memory{%s}" % API, "No heap", "green"),
        ]),
    ], color="vivid_purple")


def sesiones(pregunta, filtro, alias, paleta, ancho=6, alto=3):
    """Sesiones RUM distintas por intervalo. Sesiones y no @usr.id: los humanos no se
    identifican y todos los robots comparten el usuario «synthetic», así que contar usuarios
    daría 0 y 1."""
    return {"definition": {
        "type": "timeseries", "title": pregunta, "description": "Timeseries", "show_legend": False,
        "yaxis": {"include_zero": True},
        "requests": [{"response_format": "timeseries", "display_type": "area",
                      "queries": [{"name": "a", "data_source": "rum", "indexes": ["*"],
                                   "search": {"query": "@application.name:shop-web " + filtro},
                                   "compute": {"aggregation": "cardinality", "metric": "@session.id"}}],
                      "formulas": [{"formula": "a", "alias": alias}],
                      "style": {"palette": paleta, "line_type": "solid", "line_width": "normal"}}]},
        "layout": {"x": 0, "y": 0, "width": ancho, "height": alto, "fila_nueva": True}}


def grupo(titulo, widgets, color="vivid_blue"):
    """Coloca los widgets de izquierda a derecha y salta de fila al llenar las 12 columnas, o
    antes si el widget lo pide con fila_nueva (para apilar en la columna izquierda). Un widget
    con fijo conserva su posición y solo cuenta para la altura del grupo."""
    x = y = alto_fila = 0
    for w in widgets:
        l = w["layout"]
        if l.pop("fijo", False):
            # Ya trae su x/y: es el que ocupa el hueco al lado de una columna apilada.
            alto_fila = max(alto_fila, l["y"] + l["height"] - y)
            continue
        if l.pop("fila_nueva", False) or x + l["width"] > 12:
            x, y, alto_fila = 0, y + alto_fila, 0
        l["x"], l["y"] = x, y
        x += l["width"]
        alto_fila = max(alto_fila, l["height"])
    return {"definition": {"type": "group", "title": titulo, "background_color": color,
                           "layout_type": "ordered", "show_title": True, "widgets": widgets},
            "layout": {"x": 0, "y": 0, "width": 12, "height": 1 + y + alto_fila}}


def pestana_estado():
    # Las tres cifras sin health checks: son de las sondas, no de clientes, y con 180 cada
    # 5 minutos se comen la cuenta cuando hay poco tráfico.
    return [
        grupo("De un vistazo", [
            estado("¿Funciona la tienda, y si no, qué pieza falla?", "*", ancho=6, alto=6),
            mapa("¿Quién llama a quién, y dónde se producen los errores?", "shop-api"),
            cifra("¿Cuántas peticiones recibe la web?",
                  logs("service:shop-web -@uri:\\/actuator*"), "peticiones"),
            cifra("¿Cuántas peticiones recibe el backend?",
                  metrica("sum:trace.servlet.request.hits{%s%s}.as_count()" % (API, SIN_HEALTH)), "peticiones"),
            cifra("¿Cuántas consultas recibe la base de datos?",
                  metrica("sum:trace.postgresql.query.hits{%s}.as_count()" % API), "consultas"),
            sesiones("¿Cuántas personas están usando la tienda?", "@session.type:user", "Humanos", "green"),
            # Hoy son las sesiones de los sintéticos de navegador; si algún día entra un crawler
            # con el SDK de RUM, saldría aquí también.
            sesiones("¿Cuántos robots están usando la tienda?", "-@session.type:user", "No humanos", "grey"),
            cambios(),
        ]),
        calidad_del_servicio(),
        maquinas_y_pods(),
    ]


PESTANAS = [("1. Estado de los servicios", pestana_estado)]


def cuerpo():
    widgets, pestanas, siguiente = [], [], 1
    y = 0
    for nombre, construir in PESTANAS:
        ids = []
        for w in construir():
            # El id lo ponemos nosotros: las pestañas apuntan a los widgets por id.
            w["id"] = siguiente
            for hijo in w["definition"].get("widgets", []):
                siguiente += 1
                hijo["id"] = siguiente
            w["layout"]["y"] = y
            y += w["layout"]["height"]
            ids.append(w["id"])
            widgets.append(w)
            siguiente += 1
        pestanas.append({"id": str(uuid.uuid5(uuid.NAMESPACE_URL, TITULO + nombre)), "name": nombre, "widget_ids": ids})
    return {"title": TITULO, "layout_type": "ordered", "reflow_type": "fixed",
            "description": "Cada widget responde a una pregunta: su título. Debajo, el tipo de gráfico que la contesta.",
            "widgets": widgets, "tabs": pestanas}


def asegurar_dashboard():
    existentes = {d["title"]: d["id"] for d in (call("GET", "/api/v1/dashboard") or {}).get("dashboards", [])}
    b = cuerpo()
    if TITULO in existentes:
        r = call("PUT", "/api/v1/dashboard/" + existentes[TITULO], b)
    else:
        r = call("POST", "/api/v1/dashboard", b)
    print("  dashboard", r and "https://app.datadoghq.eu" + r["url"])


if __name__ == "__main__":
    print("monitores")
    asegurar_sinteticos()
    asegurar_monitor(BBDD)
    for m in ALTA_DISPONIBILIDAD + CALIDAD:
        asegurar_monitor(m)
    print("dashboard")
    asegurar_dashboard()
