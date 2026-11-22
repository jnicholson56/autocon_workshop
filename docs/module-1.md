# Module 1: Ansible Fundamentals & Multi-NOS Inventory

**Time:** 45 minutes

## Objectives

- Verify the lab is running in Containerlab.
- Read the Ansible inventory and see how each platform gets its own connection method:
    - **FRR** (`frr-spine`, `frr-leaf`): SSH with a key, running `vtysh` commands.
    - **Nokia SR Linux** (`srl-01`): JSON-RPC over HTTPS, using the `nokia.srlinux` collection.
    - **Clients** (`client-1`, `client-2`): `docker exec`, using the `community.docker` collection.
- Run ad-hoc commands to query state without writing a playbook.

## 1. Prepare your environment

From the repository root:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
chmod 600 configs/ssh/lab_key
```

!!! note
    `ansible.cfg` points Ansible at `inventory.yml` and installs collections into `./collections`,
    so you do not need `-i` on every command.

## 2. Verify the lab

```bash
sudo containerlab deploy -t workshop.clab.yml   # skip if already running
sudo containerlab inspect -t workshop.clab.yml
```

You should see these nodes running:

| Node | Role | Mgmt IP |
|------|------|---------|
| `srl-01` | Nokia SR Linux | 172.20.20.11 |
| `frr-spine` | FRRouting | 172.20.20.12 |
| `frr-leaf` | FRRouting | 172.20.20.13 |
| `client-1`, `client-2` | Alpine endpoints | 172.20.20.21 / .22 |
| `suzieq`, `grafana`, `prometheus`, `gnmic` | Monitoring (used in Modules 3 and 4) | 172.20.20.30 to .33 |

## 3. Read the inventory

```bash
cat inventory.yml
ansible-inventory --graph
```

```text
@all:
  |--@srl:
  |  |--srl-01
  |--@frr:
  |  |--frr-spine
  |  |--frr-leaf
  |--@routers:
  |  |--@srl:
  |  |--@frr:
  |--@endpoints:
  |  |--client-1
  |  |--client-2
```

`routers` is a parent group that contains both `srl` and `frr`, so one command can reach every
router regardless of vendor.

### Key concept: connection plugins

=== "FRR"

    ```yaml
    frr:
      vars:
        ansible_user: admin
        ansible_ssh_private_key_file: "{{ inventory_dir }}/configs/ssh/lab_key"
        ansible_become: true
    ```

    The default `ssh` connection. Ansible logs in to a Linux shell and runs commands there.
    FRR is reached through `vtysh`.

=== "Nokia SR Linux"

    ```yaml
    srl:
      vars:
        ansible_connection: ansible.netcommon.httpapi
        ansible_network_os: nokia.srlinux.srlinux
        ansible_httpapi_use_ssl: true
    ```

    A model-driven API. Ansible sends JSON-RPC requests to the router, so you get structured data
    back instead of text.

=== "Clients"

    ```yaml
    endpoints:
      vars:
        ansible_connection: community.docker.docker
    ```

    There is no SSH on the clients. Ansible runs `docker exec` in the container.

The routers are reached through `127.0.0.1` on a port that Containerlab forwards
(`ansible_host` and `ansible_port` in the inventory), so this works the same on a laptop and in a
Codespace.

## 4. Ad-hoc commands

The syntax is:

```bash
ansible <host-or-group> -m <module> [-a "<arguments>"]
```

### Exercise 4.1: Reachability

```bash
ansible all -m ping
```

All five hosts should return `pong`.

!!! note
    `ping` here is the Ansible module, not ICMP. It checks that Ansible can connect and run a
    module on the target.

### Exercise 4.2: Inspect FRR

```bash
ansible frr -m ansible.builtin.command -a "vtysh -c 'show version'"
ansible frr -m ansible.builtin.command -a "vtysh -c 'show interface brief'"
ansible frr -m ansible.builtin.command -a "vtysh -c 'show bgp summary'"
```

!!! note
    You will see `Can't open configuration file /etc/frr/vtysh.conf` in the output. It is harmless.

BGP is already configured in this lab. `frr-spine` (AS 65000) should show two established
neighbors: `srl-01` and `frr-leaf`.

Ask for JSON instead of text:

```bash
ansible frr-spine -m ansible.builtin.command -a "vtysh -c 'show bgp summary json'"
```

### Exercise 4.3: Inspect SR Linux

The `nokia.srlinux.get` module takes a list of YANG paths. Pass the arguments as JSON:

```bash
ansible srl-01 -m nokia.srlinux.get -a '{"paths":[{"path":"/system/information"}]}'
```

The result is structured data: software version, boot time, and so on.

```bash
ansible srl-01 -m nokia.srlinux.get -a '{"paths":[{"path":"/interface[name=mgmt0]/oper-state"}]}'
ansible srl-01 -m nokia.srlinux.get -a '{"paths":[{"path":"/network-instance[name=default]/protocols/bgp/neighbor[peer-address=10.1.0.1]/session-state"}]}'
```

You can also run CLI commands through the API:

```bash
ansible srl-01 -m nokia.srlinux.cli -a '{"commands":["show version"]}'
```

### Exercise 4.4: Inspect the clients

```bash
ansible endpoints -m ansible.builtin.command -a "ip -4 addr show eth1"
```

### Exercise 4.5: Target a whole group

```bash
ansible routers -m ansible.builtin.command -a uptime
```

??? warning "Look closely at the `srl-01` answer"
    `frr-spine` and `frr-leaf` report the uptime of their containers. `srl-01` reports
    **your own laptop's** uptime. The `httpapi` connection never logs in to the router. Ansible
    runs `ansible.builtin.command` locally and only uses the router's API for modules written for
    it, such as `nokia.srlinux.*`.

    Use a module that matches the connection type.

## 5. Check your understanding

1. Why does the inventory use a different `ansible_connection` for `frr`, `srl` and `endpoints`?
2. What are the advantages of structured data (SR Linux) over text (FRR CLI)?
3. Why did `uptime` give a surprising answer for `srl-01`?
4. What happens if you run `ansible endpoints -m nokia.srlinux.get ...`?

??? tip "Answers"
    1. Each platform exposes a different management interface: a Linux shell over SSH, a JSON-RPC
       API, or a container runtime.
    2. Structured data can be filtered, compared and asserted on without parsing text.
    3. With `httpapi`, general-purpose modules run on the Ansible controller, not on the device.
    4. It fails with a module error: the clients have no SR Linux API, and the module expects the
       `httpapi` connection.

Next: [Module 2: Declarative BGP & Jinja2](module-2.md).
