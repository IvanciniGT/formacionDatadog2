# Especificación del entorno de demo (curso Datadog) para el clúster

Para quien escribe los playbooks. Lo desplegable está en esta carpeta (`entorno/`); los ficheros de
referencia son `k8s/values.yaml` (chart de Datadog) y `k8s/app.yaml` (aplicación). Este documento
resume lo que hace falta y marca lo que está pendiente de decisión de Iván.

## Decisiones de Iván (11-10-2026)

| # | Decisión | Resultado |
|---|----------|-----------|
| a | Vía de despliegue | **CI**: una etiqueta `X.Y.Z` sobre `main` de `ivan/datadog-entorno` construye las imágenes con Kaniko, las sube a Harbor y lanza la plantilla de AWX (`.gitlab-ci.yml`, de cluster-51) |
| c | Postgres expuesto por ingress | **No**: ClusterIP |
| e | Alcance de logs/NPM/USM | logs solo del namespace `datadog-curso` (`containerInclude`); métricas de infra globales; NPM y USM activados |
| f | Registry | Harbor `registry.ivanosuna.com`, proyecto `curso`; el robot de push lo crea el repo del clúster; la credencial de pull cuelga de la cuenta por defecto del namespace (sin `imagePullSecrets`) |

Chart de Datadog: la versión está en `k8s/datadog-chart-version` (3.253.2). El playbook fuerza `datadog.operator.enabled=false`.

Contrato del playbook: baja este repo en el commit etiquetado, reescribe toda imagen cuyo nombre acabe en `shop-api` o `shop-web` a `curso/shop-*:<sha corto>`, aplica `k8s/app.yaml` y despliega el agente con `k8s/values.yaml` (release `datadog`, namespace `datadog-curso`). Límites de `app.yaml`: solo Namespace, ConfigMap, PVC, Deployment, StatefulSet, Service, Ingress, Job y CronJob; todo en `datadog-curso`; ningún Secret; Ingress solo con host `datadog.iochannel.tech`. Si se incumple, no se aplica nada y el job de CI vuelca el motivo.

## Namespace y hosts

- Namespace: `datadog-curso`.
- Ingress: `datadog.iochannel.tech` → Service `shop-web:80`, clase `ingress-public`, TLS con `cert-manager.io/cluster-issuer: letsencrypt-prod`.
- Postgres: Service `postgres:5432`, ClusterIP.

## Secretos (los crea el playbook desde ansible-vault; nada en git)

| Secret | Claves | Quién lo usa | Origen del valor |
|--------|--------|--------------|------------------|
| `datadog-keys` | `api-key`, `app-key` | chart de Datadog | Iván (org de Datadog, site EU) |
| `postgres-credentials` | `password` | postgres y shop-api | lo genera el playbook |
| `rum-credentials` | `app-id`, `client-token` | shop-web | Iván (RUM → New Application) |

## 1. Datadog Agent (Helm)

- Repo `https://helm.datadoghq.com`, chart `datadog/datadog` 2.24.x, release `datadog`, namespace `datadog-curso`.
- Values: `k8s/values.yaml` tal cual, más `--set datadog.apiKeyExistingSecret=datadog-keys --set datadog.appKeyExistingSecret=datadog-keys`.
- Resultado: DaemonSet `datadog` en los 5 nodos (toleration para control-plane), Deployment `datadog-cluster-agent`, Deployment `datadog-clusterchecks`.
- Privilegios: el contenedor `system-probe` es privilegiado con `hostPID` (eBPF para NPM/USM). El chart lo configura solo.
- Recursos por nodo (ya puestos en values): agent 256–512 Mi, process 128–256 Mi, trace 128–256 Mi, system-probe 256–512 Mi. Total requests ≈ 550 m CPU / 770 Mi por nodo.
- cri-o: `datadog.criSocketPath: /var/run/crio/crio.sock` (en values). Kubelet con `tlsVerify: false`.
- Instrumentación automática (admission controller) limitada al namespace `datadog-curso`.

Verificación: `kubectl -n datadog-curso exec ds/datadog -c agent -- agent status` sin errores en Collector; `kubectl -n datadog-curso exec deploy/datadog-clusterchecks -- agent status` muestra el check `postgres`.

## 2. Postgres

- Imagen `postgres:16`, 1 réplica, `strategy: Recreate`.
- Args: `-c shared_preload_libraries=pg_stat_statements -c track_io_timing=on -c pg_stat_statements.track=all`.
- Env: `POSTGRES_DB=shop`, `POSTGRES_USER=shop`, `POSTGRES_PASSWORD` del secret, `PGDATA=/var/lib/postgresql/data/pgdata`.
- PVC `postgres-data`, 5 Gi, `primary-nfs-class`, montado en `/var/lib/postgresql/data`.
- ConfigMap `postgres-init` con `postgres/init.sql` montado en `/docker-entrypoint-initdb.d/` (se ejecuta solo en el primer arranque; si hay que reiniciar los datos, borrar el PVC).
- Labels de pod: `tags.datadoghq.com/env=course`, `tags.datadoghq.com/service=shop-db`, `tags.datadoghq.com/version=16`.
- Annotation de pod: `ad.datadoghq.com/postgres.logs: [{"source":"postgresql","service":"shop-db"}]`.
- **Service `postgres` con la annotation del cluster check** (en `app.yaml`): el check DBM corre en el clusterchecks runner contra el Service. Usuario `datadog` / `datadog` (lo crea `init.sql`).
- Readiness: `pg_isready -U shop -d shop`. Recursos 100 m–500 m / 256–512 Mi.

## 3. shop-api

- Imagen `registry.ivanosuna.com/curso/shop-api:1.0.0` (Spring Boot, Java 21, puerto 8081; lleva dentro `dd-java-agent`).
- 2 réplicas.
- Labels de pod: `app=shop-api`, `tags.datadoghq.com/{env,service,version}` = `course`, `shop-api`, `<versión>`, `admission.datadoghq.com/enabled="true"`.
  **La versión se escribe solo en la label** `tags.datadoghq.com/version`, y el pipeline la pone igual a la etiqueta del despliegue. `DD_SERVICE`, `DD_ENV` y `DD_VERSION` la leen de las labels con `fieldRef` (downward API): no hay valores repetidos.
- Annotation: `ad.datadoghq.com/shop-api.logs: [{"source":"java","service":"shop-api"}]`.
- Env: `DB_HOST=postgres`, `DB_NAME=shop`, `DB_USER=shop`, `DB_PASSWORD` del secret, `DD_AGENT_HOST` = `status.hostIP` (fieldRef), `DD_LOGS_INJECTION=true`, `DD_TRACE_SAMPLE_RATE=1`, `DD_PROFILING_ENABLED=true`, `DD_DBM_PROPAGATION_MODE=full`.
- Sondas: readiness `GET /actuator/health/readiness` (delay 20 s), liveness `GET /actuator/health/liveness` (delay 40 s).
- Recursos: 250 m–1 CPU / 512–768 Mi. Service `shop-api:8081`.

## 4. shop-web

- Imagen `registry.ivanosuna.com/curso/shop-web:1.0.0` (nginx; sirve la página con el SDK de RUM y hace proxy de `/api` a `shop-api:8081`).
- 1 réplica. Labels `tags.datadoghq.com/*` = `course` / `shop-web` / `<versión>` (misma regla: la versión solo en la label, la pone el pipeline). Annotation de logs `source: nginx`.
- Env: `DD_SITE=datadoghq.eu`, `DD_ENV` y `DD_VERSION` leídas de las labels, `DD_RUM_APP_ID` y `DD_RUM_CLIENT_TOKEN` del secret `rum-credentials` (el entrypoint genera `rum-config.js` con ellos).
- Readiness `GET /rum-config.js`. Recursos 50–200 m / 64–128 Mi. Service `shop-web:80`. Ingress descrito arriba.

## 5. load

- Imagen `curlimages/curl:8.10.1`, 1 réplica, comando `/bin/sh /scripts/generate.sh` con el script de `load/generate.sh` en un ConfigMap.
- Env `TARGET=http://shop-web`, `PAUSE=2`. Recursos 20–100 m / 32–64 Mi.
- Label `tags.datadoghq.com/service=load` (para poder excluir sus logs en clase).

## Orden y comprobaciones

1. Namespace y secrets.
2. Postgres (esperar readiness).
3. Chart de Datadog (puede ir antes; el orden no importa salvo que el admission controller debe existir antes que shop-api para inyectar las variables).
4. shop-api, shop-web, ingress, load.
5. Comprobar: `curl https://datadog.iochannel.tech/api/products` devuelve JSON; en Datadog aparecen el clúster, los pods del namespace, el servicio `shop-api` en APM, logs con `kube_namespace:datadog-curso`, el host Postgres en DBM, y sesiones RUM al abrir la web.

## Desinstalación (al acabar el curso)

`helm uninstall datadog -n datadog-curso`, borrar el namespace (incluye el PVC), borrar las imágenes de Harbor si se quiere.
