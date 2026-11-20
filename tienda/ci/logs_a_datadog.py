#!/usr/bin/env python3
"""
Manda a Datadog Logs la salida de todos los jobs de un pipeline.

POR QUE EXISTE: la recogida nativa de logs de jobs de Datadog DESCARGA cada log del
almacenamiento de objetos de GitLab con una URL prefirmada, y el de este GitLab es un MinIO
interno que Datadog no alcanza desde Internet: GitLab avisa, Datadog contesta ok, y el log
nunca llega. Esto hace el camino al reves: lee las trazas con la API de GitLab y las empuja a
la ingesta de logs.

Lleva las etiquetas de la recogida nativa (datadog.product:cipipeline, source:gitlab) y los
identificadores de pipeline y job para filtrar por ellos. Que CI Visibility las enlace con su
pipeline como hace con las suyas NO esta garantizado.

Variables: CI_API_V4_URL, CI_PROJECT_ID, CI_PIPELINE_ID, CI_JOB_ID, CI_PROJECT_PATH,
CI_COMMIT_SHA, CI_COMMIT_REF_NAME (las pone GitLab), GITLAB_TOKEN_LOGS (token de proyecto con
read_api), DD_API_KEY y DD_SITE.
"""
import json, os, re, sys, urllib.request
from datetime import datetime

GITLAB = os.environ["CI_API_V4_URL"]
PROYECTO = os.environ["CI_PROJECT_ID"]
PIPELINE = os.environ["CI_PIPELINE_ID"]
ESTE_JOB = os.environ.get("CI_JOB_ID", "")
TOKEN = os.environ["GITLAB_TOKEN_LOGS"]
INTAKE = "https://http-intake.logs.%s/api/v2/logs" % os.environ.get("DD_SITE", "datadoghq.eu")
DD_API_KEY = os.environ["DD_API_KEY"]

# Colores ANSI y marcas de seccion de GitLab: ensucian el mensaje y rompen las busquedas.
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|section_(?:start|end):\d+:[\w.\[\]=,-]+\r?")
# El runner antepone a cada linea su hora y el flujo: «2026-11-20T07:03:39.003407Z 01O ».
PREFIJO = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z) \d\d[OE]\+? ?")
LOTE = 500   # la ingesta admite 1000 entradas y 5 MB por peticion: margen de sobra
TERMINADOS = ("success", "failed", "canceled")


def gitlab(ruta, crudo=False):
    req = urllib.request.Request(GITLAB + ruta, headers={"PRIVATE-TOKEN": TOKEN})
    with urllib.request.urlopen(req, timeout=30) as r:
        datos = r.read()
    return datos.decode("utf-8", "replace") if crudo else json.loads(datos)


def enviar(entradas):
    req = urllib.request.Request(INTAKE, method="POST", data=json.dumps(entradas).encode(),
                                 headers={"DD-API-KEY": DD_API_KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status != 202:
            raise RuntimeError("la ingesta de logs contesto %s" % r.status)


def lineas(traza):
    for cruda in traza.splitlines():
        texto = ANSI.sub("", cruda).rstrip()
        hora = None
        m = PREFIJO.match(texto)
        if m:
            hora, texto = m.group(1), texto[m.end():]
        if texto.strip():
            yield hora, texto


def a_milisegundos(hora):
    # fromisoformat entiende la Z desde Python 3.11; el runner pone mas de 6 decimales.
    return int(datetime.fromisoformat(re.sub(r"(\.\d{6})\d*", r"\1", hora)).timestamp() * 1000)


def main():
    jobs = gitlab("/projects/%s/pipelines/%s/jobs?per_page=100&include_retried=true" % (PROYECTO, PIPELINE))
    total = enviados = 0
    for job in jobs:
        if str(job["id"]) == ESTE_JOB or job["status"] not in TERMINADOS:
            continue
        etiquetas = ",".join([
            "datadog.product:cipipeline", "source:gitlab", "env:course",
            "ci.pipeline.id:%s" % PIPELINE, "ci.job.name:%s" % job["name"],
            "ci.job.id:%s" % job["id"], "ci.status:%s" % job["status"]])
        comun = {
            "ddsource": "gitlab", "service": "datadog-entorno", "hostname": "gitlab-runner",
            "ddtags": etiquetas, "status": "error" if job["status"] == "failed" else "info",
            "ci": {"provider": {"name": "gitlab"},
                   "pipeline": {"id": PIPELINE, "name": os.environ.get("CI_PROJECT_PATH", "")},
                   "job": {"id": str(job["id"]), "name": job["name"], "stage": job["stage"],
                           "status": job["status"], "url": job["web_url"]}},
            "git": {"commit": {"sha": os.environ.get("CI_COMMIT_SHA", "")},
                    "branch": os.environ.get("CI_COMMIT_REF_NAME", "")},
        }
        lote = []
        for hora, texto in lineas(gitlab("/projects/%s/jobs/%s/trace" % (PROYECTO, job["id"]), crudo=True)):
            entrada = dict(comun, message=texto)
            if hora:
                entrada["timestamp"] = a_milisegundos(hora)
            lote.append(entrada)
            if len(lote) == LOTE:
                enviar(lote); total += len(lote); lote = []
        if lote:
            enviar(lote); total += len(lote)
        enviados += 1
        print("LOGS> %-20s %-8s enviado" % (job["name"], job["status"]))
    print("LOGS> %d lineas de %d jobs del pipeline %s" % (total, enviados, PIPELINE))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:   # sin ocultar el motivo: el job queda en naranja y lo dice
        print("NO SE MANDARON LOS LOGS: %s" % e)
        sys.exit(1)
