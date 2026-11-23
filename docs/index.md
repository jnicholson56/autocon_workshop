# Beginner Ansible Workshop

A 4-hour, hands-on introduction to Ansible fundamentals — playbooks, inventory, variables, templates, roles, and error handling. Built on a simple Containerlab topology with 2 Nokia SR Linux routers and 1 Ubuntu server.

## Lab topology

```
              ┌────────┐
              │   r1   │ (Nokia SR Linux)
              │ 172.20.20.11 ──┐
              └──┬─────┬──────┘
                 │     │
           e1-1 ─┘     └─ e1-2
                 │       │
          ┌──────┴──┐  ┌─┴──────────┐
          │   r2    │  │  server1   │ (Ubuntu)
          │172.20.20.12│ │172.20.20.13
          └───────────┘  └──────────┘
```

| Node | Role | Image | Mgmt IP | Ansible Group |
|------|------|-------|---------|---------------|
| `r1` | Nokia SR Linux | `ghcr.io/nokia/srlinux` | 172.20.20.11 | srl |
| `r2` | Nokia SR Linux | `ghcr.io/nokia/srlinux` | 172.20.20.12 | srl |
| `server1` | Ubuntu server | `ghcr.io/hellt/ubuntu-netlab` | 172.20.20.13 | servers |

The topology is defined in `workshop-beginner.clab.yml` and the Ansible inventory in `inventory.yml`.

## Prerequisites

- Docker (Docker Desktop, OrbStack, or WSL2) **or** a GitHub Codespace
- Containerlab — install from [GitHub releases](https://github.com/srl-labs/containerlab/releases)
- Python 3 with the packages in `requirements.txt`

```bash
pip install -r requirements.txt
```

!!! note
    Keep Docker memory allocation at 4 GB or higher so SR Linux containers start reliably.

## Agenda

1. [Foundations & Inventory](module-1.md)
2. [Variables, Facts & Loops](module-2.md)
3. [Templates & Roles](module-3.md)
4. [Handlers, Tags & Error Handling](module-4.md)
