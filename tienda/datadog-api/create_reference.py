#!/usr/bin/env python3
"""
Creates the trainer's reference assets in the course org (prefix "ivan - "): the ops dashboard,
the monitors of lab04, the log pipeline of lab07, an SLO and the investigation notebook of lab11.
Idempotent: skips anything whose name already exists. Needs DD_API_KEY and DD_APP_KEY in the env.

  export $(grep -E '^DD_(API|APP)_KEY' ../.env | xargs) && python3 create_reference.py
  python3 create_reference.py --delete      # removes everything it created (by name prefix)
"""
import json, os, ssl, sys, urllib.request, urllib.error

# python.org builds on macOS ship without root CAs until "Install Certificates.command" is run:
# fall back to certifi or the system bundle.
try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem" if os.path.exists("/etc/ssl/cert.pem") else None)

SITE = "https://api.datadoghq.eu"
PREFIX = "ivan - "
ENV, SERVICE = "course", "shop-api"
HEADERS = {"DD-API-KEY": os.environ["DD_API_KEY"], "DD-APPLICATION-KEY": os.environ["DD_APP_KEY"],
           "Content-Type": "application/json"}


def call(method, path, body=None):
    req = urllib.request.Request(SITE + path, method=method, headers=HEADERS,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        print(f"  !! {method} {path} -> {e.code}: {e.read().decode()[:300]}")
        return None


# ----------------------------------------------------------------------------- monitors
def monitors_by_name():
    return {m["name"]: m["id"] for m in (call("GET", "/api/v1/monitor?page_size=1000") or [])}


MESSAGE = """{{#is_alert}}🔴 {{value}} (threshold {{threshold}}) on {{resource_name.name}} in {{env.name}}{{/is_alert}}
{{#is_warning}}🟡 {{value}}, approaching the threshold{{/is_warning}}
{{#is_recovery}}🟢 Recovered: {{value}}{{/is_recovery}}

**Impact**: users wait or fail on checkout.
**Look first**: [service page](https://app.datadoghq.eu/apm/services/shop-api?env=course) · runbook: check the `payment.charge` span, the N+1 on /api/report, JVM heap.
"""

MONITORS = [
    {"name": PREFIX + "[shop] shop-api p95 latency high on {{resource_name.name}}", "type": "query alert",
     "query": f"avg(last_5m):p95:trace.servlet.request{{env:{ENV},service:{SERVICE}}} by {{resource_name}} > 1",
     "message": MESSAGE, "priority": 3,
     "options": {"thresholds": {"critical": 1, "warning": 0.7, "critical_recovery": 0.5}, "require_full_window": True,
                 "notify_no_data": False, "renotify_interval": 30, "include_tags": True}},
    {"name": PREFIX + "[shop] shop-api error rate", "type": "query alert",
     "query": f"sum(last_10m):sum:trace.servlet.request.errors{{env:{ENV},service:{SERVICE}}}.as_count() / sum:trace.servlet.request.hits{{env:{ENV},service:{SERVICE}}}.as_count() * 100 > 20",
     "message": MESSAGE, "priority": 2,
     "options": {"thresholds": {"critical": 20, "warning": 10, "critical_recovery": 8}, "notify_no_data": False}},
    {"name": PREFIX + "[shop] shop-api has traffic", "type": "query alert",
     "query": f"sum(last_5m):sum:trace.servlet.request.hits{{env:{ENV},service:{SERVICE}}}.as_count() > 10",
     "message": "Traffic present (helper monitor for the composite). @nobody", "priority": 5,
     "options": {"thresholds": {"critical": 10}, "notify_no_data": True, "no_data_timeframe": 10}},
    {"name": PREFIX + "[shop] orders volume anomaly", "type": "query alert",
     "query": f"avg(last_15m):anomalies(sum:shop.orders.created{{env:{ENV}}}.as_count(), 'agile', 2, direction='below', interval=60, alert_window='last_15m', count_default_zero='true', seasonality='hourly') >= 0.5",
     "message": "Orders dropped below the expected band. @nobody", "priority": 3,
     "options": {"thresholds": {"critical": 0.5, "critical_recovery": 0.25},
                 "threshold_windows": {"trigger_window": "last_15m", "recovery_window": "last_15m"}, "notify_no_data": False}},
    # A failed pipeline is a deploy that did not happen (or a red test that stopped one): it goes
    # to the Mailpit inbox, where the course sees every notification.
    {"name": PREFIX + "[ci] datadog-entorno pipeline failed", "type": "ci-pipelines alert",
     "query": 'ci-pipelines("ci_level:pipeline @ci.pipeline.name:\\"ivan/datadog-entorno\\" @ci.status:error")'
              '.rollup("count").last("15m") > 0',
     "message": "{{#is_alert}}🔴 A pipeline of ivan/datadog-entorno failed: check the job that went red in GitLab "
                "or in CI Visibility.{{/is_alert}}\n@webhook-mailpit", "priority": 3,
     "options": {"thresholds": {"critical": 0}, "notify_no_data": False}},
    {"name": PREFIX + "[shop] payment rejections spike", "type": "log alert",
     "query": f'logs("service:{SERVICE} status:error \\"Payment rejected\\"").index("*").rollup("count").last("5m") > 20',
     "message": "More than 20 payment rejections in 5 minutes. {{#is_alert}}@nobody{{/is_alert}}", "priority": 3,
     "options": {"thresholds": {"critical": 20, "warning": 10}, "enable_logs_sample": True, "notify_no_data": False}},
]


def create_monitors():
    existing = monitors_by_name()
    ids = {}
    for m in MONITORS:
        if m["name"] in existing:
            ids[m["name"]] = existing[m["name"]]; print(f"  = monitor exists: {m['name']}"); continue
        body = dict(m, tags=["team:training", f"service:{SERVICE}", "owner:ivan", "managed-by:script"])
        r = call("POST", "/api/v1/monitor", body)
        if r: ids[m["name"]] = r["id"]; print(f"  + monitor {r['id']}: {m['name']}")
    lat, traffic = ids.get(MONITORS[0]["name"]), ids.get(MONITORS[2]["name"])
    comp = PREFIX + "[shop] latency high AND traffic present"
    if lat and traffic and comp not in existing:
        r = call("POST", "/api/v1/monitor", {"name": comp, "type": "composite", "query": f"{lat} && {traffic}",
                 "message": "Latency is high while there is real traffic. @nobody",
                 "tags": ["team:training", f"service:{SERVICE}", "owner:ivan", "managed-by:script"]})
        if r: print(f"  + composite {r['id']}")
    return ids


# ----------------------------------------------------------------------------- dashboard
def create_dashboard():
    """Creates the ops dashboard, or UPDATES it in place (same id, same URL the students have).
    The body lives in dashboard_ops.py: it is long, and it changes more often than the rest."""
    import dashboard_ops
    name = PREFIX + "shop-api ops"
    slo = next((s["id"] for s in (call("GET", "/api/v1/slo?limit=1000") or {}).get("data", [])
                if s["name"].startswith(PREFIX + "shop-api availability")), "")
    mons = monitors_by_name()
    pick = lambda frag: next((str(i) for n, i in mons.items() if n.startswith(PREFIX) and frag in n), "")
    body = dashboard_ops.body(name, slo, {"errors": pick("shop-api error rate"), "p95": pick("p95 latency")})
    for d in (call("GET", "/api/v1/dashboard") or {}).get("dashboards", []):
        if d["title"] == name:
            r = call("PUT", f"/api/v1/dashboard/{d['id']}", body)
            if r: print(f"  ~ dashboard updated {r['id']}: {r['url']}")
            return d["id"]
    r = call("POST", "/api/v1/dashboard", body)
    if r: print(f"  + dashboard {r['id']}: {r['url']}"); return r["id"]


# ----------------------------------------------------------------------------- log pipeline
def create_pipeline():
    name = PREFIX + "shop-api"
    for p in call("GET", "/api/v1/logs/config/pipelines") or []:
        if p["name"] == name:
            print(f"  = pipeline exists: {p['id']}"); return p["id"]
    line = (r'shop_line %{date("yyyy-MM-dd HH:mm:ss.SSS"):timestamp} %{word:level}\s+\[%{notSpace:logger.thread_name}\] '
            r'\[dd.service=%{notSpace:dd.service} dd.env=%{notSpace:dd.env} dd.version=%{notSpace:dd.version} '
            r'dd.trace_id=%{regex("[^ ]*"):dd.trace_id} dd.span_id=%{regex("[^ \\]]*"):dd.span_id}\] %{notSpace:logger.name} - %{data:msg}')
    body = {
        "name": name, "is_enabled": True, "filter": {"query": f"service:{SERVICE} source:java"},
        "processors": [
            {"type": "grok-parser", "name": "Parse the logback line", "is_enabled": True, "source": "message",
             "samples": ["2026-10-11 07:57:40.105 INFO  [http-nio-8081-exec-2] [dd.service=shop-api dd.env=course dd.version=1.0.0 dd.trace_id=6acb417300000000214d1720c53ac691 dd.span_id=5740378446534783345] c.course.shop.service.OrderService - Order created id=10 customer=ivan product=Keyboard quantity=2 total=99.80 status=PAID"],
             "grok": {"support_rules": "", "match_rules": line}},
            {"type": "grok-parser", "name": "key=value pairs from the message", "is_enabled": True, "source": "msg",
             "samples": ["Order created id=10 customer=ivan product=Keyboard quantity=2 total=99.80 status=PAID"],
             "grok": {"support_rules": "", "match_rules": "kv %{data::keyvalue}"}},
            {"type": "date-remapper", "name": "timestamp", "is_enabled": True, "sources": ["timestamp"]},
            {"type": "status-remapper", "name": "level -> status", "is_enabled": True, "sources": ["level"]},
            {"type": "trace-id-remapper", "name": "trace id", "is_enabled": True, "sources": ["dd.trace_id"]},
            {"type": "attribute-remapper", "name": "customer -> usr.name", "is_enabled": True, "sources": ["customer"], "target": "usr.name",
             "source_type": "attribute", "target_type": "attribute", "preserve_source": False, "override_on_conflict": False},
            {"type": "category-processor", "name": "payment.outcome", "is_enabled": True, "target": "payment.outcome",
             # PaymentGateway logs exactly two messages; only the rejected one carries @reason
             "categories": [{"name": "rejected", "filter": {"query": "@logger.name:c.course.shop.service.PaymentGateway @reason:*"}},
                            {"name": "accepted", "filter": {"query": "@logger.name:c.course.shop.service.PaymentGateway -@reason:*"}}]},
            {"type": "message-remapper", "name": "msg -> message", "is_enabled": True, "sources": ["msg"]},
        ],
    }
    r = call("POST", "/api/v1/logs/config/pipelines", body)
    if r: print(f"  + pipeline {r['id']}"); return r["id"]


# ----------------------------------------------------------------------------- SLO
def create_slo():
    name = PREFIX + "shop-api availability"
    for s in (call("GET", "/api/v1/slo?limit=1000") or {}).get("data", []):
        if s["name"] == name:
            print(f"  = SLO exists: {s['id']}"); return s["id"]
    hits = f"sum:trace.servlet.request.hits{{env:{ENV},service:{SERVICE}}}.as_count()"
    errs = f"sum:trace.servlet.request.errors{{env:{ENV},service:{SERVICE}}}.as_count()"
    body = {"name": name, "type": "metric", "description": "Share of non-5xx requests (reference, lab04).",
            "query": {"numerator": f"{hits} - {errs}", "denominator": hits},
            "thresholds": [{"timeframe": "7d", "target": 95.0, "warning": 97.0}],
            "tags": ["team:training", f"service:{SERVICE}", "owner:ivan"]}
    r = call("POST", "/api/v1/slo", body)
    if r: print(f"  + SLO {r['data'][0]['id']}"); return r["data"][0]["id"]


# ----------------------------------------------------------------------------- notebook
def create_notebook():
    name = PREFIX + "payment failures investigation"
    for n in (call("GET", "/api/v1/notebooks?count=100") or {}).get("data", []):
        if n["attributes"]["name"] == name:
            print(f"  = notebook exists: {n['id']}"); return n["id"]
    f = f"env:{ENV},service:{SERVICE}"
    def md(text): return {"type": "notebook_cells", "attributes": {"definition": {"type": "markdown", "text": text}}}
    def graph(title, queries): return {"type": "notebook_cells", "attributes": {"definition": {"type": "timeseries", "title": title,
                                       "requests": [{"q": x, "display_type": "line"} for x in queries]}, "graph_size": "m"}}
    body = {"data": {"type": "notebooks", "attributes": {"name": name, "time": {"live_span": "2h"}, "cells": [
        md("# Payment failures on checkout\n**Status**: investigating · **Owner**: ivan\n\nThe error-rate monitor went WARN. Payment failures suspected."),
        graph("Error rate %", [f"sum:trace.servlet.request.errors{{{f}}}.as_count() / sum:trace.servlet.request.hits{{{f}}}.as_count() * 100"]),
        md("Errors are concentrated on `POST /api/orders` and `GET /api/payment`."),
        graph("Errors by endpoint", [f"sum:trace.servlet.request.errors{{{f}}} by {{resource_name}}.as_count()"]),
        md("Payment provider: latency and outcome split. The provider fails ~30 % regardless of our load."),
        graph("Payment duration by status (ms)", [f"avg:shop.payment.duration.avg{{env:{ENV}}} by {{status}}"]),
        graph("Orders by status", [f"sum:shop.orders.created{{env:{ENV}}} by {{status}}.as_count()"]),
        md("Infrastructure is fine (CPU, heap) and nothing was deployed.\n\n**Conclusion**: third-party gateway timeouts. Actions: client timeout + retry + fallback; monitor on provider latency; synthetic payment journey."),
        graph("Container CPU and JVM heap", [f"avg:docker.cpu.user{{{f}}}", f"avg:jvm.heap_memory{{{f}}}"]),
    ]}}}
    r = call("POST", "/api/v1/notebooks", body)
    if r: print(f"  + notebook {r['data']['id']}"); return r["data"]["id"]


# ----------------------------------------------------------------------------- synthetics
BASE_URL = os.environ.get("DEMO_URL", "https://datadog.iochannel.tech")


def create_synthetics():
    existing = {t["name"]: t["public_id"] for t in (call("GET", "/api/v1/synthetics/tests") or {}).get("tests", [])}
    common = {"locations": ["aws:eu-central-1", "aws:eu-west-3", "aws:eu-west-1"], "status": "paused",
              "tags": ["team:training", "owner:ivan", "managed-by:script"], "message": "@nobody"}
    api = {**common, "name": PREFIX + "shop api products", "type": "api", "subtype": "http",
           "config": {"request": {"method": "GET", "url": BASE_URL + "/api/products"},
                      "assertions": [{"type": "statusCode", "operator": "is", "target": 200},
                                     {"type": "responseTime", "operator": "lessThan", "target": 1000},
                                     {"type": "header", "property": "content-type", "operator": "contains", "target": "application/json"},
                                     {"type": "body", "operator": "contains", "target": "Keyboard"}]},
           "options": {"tick_every": 300, "min_failure_duration": 60, "min_location_failed": 2, "retry": {"count": 1, "interval": 30000}}}
    def el(css): return {"userLocator": {"values": [{"type": "css", "value": css}], "failTestOnCannotLocate": True}}
    browser = {**common, "name": PREFIX + "shop checkout journey", "type": "browser",
               "config": {"request": {"method": "GET", "url": BASE_URL + "/"}, "assertions": [], "setCookie": ""},
               "options": {"tick_every": 900, "min_failure_duration": 60, "min_location_failed": 2, "device_ids": ["chrome.laptop_large"],
                           "retry": {"count": 1, "interval": 30000}, "ignoreServerCertificateError": False},
               "steps": [
                   {"name": "Type the name", "type": "typeText", "params": {"element": el("#customer"), "value": "synthetic", "delay": 25}, "allowFailure": False},
                   {"name": "Identify in RUM", "type": "click", "params": {"element": el("#identify")}, "allowFailure": False},
                   {"name": "Buy the first product", "type": "click", "params": {"element": el("#products .card:first-child button")}, "allowFailure": False},
                   {"name": "Order appears", "type": "assertElementContent", "params": {"element": el("#orders"), "check": "contains", "value": "synthetic"}, "allowFailure": False},
               ]}
    for t in (api, browser):
        if t["name"] in existing:
            print(f"  = synthetic exists: {t['name']}"); continue
        r = call("POST", "/api/v1/synthetics/tests/" + ("browser" if t["type"] == "browser" else "api"), t)
        if r: print(f"  + synthetic {r['public_id']}: {t['name']} (paused until {BASE_URL} exists)")


# ----------------------------------------------------------------------------- delete
def delete_all():
    for name, mid in monitors_by_name().items():
        if name.startswith(PREFIX): call("DELETE", f"/api/v1/monitor/{mid}?force=true"); print("  - monitor", name)
    for d in (call("GET", "/api/v1/dashboard") or {}).get("dashboards", []):
        if d["title"].startswith(PREFIX): call("DELETE", f"/api/v1/dashboard/{d['id']}"); print("  - dashboard", d["title"])
    for p in call("GET", "/api/v1/logs/config/pipelines") or []:
        if p["name"].startswith(PREFIX): call("DELETE", f"/api/v1/logs/config/pipelines/{p['id']}"); print("  - pipeline", p["name"])
    for s in (call("GET", "/api/v1/slo?limit=1000") or {}).get("data", []):
        if s["name"].startswith(PREFIX): call("DELETE", f"/api/v1/slo/{s['id']}?force=true"); print("  - SLO", s["name"])
    for n in (call("GET", "/api/v1/notebooks?count=100") or {}).get("data", []):
        if n["attributes"]["name"].startswith(PREFIX): call("DELETE", f"/api/v1/notebooks/{n['id']}"); print("  - notebook", n["attributes"]["name"])
    ids = [t["public_id"] for t in (call("GET", "/api/v1/synthetics/tests") or {}).get("tests", []) if t["name"].startswith(PREFIX)]
    if ids: call("POST", "/api/v1/synthetics/tests/delete", {"public_ids": ids}); print("  - synthetics", ids)


if __name__ == "__main__":
    if "--delete" in sys.argv:
        delete_all(); sys.exit()
    print("monitors"); create_monitors()
    print("dashboard"); create_dashboard()
    print("log pipeline"); create_pipeline()
    print("SLO"); create_slo()
    print("notebook"); create_notebook()
    print("synthetics"); create_synthetics()
