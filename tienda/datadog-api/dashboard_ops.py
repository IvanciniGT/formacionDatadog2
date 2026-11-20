"""
The reference dashboard "ivan - shop-api ops": one screen for the on-call engineer AND the dev team.

Read it top to bottom, like an incident: is it broken? (health) -> where? (golden signals, by
endpoint) -> why? (dependencies, logs, errors) -> is it us? (saturation, deploys) -> does the
business notice? (orders, revenue, real users). The last groups are for the dev team in the daily:
delivery (pipelines, deploys, synthetics in CI) and code (JVM, slow queries).

It is also a catalogue on purpose: almost every widget type Datadog has appears once, so the
students can open it and copy the one they need (lab02). Each one says WHY it is that type in its
title or in the note above it.

Only the body is built here; create_reference.py creates it, or updates it in place (same URL).
"""

ENV, SERVICE = "course", "shop-api"
F = "$env,$service,$version"                     # scope of everything the app emits (unified service tagging)
DB = "$env,service:shop-db"               # the Postgres DBM cluster check reports as shop-db
RUM_APP = "@application.name:shop-web"
APP_URL = "https://datadog.iochannel.tech"
DD = "https://app.datadoghq.eu"


# ----------------------------------------------------------------------------- helpers
def m(name, query, aggregator=None):
    d = {"data_source": "metrics", "name": name, "query": query}
    if aggregator:
        d["aggregator"] = aggregator
    return d


def ev(name, source, query, aggregation="count", metric=None, group_by=None, limit=10):
    """A query against an event platform source: logs, spans, rum, ci_pipelines, ci_tests..."""
    c = {"aggregation": aggregation}
    if metric:
        c["metric"] = metric
    d = {"data_source": source, "name": name, "search": {"query": query}, "indexes": ["*"], "compute": c}
    if group_by:
        d["group_by"] = [{"facet": g, "limit": limit, "sort": {"aggregation": aggregation, "order": "desc",
                                                               **({"metric": metric} if metric else {})}}
                         for g in group_by]
    return d


def fx(formula, alias=None, **kw):
    d = {"formula": formula}
    if alias:
        d["alias"] = alias
    d.update(kw)
    return d


def w(definition, width=None, height=None):
    return {"definition": definition}


def note(content, color="white", size="14", tick=False, pos="left"):
    return w({"type": "note", "content": content, "background_color": color, "font_size": size,
              "text_align": "left", "show_tick": tick, "tick_pos": "50%", "tick_edge": pos,
              "has_padding": True})


def group(title, widgets, color="vivid_blue", collapsed=False):
    return {"definition": {"type": "group", "title": title, "layout_type": "ordered", "show_title": True,
                           "background_color": color, "widgets": widgets}}


def traffic_light(green, red, lower_is_better=True):
    if lower_is_better:
        return [{"comparator": "<", "value": green, "palette": "white_on_green"},
                {"comparator": ">=", "value": red, "palette": "white_on_red"},
                {"comparator": ">=", "value": green, "palette": "white_on_yellow"}]
    return [{"comparator": ">", "value": green, "palette": "white_on_green"},
            {"comparator": "<=", "value": red, "palette": "white_on_red"},
            {"comparator": "<=", "value": green, "palette": "white_on_yellow"}]


def big_number(title, queries, formula, unit=None, fmt=None, precision=1, spark=True, timeshift=None):
    req = {"response_format": "scalar", "queries": queries, "formulas": [fx(formula)]}
    if fmt:
        req["conditional_formats"] = fmt
    d = {"type": "query_value", "title": title, "title_size": "16", "title_align": "left",
         "precision": precision, "autoscale": True, "requests": [req]}
    if unit:
        d["custom_unit"] = unit
    if spark:
        # the sparkline behind the number: the value AND its trend, in the same square
        d["timeseries_background"] = {"type": "area", "yaxis": {"include_zero": True}}
    return w(d)


DEPLOYS = [{"q": "source:kubernetes kube_deployment:shop-api", "tags_execution": "and"}]


def series(title, requests, markers=None, events=True, yaxis=None, legend="auto", right_yaxis=None):
    d = {"type": "timeseries", "title": title, "title_size": "16", "title_align": "left",
         "show_legend": True, "legend_layout": legend, "legend_columns": ["avg", "max", "value"],
         "requests": requests}
    if markers:
        d["markers"] = markers
    if events:
        d["events"] = DEPLOYS          # the vertical bars: "did it start with a deploy?"
    if yaxis:
        d["yaxis"] = yaxis
    if right_yaxis:
        d["right_yaxis"] = right_yaxis
    return w(d)


def treq(queries, formulas, display="line", palette="dog_classic", line="solid", width="normal", axis=None):
    r = {"response_format": "timeseries", "queries": queries, "formulas": formulas, "display_type": display,
         "style": {"palette": palette, "line_type": line, "line_width": width}}
    if axis:
        r["on_right_yaxis"] = True
    return r


# ----------------------------------------------------------------------------- the groups
def header():
    return [
        note(f"""# 🛒 shop-api — operations & development
**Who reads it**: on-call (top half) and the dev team in the daily (bottom half).
**How**: top to bottom, like an incident — *is it broken? → where? → why? → is it us? → does the business notice?*

🔗 [Service page]({DD}/apm/services/shop-api?env=course) · [Logs]({DD}/logs?query=service%3Ashop-api) · [Error Tracking]({DD}/apm/error-tracking?query=service%3Ashop-api) · [The shop]({APP_URL}) · [Runbook](https://gitlab.ivanosuna.com/ivan/datadog-entorno)

Vertical bars on the graphs = **deploys** of shop-api. Dashed lines = **thresholds** of the monitors.""",
             color="vivid_purple", size="14"),
        w({"type": "manage_status", "title": "Monitors of the shop (red first)", "title_size": "16",
           "query": "ivan - [shop]", "summary_type": "monitors", "display_format": "countsAndList",
           "color_preference": "background", "hide_zero_counts": True, "show_last_triggered": True,
           "show_priority": False, "sort": "status,asc"}),
        w({"type": "slo", "title": "Availability SLO — APM requests, target 95 %", "title_size": "16", "view_type": "detail",
           "slo_id": "__SLO_ID__", "show_error_budget": True, "view_mode": "overall",
           "time_windows": ["7d", "30d"], "global_time_target": "0"}),
        w({"type": "check_status", "title": "Agents up, per node", "title_size": "16",
           "check": "datadog.agent.up", "grouping": "check", "group_by": ["host"],
           "tags": ["kube_cluster_name:iochannel-cluster"]}),
    ]


def health():
    hits, errs = f"sum:trace.servlet.request.hits{{{F}}}.as_count()", f"sum:trace.servlet.request.errors{{{F}}}.as_count()"
    return group("① Right now — is it broken?", [
        big_number("Requests / s", [m("hits", f"sum:trace.servlet.request.hits{{{F}}}.as_rate()", "avg")], "hits", "req/s"),
        big_number("Error rate", [m("e", errs, "sum"), m("h", hits, "sum")], "e / h * 100", "%", traffic_light(2, 5), 2),
        big_number("p95 latency", [m("p", f"p95:trace.servlet.request{{{F}}}", "avg")], "p * 1000", "ms",
                   traffic_light(500, 1000), 0),
        big_number("Apdex", [m("a", f"avg:trace.servlet.request.apdex{{{F}}}", "avg")], "a", None,
                   traffic_light(0.9, 0.7, lower_is_better=False), 2),
        big_number("Orders paid", [m("o", "sum:shop.orders.created{$env,status:paid}.as_count()", "sum")], "o", "orders", None, 0),
        big_number("Payment failures", [m("f", "sum:shop.orders.created{$env,status:payment_failed}.as_count()", "sum"),
                                        m("t", "sum:shop.orders.created{$env}.as_count()", "sum")],
                   "f / t * 100", "%", traffic_light(5, 15), 1),
        # change: the same number against yesterday, because "is 40 req/s a lot?" has no answer alone
        w({"type": "change", "title": "Traffic vs. same time yesterday", "title_size": "16", "requests": [{
            "response_format": "scalar",
            "queries": [m("now", f"sum:trace.servlet.request.hits{{{F}}}.as_count()", "sum")],
            "formulas": [fx("now"), fx("day_before(now)")],
            "compare_to": "day_before", "increase_good": True, "order_by": "change", "change_type": "relative",
            "order_dir": "desc", "show_present": True}]}),
        w({"type": "alert_value", "title": "Monitor: error rate (live value)", "title_size": "16",
           "alert_id": "__MON_ERRORS__", "precision": 2, "unit": "%", "text_align": "center"}),
    ], "vivid_green")


def golden_signals():
    by_res = f"{{{F}}} by {{resource_name}}"
    return group("② Golden signals — where?", [
        series("Error rate % (formula: errors ÷ hits)", [treq(
            [m("e", f"sum:trace.servlet.request.errors{{{F}}}.as_count()"), m("h", f"sum:trace.servlet.request.hits{{{F}}}.as_count()")],
            [fx("e / h * 100", "error %")], "line", "warm", width="thick")],
            markers=[{"value": "y = 2", "display_type": "warning dashed", "label": "warn 2 %"},
                     {"value": "y = 5", "display_type": "error dashed", "label": "alert 5 %"}]),
        series("Latency p50 / p95 / p99 (ms)", [treq(
            [m("p50", f"p50:trace.servlet.request{{{F}}}"), m("p95", f"p95:trace.servlet.request{{{F}}}"),
             m("p99", f"p99:trace.servlet.request{{{F}}}")],
            [fx("p50 * 1000", "p50"), fx("p95 * 1000", "p95"), fx("p99 * 1000", "p99")], "line", "cool")],
            markers=[{"value": "y = 1000", "display_type": "error dashed", "label": "SLO 1 s"}]),
        series("Requests by endpoint (stacked)", [treq([m("h", f"sum:trace.servlet.request.hits{by_res}.as_rate()")],
                                                       [fx("h")], "bars", "semantic")]),
        series("Requests by HTTP status", [treq(
            [m("s", f"sum:trace.servlet.request.hits.by_http_status{{{F}}} by {{http.status_code}}.as_count()")],
            [fx("s")], "area", "semantic")]),
        # query table: every endpoint with its 4 numbers side by side, coloured where it hurts
        w({"type": "query_table", "title": "Endpoints: traffic, errors, latency", "title_size": "16",
           "has_search_bar": "auto", "requests": [{
               "response_format": "scalar",
               "queries": [m("hits", f"sum:trace.servlet.request.hits{by_res}.as_count()", "sum"),
                           m("errs", f"sum:trace.servlet.request.errors{by_res}.as_count()", "sum"),
                           m("p95", f"p95:trace.servlet.request{by_res}", "avg"),
                           m("p50", f"p50:trace.servlet.request{by_res}", "avg")],
               "formulas": [fx("hits", "requests", cell_display_mode="bar"),
                            fx("errs / hits * 100", "error %", conditional_formats=traffic_light(2, 5)),
                            fx("p50 * 1000", "p50 ms"),
                            fx("p95 * 1000", "p95 ms", conditional_formats=traffic_light(500, 1000),
                               cell_display_mode="bar"),
                            ],
               "sort": {"count": 20, "order_by": [{"type": "formula", "index": 0, "order": "desc"}]}}]}),
        # heatmap: the shape of latency, not one percentile. POST /api/orders comes out bimodal
        w({"type": "heatmap", "title": "Latency heatmap, all endpoints", "title_size": "16",
           "show_legend": False, "events": DEPLOYS,
           "requests": [{"response_format": "timeseries",
                         "queries": [m("l", f"avg:trace.servlet.request{by_res}")], "formulas": [fx("l")],
                         "style": {"palette": "dog_classic"}}]}),
        # distribution: how many requests took how long, over the whole time range
        w({"type": "distribution", "title": "Latency distribution (whole range)", "title_size": "16",
           "show_legend": False, "xaxis": {"include_zero": True},
           "requests": [{"request_type": "histogram",
                         "query": {"data_source": "metrics", "name": "d",
                                   "query": f"histogram:trace.servlet.request{{{F}}}"},
                         "style": {"palette": "dog_classic"}}]}),
        # treemap: which endpoints carry the load, at a glance
        w({"type": "treemap", "title": "Where the traffic goes", "title_size": "16", "requests": [{
            "response_format": "scalar",
            "queries": [m("h", f"sum:trace.servlet.request.hits{by_res}.as_count()", "sum")], "formulas": [fx("h")]}]}),
        w({"type": "sunburst", "title": "Status codes, by endpoint", "title_size": "16", "hide_total": False,
           "legend": {"type": "automatic"}, "requests": [{
               "response_format": "scalar",
               "queries": [m("s", f"sum:trace.servlet.request.hits.by_http_status{{{F}}} by {{http.status_code,resource_name}}.as_count()", "sum")],
               "formulas": [fx("s")]}]}),
    ], "vivid_blue")


def why():
    return group("③ Why? — dependencies, errors, logs", [
        w({"type": "trace_service", "title": "shop-api — APM service summary", "title_size": "16",
           "env": ENV, "service": SERVICE, "span_name": "servlet.request", "show_hits": True, "show_errors": True,
           "show_latency": True, "show_breakdown": True, "show_distribution": True, "show_resource_list": True,
           "size_format": "large", "display_format": "three_column"}),
        w({"type": "servicemap", "title": "Who shop-api talks to", "title_size": "16",
           "service": SERVICE, "filters": [f"env:{ENV}"]}),
        series("Payment provider: p95 and avg by result (ms)", [treq(
            [m("p95", "avg:shop.payment.duration.95percentile{$env} by {status}")], [fx("p95", "p95")], "line", "orange"),
            treq([m("avg", "avg:shop.payment.duration.avg{$env} by {status}")], [fx("avg", "avg")], "line", "grey", line="dashed")]),
        # anomalies(): the band is what Datadog learnt as normal; the red bits are outside it
        series("Payment p95 — anomaly detection", [treq(
            [m("a", "anomalies(avg:shop.payment.duration.95percentile{$env}, 'agile', 2)")], [fx("a")], "line", "purple")],
            events=False),
        w({"type": "toplist", "title": "Slowest SQL (p95, from the APM spans)", "title_size": "16", "requests": [{
            "response_format": "scalar",
            "queries": [m("q", "p95:trace.postgresql.query{$env,$service} by {resource_name}", "avg")],
            "formulas": [fx("q * 1000", "ms", limit={"count": 7, "order": "desc"})],
            "conditional_formats": traffic_light(20, 100)}],
           "style": {"display": {"type": "stacked", "legend": "automatic"}, "palette": "warm"}}),
        w({"type": "toplist", "title": "Most frequent SQL — look for the N+1", "title_size": "16", "requests": [{
            "response_format": "scalar",
            "queries": [m("q", "sum:trace.postgresql.query.hits{$env,$service} by {resource_name}.as_count()", "sum")],
            "formulas": [fx("q", limit={"count": 7, "order": "desc"})]}]}),
        # logs as numbers: the same facets the log pipeline extracts
        series("Logs by status (from the log pipeline)", [{
            "response_format": "timeseries", "display_type": "bars",
            "queries": [ev("l", "logs", "service:shop-api", group_by=["status"])], "formulas": [fx("l")],
            "style": {"palette": "semantic"}}]),
        w({"type": "toplist", "title": "Who fails to pay (usr.name from the logs)", "title_size": "16", "requests": [{
            "response_format": "scalar",
            "queries": [ev("l", "logs", "service:shop-api status:(warn OR error) @usr.name:*", group_by=["@usr.name"], limit=8)],
            "formulas": [fx("l")]}]}),
        w({"type": "list_stream", "title": "Live errors (log stream)", "title_size": "16", "requests": [{
            "response_format": "event_list",
            "query": {"data_source": "logs_stream", "query_string": "service:shop-api status:error",
                      "indexes": [], "storage": "hot", "sort": {"column": "timestamp", "order": "desc"}},
            "columns": [{"field": "status_line", "width": "auto"}, {"field": "timestamp", "width": "auto"},
                        {"field": "@http.url_details.path", "width": "auto"}, {"field": "content", "width": "compact"}]}]}),
        w({"type": "list_stream", "title": "Error Tracking issues", "title_size": "16", "requests": [{
            "response_format": "event_list",
            "query": {"data_source": "apm_issue_stream", "query_string": "service:shop-api env:course",
                      "sort": {"column": "@first_seen", "order": "desc"}},
            "columns": [{"field": "details", "width": "auto"}]}]}),
    ], "vivid_orange")


def saturation():
    k = f"{{{F}}}"
    return group("④ Is it us? — saturation and Kubernetes", [
        series("CPU used vs. limit (cores)", [treq(
            [m("u", f"sum:container.cpu.usage{k} by {{pod_name}}")], [fx("u / 1000000000", "used")], "area", "cool"),
            treq([m("l", f"sum:container.cpu.limit{k}")], [fx("l / 1000000000", "limit")], "line", "red", line="dashed")]),
        series("Memory used vs. limit", [treq(
            [m("u", f"sum:container.memory.usage{k} by {{pod_name}}")], [fx("u")], "area", "green"),
            treq([m("l", f"sum:container.memory.limit{k}")], [fx("l", "limit")], "line", "red", line="dashed")]),
        series("CPU throttling (the silent latency)", [treq(
            [m("t", f"sum:container.cpu.throttled{k} by {{pod_name}}")], [fx("t")], "bars", "orange")]),
        # forecast(): where the line goes if nothing changes — for "will we run out?" questions
        series("Postgres connections — 1-day forecast", [treq(
            [m("c", f"forecast(avg:postgresql.connections{{{DB}}}, 'linear', 1)")], [fx("c")], "line", "purple")],
            events=False, markers=[{"value": "y = 100", "display_type": "error dashed", "label": "max_connections"}]),
        big_number("Pod restarts (range)", [m("r", f"sum:kubernetes.containers.restarts{k}", "max")], "r", None,
                   traffic_light(1, 3), 0, spark=False),
        big_number("Replicas available", [m("a", "avg:kubernetes_state.deployment.replicas_available{kube_deployment:shop-api}", "last"),
                                          m("d", "avg:kubernetes_state.deployment.replicas_desired{kube_deployment:shop-api}", "last")],
                   "a / d * 100", "% of desired", traffic_light(100, 50, lower_is_better=False), 0),
        w({"type": "hostmap", "title": "Nodes of the cluster, by CPU", "title_size": "16",
           "requests": {"fill": {"q": "avg:system.cpu.user{kube_cluster_name:iochannel-cluster} by {host}"},
                        "size": {"q": "avg:system.mem.used{kube_cluster_name:iochannel-cluster} by {host}"}},
           "node_type": "host", "no_metric_hosts": False, "no_group_hosts": True,
           "scope": ["kube_cluster_name:iochannel-cluster"],
           "style": {"palette": "green_to_orange", "palette_flip": False}}),
        w({"type": "list_stream", "title": "Kubernetes events of the namespace", "title_size": "16", "requests": [{
            "response_format": "event_list",
            "query": {"data_source": "event_stream", "query_string": "source:kubernetes kube_namespace:datadog-curso",
                      "sort": {"column": "timestamp", "order": "desc"}},
            "columns": [{"field": "title", "width": "auto"}, {"field": "timestamp", "width": "auto"}]}]}),
    ], "vivid_pink")


def business():
    return group("⑤ Does the business notice? — orders and real users", [
        series("Orders: paid vs. failed (stacked)", [treq(
            [m("o", "sum:shop.orders.created{$env} by {status}.as_count()")], [fx("o")], "bars", "semantic")]),
        series("Orders today vs. same day last week", [treq(
            [m("o", "sum:shop.orders.created{$env,status:paid}.as_count()")], [fx("o", "today")], "line", "dog_classic", width="thick"),
            treq([m("o2", "sum:shop.orders.created{$env,status:paid}.as_count()")], [fx("week_before(o2)", "last week")],
                 "line", "grey", line="dotted")], events=False),
        big_number("Revenue", [m("v", "sum:shop.orders.value{$env}.as_count()", "sum")], "v", "€", None, 0),
        big_number("Average ticket", [m("v", "sum:shop.orders.value{$env}.as_count()", "sum"),
                                      m("o", "sum:shop.orders.created{$env,status:paid}.as_count()", "sum")],
                   "v / o", "€", None, 2, spark=False),
        w({"type": "sunburst", "title": "Revenue by category", "title_size": "16", "hide_total": False,
           "legend": {"type": "table"}, "requests": [{
               "response_format": "scalar",
               "queries": [m("v", "sum:shop.orders.value{$env} by {category}.as_count()", "sum")], "formulas": [fx("v")]}]}),
        w({"type": "toplist", "title": "Stock left — reorder in red", "title_size": "16", "requests": [{
            "response_format": "scalar",
            "queries": [m("s", "min:shop.stock.units{$env} by {product}", "last")],
            "formulas": [fx("s", limit={"count": 10, "order": "asc"})],
            "conditional_formats": traffic_light(10, 3, lower_is_better=False)}]}),
        big_number("Real users: LCP p75 (RUM)", [ev("lcp", "rum", f"@type:view {RUM_APP}", "pc75", "@view.largest_contentful_paint")],
                   "lcp / 1000000", "ms", traffic_light(2500, 4000), 0),
        big_number("Sessions with errors (RUM)", [ev("e", "rum", f"@type:session {RUM_APP} @session.error.count:>0"),
                                                  ev("t", "rum", f"@type:session {RUM_APP}")],
                   "e / t * 100", "%", traffic_light(5, 20), 1),
        w({"type": "geomap", "title": "Where the real users are (RUM)", "title_size": "16",
           "view": {"focus": "WORLD"}, "style": {"palette": "hostmap_blues", "palette_flip": False},
           "requests": [{"response_format": "scalar",
                         "queries": [ev("s", "rum", f"@type:session {RUM_APP}", group_by=["@geo.country_iso_code"], limit=250)],
                         "formulas": [fx("s")]}]}),
        series("Robots: synthetic checkout and API response time (ms)", [treq(
            [m("b", "avg:synthetics.browser.test_duration{*}")], [fx("b", "browser checkout")], "line", "purple"),
            treq([m("h", "avg:synthetics.http.response.time{*}")], [fx("h", "API /products")], "line", "green")], events=False),
    ], "vivid_yellow")


def delivery():
    return group("⑥ For the dev team — delivery and the code", [
        note("**Daily questions**: did yesterday's version make it worse? (error rate by `version`) · how long "
             "does the pipeline take and where? · did the robots pass after the deploy? · is the JVM "
             "healthy or are we tuning the wrong thing?", color="blue", size="14"),
        series("Error rate by version — compare before/after a deploy", [treq(
            [m("e", f"sum:trace.servlet.request.errors{{{F}}} by {{version}}.as_count()"),
             m("h", f"sum:trace.servlet.request.hits{{{F}}} by {{version}}.as_count()")],
            [fx("e / h * 100", "error %")], "line", "dog_classic")]),
        series("p95 by version (ms)", [treq([m("p", f"p95:trace.servlet.request{{{F}}} by {{version}}")],
                                            [fx("p * 1000")], "line", "cool")]),
        w({"type": "query_table", "title": "Pipelines of datadog-entorno (CI Visibility)", "title_size": "16",
           "requests": [{"response_format": "scalar",
                         "queries": [ev("n", "ci_pipelines", '@ci.pipeline.name:"ivan/datadog-entorno" @ci.job.name:*',
                                        group_by=["@ci.job.name", "@ci.status"], limit=20),
                                     ev("d", "ci_pipelines", '@ci.pipeline.name:"ivan/datadog-entorno" @ci.job.name:*',
                                        "avg", "@duration", group_by=["@ci.job.name", "@ci.status"], limit=20)],
                         "formulas": [fx("n", "runs"), fx("d / 1000000000", "avg s", cell_display_mode="bar")]}]}),
        w({"type": "toplist", "title": "Synthetic tests run from CI, by result", "title_size": "16", "requests": [{
            "response_format": "scalar",
            "queries": [ev("t", "ci_tests", "@test.framework:synthetics", group_by=["@test.name", "@test.status"])],
            "formulas": [fx("t")]}]}),
        series("JVM heap used vs. max", [treq(
            [m("u", f"avg:jvm.heap_memory{{{F}}} by {{host}}")], [fx("u", "used")], "area", "green"),
            treq([m("x", f"avg:jvm.heap_memory_max{{{F}}}")], [fx("x", "max")], "line", "red", line="dashed")], events=False),
        series("GC time per minute (ms) — minor bars, major line", [treq(
            [m("mi", f"sum:jvm.gc.minor_collection_time{{{F}}}")], [fx("mi", "minor")], "bars", "cool"),
            treq([m("ma", f"sum:jvm.gc.major_collection_time{{{F}}}")], [fx("ma", "major")], "line", "red", width="thick")],
            events=False),
        # scatterplot: endpoints by traffic (x) and latency (y). Top right = fix it first
        w({"type": "scatterplot", "title": "Endpoints: traffic (x) vs. p95 (y) — top right first", "title_size": "16",
           "xaxis": {"scale": "log", "include_zero": False}, "yaxis": {"scale": "log", "include_zero": False},
           "color_by_groups": ["resource_name"],
           "requests": {"table": {"response_format": "scalar",
                                  "queries": [m("h", f"sum:trace.servlet.request.hits{{{F}}} by {{resource_name}}.as_count()", "sum"),
                                              m("p", f"p95:trace.servlet.request{{{F}}} by {{resource_name}}", "avg")],
                                  "formulas": [fx("h", dimension="x"), fx("p * 1000", dimension="y")]}}}),
        big_number("Threads", [m("t", f"avg:jvm.thread_count{{{F}}}", "avg")], "t", None, None, 0),
        big_number("Postgres cache hit ratio", [m("h", f"sum:postgresql.buffer_hit{{{DB}}}", "sum"),
                                                 m("r", f"sum:postgresql.disk_read{{{DB}}}", "sum")],
                   "h / (h + r) * 100", "%", traffic_light(99, 95, lower_is_better=False), 2),
        w({"type": "alert_graph", "title": "Monitor: p95 latency (with its threshold)", "title_size": "16",
           "alert_id": "__MON_P95__", "viz_type": "timeseries"}),
    ], "gray")


def body(name, slo_id, monitors):
    import json
    b = {
        "title": name, "layout_type": "ordered", "reflow_type": "auto",
        "description": "Reference dashboard of the course: operations (top) and development (bottom). "
                       "Almost every widget type appears once, on purpose — copy the one you need (lab02).",
        "template_variables": [
            {"name": "env", "prefix": "env", "available_values": [], "default": ENV},
            {"name": "service", "prefix": "service", "available_values": [], "default": SERVICE},
            {"name": "version", "prefix": "version", "available_values": [], "default": "*"},
        ],
        "template_variable_presets": [
            {"name": "Only the current version", "template_variables": [{"name": "version", "value": "*"}]},
        ],
        "notify_list": [],
        "widgets": header() + [health(), golden_signals(), why(), saturation(), business(), delivery()],
    }
    s = json.dumps(b)
    s = (s.replace("__SLO_ID__", slo_id or "")
          .replace('"__MON_ERRORS__"', '"%s"' % monitors.get("errors", ""))
          .replace('"__MON_P95__"', '"%s"' % monitors.get("p95", "")))
    return json.loads(s)
