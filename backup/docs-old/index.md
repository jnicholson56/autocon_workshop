# Ansible Network Automation Workshop

A 4-hour, hands-on lab that automates a small multi-NOS network built with
[Containerlab](https://containerlab.dev), then verifies and monitors it with SuzieQ,
Prometheus, gnmic and Grafana.

## Lab topology

| Node | Role | Image | Mgmt IP |
|------|------|-------|---------|
| `srl-01` | Nokia SR Linux | `ghcr.io/nokia/srlinux` | 172.20.20.11 |
| `frr-spine` | FRRouting | `localhost/frr-mon` | 172.20.20.12 |
| `frr-leaf` | FRRouting | `localhost/frr-mon` | 172.20.20.13 |
| `client-1`, `client-2` | Traffic generators (iperf3) | `python:3.13-alpine` | 172.20.20.21 / .22 |
| `suzieq` | State verification | `localhost/suzieq` | 172.20.20.30 |

The topology is defined in `workshop.clab.yml` and the Ansible inventory in `inventory.yml`.

## Prerequisites

- Docker (Docker Desktop, OrbStack, or WSL2) **or** a GitHub Codespace
- Containerlab
- Python 3 with the packages in `requirements.txt`
- Ansible collections from `requirements.yml`

```bash
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
```

!!! note
    Pure container NOS images keep the whole lab within roughly 4 GB of RAM.

## Agenda

1. [Foundations & Inventory](module-1.md)
2. [Declarative BGP & Jinja2](module-2.md)
3. [SuzieQ State Verification](module-3.md)
4. [Observability & Telemetry](module-4.md)
