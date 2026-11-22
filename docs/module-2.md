# Module 2: Declarative BGP & Jinja2

**Time:** 60 minutes

## Objectives

- Describe the BGP design once, as data, and render it for two very different platforms:
    - **FRR** takes CLI text, so its template produces `vtysh` commands.
    - **SR Linux** takes structured data that follows its YANG model, so its template produces JSON.
- Write a playbook that runs both platforms in one execution.
- See idempotency: a second run changes nothing, and a data change touches only what it affects.
- Verify the result with checks written for each platform.

## 1. The lab already runs BGP. What is new?

The lab starts with eBGP sessions up and each router advertising its loopback. The playbook you
run in this module takes over that configuration and adds one thing to every router: a
**service loopback** in `10.20.0.0/24`, advertised into BGP.

```text
AS 65001            AS 65000             AS 65002
srl-01 ---------- frr-spine ---------- frr-leaf
10.1.0.2   10.1.0.1  10.1.0.6   10.1.0.5
```

| Router | AS | Loopback | New service loopback |
|--------|----|----------|----------------------|
| `srl-01` | 65001 | 10.0.0.1/32 | 10.20.0.1/32 |
| `frr-spine` | 65000 | 10.0.0.2/32 | 10.20.0.2/32 |
| `frr-leaf` | 65002 | 10.0.0.3/32 | 10.20.0.3/32 |

## 2. The data model

Each router has a file in `host_vars/` with the same structure. Ansible loads it automatically
for the host with the matching name.

```yaml title="host_vars/frr-leaf.yml"
bgp:
  asn: 65002
  router_id: 10.0.0.3
  service_loopback: 10.20.0.3/32     # new in Module 2
  advertise:                         # prefixes already advertised by the lab
    - 10.0.0.3/32
    - 172.16.1.0/24
  neighbors:
    - { address: 10.1.0.6, asn: 65000, description: frr-spine }
```

Compare it with `host_vars/srl-01.yml` and `host_vars/frr-spine.yml`. The structure is identical,
whatever the vendor. That is what lets one set of tooling serve every platform.

## 3. The templates

Both templates read the `bgp` variable. They differ only in the output format.

=== "FRR (text)"

    ```jinja title="playbooks/templates/frr_bgp.j2"
    interface lo
     ip address {{ bgp.service_loopback }}
    exit
    !
    router bgp {{ bgp.asn }}
     bgp router-id {{ bgp.router_id }}
    {% for n in bgp.neighbors %}
     neighbor {{ n.address }} remote-as {{ n.asn }}
     neighbor {{ n.address }} description {{ n.description }}
    {% endfor %}
     !
     address-family ipv4 unicast
    {% for prefix in bgp.advertise + [bgp.service_loopback] %}
      network {{ prefix }}
    {% endfor %}
    {% for n in bgp.neighbors %}
      neighbor {{ n.address }} activate
    {% endfor %}
     exit-address-family
    exit
    ```

=== "SR Linux (JSON)"

    ```jinja title="playbooks/templates/srl_bgp.json.j2"
    {
      "interface": [
        {
          "name": "lo0",
          "admin-state": "enable",
          "subinterface": [
            {
              "index": 0,
              "admin-state": "enable",
              "ipv4": {
                "admin-state": "enable",
                "address": [ { "ip-prefix": "{{ bgp.service_loopback }}" } ]
              }
            }
          ]
        }
      ],
      "network-instance": [
        {
          "name": "default",
          "interface": [ { "name": "lo0.0" } ],
          "protocols": {
            "bgp": {
              "autonomous-system": {{ bgp.asn }},
              "router-id": "{{ bgp.router_id }}",
              "neighbor": [
    {% for n in bgp.neighbors %}
                {
                  "peer-address": "{{ n.address }}",
                  "peer-as": {{ n.asn }},
                  "peer-group": "ebgp",
                  "description": "{{ n.description }}"
                }{{ "," if not loop.last }}
    {% endfor %}
              ]
            }
          }
        }
      ],
      "routing-policy": {
        "prefix-set": [
          {
            "name": "default_bgp_advertise",
            "prefix": [
    {% for prefix in bgp.advertise + [bgp.service_loopback] %}
              { "ip-prefix": "{{ prefix }}", "mask-length-range": "exact" }{{ "," if not loop.last }}
    {% endfor %}
            ]
          }
        ]
      }
    }
    ```

On SR Linux, a prefix is only advertised if it is in the `default_bgp_advertise` prefix set, so
the template manages that set too.

## 4. The playbook

```yaml title="playbooks/deploy_bgp.yml"
- name: Configure the FRR routers (text template)
  hosts: frr
  gather_facts: false
  tasks:
    - name: Render the vtysh configuration on the router
      ansible.builtin.template:
        src: frr_bgp.j2
        dest: /tmp/workshop-bgp.conf
        mode: "0644"
      notify: Apply the FRR configuration

  handlers:
    - name: Apply the FRR configuration
      ansible.builtin.command: vtysh -f /tmp/workshop-bgp.conf
      changed_when: true

- name: Configure SR Linux (structured JSON)
  hosts: srl
  gather_facts: false
  tasks:
    - name: Apply the rendered JSON to the candidate datastore and commit
      nokia.srlinux.config:
        update:
          - path: "/"
            value: "{{ lookup('ansible.builtin.template', 'srl_bgp.json.j2') }}"
```

Two plays, two approaches:

- **FRR:** the template is rendered into a file on the router. Ansible only reports a change when
  the file content changes, and only then does the **handler** apply it with `vtysh -f`.
- **SR Linux:** the module sends the data to the router, which compares it with its own
  configuration. It reports a change only if something differs.

## 5. Run it

Preview the FRR change first. `--check` changes nothing and `--diff` shows what would be written:

```bash
ansible-playbook playbooks/deploy_bgp.yml --check --diff -l frr
```

Now deploy to all three routers:

```bash
ansible-playbook playbooks/deploy_bgp.yml --diff
```

You should see `changed` on all three routers. On SR Linux the diff lists the new loopback and
its prefix-set entry, and nothing else, because everything else in the data already matched.

### Idempotency

Run the exact same command again:

```bash
ansible-playbook playbooks/deploy_bgp.yml
```

```text
frr-leaf  : ok=1  changed=0
frr-spine : ok=1  changed=0
srl-01    : ok=1  changed=0
```

Nothing changed, and the handler did not run. Playbooks describe the **desired state**, not a
sequence of commands, so running them again is safe.

## 6. Verify

```bash
ansible-playbook playbooks/verify_bgp.yml
```

This playbook checks that every neighbor in `host_vars/` is established and that every router has
every service loopback. Notice that each platform is checked differently:

- **FRR:** run `vtysh -c 'show bgp summary json'` and parse the text output.
- **SR Linux:** ask for `.../neighbor[peer-address=X]/session-state` and get one value back.

You can also look at the result yourself:

```bash
ansible frr-leaf -m ansible.builtin.command -a "vtysh -c 'show bgp ipv4 unicast'"
```

## 7. Exercise: change the data, not the commands

1. In `host_vars/frr-leaf.yml`, change the neighbor's description from `frr-spine` to
   `spine-uplink`.
2. Run `ansible-playbook playbooks/deploy_bgp.yml --diff`.
3. Only `frr-leaf` changes, and the diff shows the single changed line.
4. Check it: `ansible frr-leaf -m ansible.builtin.command -a "vtysh -c 'show bgp summary'"`.
5. Change it back and run the playbook again.

!!! warning "Playbooks add and update. They do not remove."
    If you delete a neighbor from `host_vars/`, the playbook stops managing it, but it stays on the
    router. Removing configuration needs an explicit `no neighbor ...` on FRR or a `delete` on
    SR Linux. Real automation often handles removals the same way.

!!! note
    The changes live only in the routers' running configuration. Redeploy the lab to start clean:
    `sudo containerlab redeploy -t workshop.clab.yml`.

## 8. Check your understanding

1. Why do both templates read the same `bgp` variable?
2. On FRR, what decides whether the handler runs? On SR Linux, what decides whether the task
   reports `changed`?
3. What would you change to add a fourth router?
4. Why does `verify_bgp.yml` need different tasks for FRR and SR Linux?

??? tip "Answers"
    1. One source of truth: a change is made once and both platforms get it, so the routers cannot
       drift apart.
    2. FRR: whether the rendered file differs from the one on the router. SR Linux: whether the
       data differs from the router's configuration.
    3. Add a `host_vars/<name>.yml` file and an inventory entry. The templates and playbooks stay
       the same.
    4. The platforms return different things: text that has to be parsed, versus structured data.
       Module 3 removes that difference.

Next: [Module 3: SuzieQ State Verification](module-3.md).
