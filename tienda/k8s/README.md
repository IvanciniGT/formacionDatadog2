# Demo stack on Kubernetes

Same five pieces as the Docker Compose stack, on the course cluster, namespace `datadog-curso`,
exposed at https://datadog.iochannel.tech. Deployment is done by the cluster's playbooks (AWX);
this folder is the **reference**: what to deploy and with which values.

- `values.yaml`: Helm values for the official `datadog/datadog` chart (node agent DaemonSet on every
  node, cluster agent, cluster-checks runner). APM, DogStatsD, logs (scoped to the namespace), process,
  NPM, USM (eBPF), orchestrator explorer, events, Single Step Instrumentation for the namespace.
- `app.yaml`: Postgres (ClusterIP, DBM via a cluster check on the Service), shop-api (2 replicas, unified
  tags as labels, admission controller enabled), shop-web (nginx + RUM), Ingress with TLS, load generator.
- `../ESPECIFICACION.md`: the specification handed to the cluster playbook author (in Spanish).

Images are built from `../app` and `..` (web) and pushed to Harbor, project `curso`:

```bash
cd demo
docker build -t registry.ivanosuna.com/curso/shop-api:1.0.0 app
docker build -t registry.ivanosuna.com/curso/shop-web:1.0.0 -f web/Dockerfile .
docker push registry.ivanosuna.com/curso/shop-api:1.0.0
docker push registry.ivanosuna.com/curso/shop-web:1.0.0
```

Secrets (never in git; created by the playbook from vault):

| Secret | Keys | Used by |
|--------|------|---------|
| `datadog-keys` | `api-key`, `app-key` | the chart (`apiKeyExistingSecret`, `appKeyExistingSecret`) |
| `postgres-credentials` | `password` | postgres, shop-api |
| `rum-credentials` | `app-id`, `client-token` | shop-web |

What differs from Compose, and why it matters in class:
- the agent is a **DaemonSet**: one pod per node, the app finds it through `status.hostIP`;
- the Postgres check is a **cluster check**: it runs once (on the runner), not on every node;
- **USM** works here (real kernel) and is the reason the k8s variant exists;
- unified tags come from **pod labels** (`tags.datadoghq.com/*`), and the **admission controller** turns
  them into env vars; `kube_namespace`, `pod_name`, `kube_deployment` tags come for free;
- the host in Datadog is the **node**; pods are containers of that host.

Checks after the playbook runs:

```bash
kubectl -n datadog-curso get pods -o wide
kubectl -n datadog-curso exec -it ds/datadog -c agent -- agent status | less
kubectl -n datadog-curso exec -it deploy/datadog-cluster-agent -- agent status
kubectl -n datadog-curso exec -it deploy/datadog-clusterchecks -- agent status | grep -A20 postgres   # the DBM check lives here
kubectl -n datadog-curso logs deploy/shop-api | head -5                                              # DATADOG TRACER CONFIGURATION line, agent_error:false
curl -s https://datadog.iochannel.tech/api/products | head -c 200
```

Then in Datadog: Infrastructure → Kubernetes → namespace `datadog-curso`; APM → `shop-api`; Logs → `kube_namespace:datadog-curso`; Network Map filtered by the namespace; DBM → the postgres host.
