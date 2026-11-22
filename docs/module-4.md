# Module 4: Observability & Telemetry

**Time:** 45 minutes

Modules 2 and 3 checked **state**: is BGP up, are the routes there. This module looks at **traffic**
over time.

## Objectives

- Follow telemetry from the routers to a dashboard.
- Use Ansible to start a traffic flow, then confirm in Prometheus that a router is forwarding it.
- Cause a failure with a playbook and watch it appear in Grafana, in Prometheus alerts, and in
  SuzieQ.

## 1. The telemetry pipeline

```text
srl-01 --gNMI--> gnmic --:9273--> Prometheus <--scrape-- FRR exporters (:9100, :9342)
                                      |
                                      v
                                   Grafana
```

| Piece | What it does | From your machine |
|-------|--------------|-------------------|
| **gnmic** | Subscribes to SR Linux over gNMI (interface counters, BGP state every 10 s) and publishes them as Prometheus metrics | |
| **Prometheus** | Scrapes gnmic and the FRR exporters every 10 s, stores the time series, and evaluates alert rules | <http://localhost:9091> |
| **Grafana** | Dashboards | <http://localhost:3000> |
| **Ansible** | Creates traffic, makes changes, and checks the result | |

FRR is not streamed. Prometheus scrapes `node_exporter` (interfaces) and `frr_exporter` (BGP) from
each FRR router instead. The dashboard combines both sources.

## 2. Look at the collector configuration

```bash
cat configs/gnmic/gnmic.yml
```

Find the `subscriptions` section. Each one lists YANG paths and a `sample-interval`, for example:

```yaml
subscriptions:
  interface:
    paths:
      - /interface[name=ethernet-*]/statistics
      - /interface[name=ethernet-*]/oper-state
    stream-mode: sample
    sample-interval: 10s
```

Check that Prometheus is receiving the gnmic data:

```bash
curl -s 'http://127.0.0.1:9091/api/v1/query?query=srl_interface_out_octets' | head -c 400
```

## 3. Open Grafana

1. Open <http://localhost:3000>. In a Codespace, use the **Ports** tab.
2. The **Workshop Network Overview** dashboard is the home page. Anonymous viewing is enabled. To
   edit, sign in as `admin` with the password `workshop`.
3. Find the **BGP session state**, **Interface traffic in** and **Interface traffic out** panels.
   Right now traffic is close to zero.

## 4. Generate traffic and check it

The playbook has three steps:

1. Start an `iperf3` server on `client-2`.
2. Start a 45-second, 20 Mbps UDP flow from `client-1` to `client-2`. It crosses `srl-01`,
   `frr-spine` and `frr-leaf`.
3. Ask Prometheus for the transmit rate on `srl-01` `ethernet-1/1` and assert that it is above
   5 Mbps.

```yaml title="playbooks/traffic_and_verify.yml (the check)"
- name: Ask Prometheus for the transmit rate of ethernet-1/1 (it refreshes every 10 seconds)
  ansible.builtin.uri:
    url: "{{ prometheus_url }}/query?query={{ rate_query | urlencode }}"
    return_content: true
  register: prometheus
  until: >-
    prometheus.json.data.result | length > 0 and
    prometheus.json.data.result[0].value[1] | float > min_bps | int
  retries: 8
  delay: 10
```

The `rate_query` is a PromQL expression:

```text
rate(srl_interface_out_octets{router="srl-01",interface_name="ethernet-1/1"}[30s]) * 8
```

It turns the byte counter into bits per second, averaged over 30 seconds.

Open Grafana next to your terminal and run it:

```bash
ansible-playbook playbooks/traffic_and_verify.yml
```

Watch the **Interface traffic** panels rise. The playbook retries until the data reaches
Prometheus, passes the check, then waits for the flow and prints the iperf3 receiver summary.

!!! note
    The rate it reports can be lower than 20 Mbps. It is averaged over 30 seconds, and the
    playbook stops as soon as the value passes the threshold, while the flow is still ramping up
    in the graph. Try `-e rate=50M -e duration=90` for a longer, heavier flow.

## 5. Day-2: cause an outage and watch it

Start a long flow in one terminal:

```bash
ansible-playbook playbooks/traffic_and_verify.yml -e duration=180
```

In a second terminal, shut down the port that `srl-01` uses to reach `frr-spine`. The lab provides
a playbook for this:

```bash
ansible-playbook playbooks/scenario.yml -e scenario=port-down -l srl-01
```

Look at what happens:

- **Grafana:** traffic on `ethernet-1/1` falls to zero, and BGP sessions drop.
- **Prometheus:** open <http://localhost:9091/alerts>. After about 20 seconds `PortDown` and
  `BGPSessionDown` fire for `frr-spine`.
- **SuzieQ:** the playbook ends by asking SuzieQ for the BGP assertion, and confirms the network
  is broken, as expected.

!!! note "There is no second path"
    The lab is a single chain, so traffic cannot reroute. It stops until the port is back. In a
    network with redundant links, the graph would move to another interface instead.

Restore the port:

```bash
ansible-playbook playbooks/scenario.yml -e scenario=port-up -l srl-01
```

The playbook waits for SuzieQ to report a healthy network. Within a minute, the alerts clear and
traffic resumes if the flow is still running.

??? tip "Other scenarios"
    `playbooks/scenario.yml` also supports `bgp-down`, `bgp-up`, `reset` and `status`. For example,
    `-e scenario=bgp-down -l frr-leaf` shuts down only the BGP session and leaves the port up.
    Compare the two in Grafana.

## 6. Check your understanding

1. How does sampled gNMI telemetry (every 10 seconds) differ from SNMP polling for the kind of
   assertion you wrote?
2. Why does the playbook retry instead of querying Prometheus once?
3. Why use Prometheus for the traffic check, and SuzieQ for BGP state?

??? tip "Answers"
    1. The router pushes data on a schedule, so it is fresher and no longer depends on a poller
       asking the router. You still have to allow for the sample and scrape intervals.
    2. Data takes up to two 10-second intervals to travel from the router through gnmic to
       Prometheus.
    3. Prometheus stores numbers over time, which suits rates and thresholds. SuzieQ keeps discrete
       state and answers questions like "is this session established" and "what route is used".

## Wrap-up

You described a network once and configured two vendors from it (Module 2), proved it with
normalized state (Module 3), and watched it with telemetry (Module 4). The same ideas apply to any
platform with an API.
