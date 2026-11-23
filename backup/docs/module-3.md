# Module 3: SuzieQ State Verification

**Time:** 45 minutes

## Objectives

- Understand why a **normalized state engine** is easier to work with than parsing each vendor's CLI.
- Query SuzieQ from its CLI and its REST API.
- Write a validation playbook that makes REST calls and uses `ansible.builtin.assert`.
- Break the network on purpose and watch the playbook catch it.

## 1. Why SuzieQ?

In Module 2, `verify_bgp.yml` needed one set of tasks for FRR (parse JSON from `vtysh`) and
another for SR Linux (read YANG paths). Every new vendor means more custom code.

```text
Without SuzieQ:
  Ansible ---> FRR       (parse 'show bgp summary json')  --+
  Ansible ---> SR Linux  (read YANG paths)                --+--> custom logic per platform

With SuzieQ:
  FRR      ---+
  SR Linux ---+--> SuzieQ poller ---> database ---> one schema ---> Ansible (REST)
```

SuzieQ polls the devices, converts what they return into common tables (BGP, routes, interfaces,
and more), and serves them through one CLI and one REST API.

!!! note "SR Linux support is added by this lab"
    SuzieQ has no built-in support for SR Linux. The lab's SuzieQ image adds it: the poller logs
    in to `srl-01` over SSH, runs `info from state ... | as json` commands, and converts the answer
    into the same tables the FRR routers fill. The code is in `configs/suzieq/srlinux/`. This is
    what adding a new vendor to a normalized tool looks like. Once the data is in the common
    schema, nothing downstream cares where it came from.

## 2. Explore with the SuzieQ CLI

SuzieQ runs in the `suzieq` container. Run its CLI with `docker exec`:

```bash
docker exec clab-ansible-workshop-suzieq suzieq-cli device show --columns='hostname vendor os version status'
```

```text
    hostname  vendor       os      version status
0   frr-leaf  Alpine    linux  Linux v3.22  alive
1  frr-spine  Alpine    linux  Linux v3.22  alive
2     srl-01   Nokia  srlinux       26.7.2  alive
```

### BGP sessions

```bash
docker exec clab-ansible-workshop-suzieq suzieq-cli bgp show --columns='hostname peer peerHostname asn peerAsn state'
```

```text
    hostname      peer peerHostname    asn  peerAsn        state
0   frr-leaf  10.1.0.6    frr-spine  65002    65000  Established
1  frr-spine  10.1.0.2       srl-01  65000    65001  Established
2  frr-spine  10.1.0.5     frr-leaf  65000    65002  Established
3     srl-01  10.1.0.1    frr-spine  65001    65000  Established
```

Both ends of every session are there, and SuzieQ worked out which router is on the other end
(`peerHostname`), including across vendors.

### Routes

Which way does `frr-leaf` send traffic for the service loopback on `srl-01`? Then ask the same
question from `srl-01`'s side. The command is identical for both vendors:

```bash
docker exec clab-ansible-workshop-suzieq suzieq-cli route lpm --hostname=frr-leaf --address=10.20.0.1 --columns='hostname prefix nexthopIps protocol'
docker exec clab-ansible-workshop-suzieq suzieq-cli route lpm --hostname=srl-01 --address=10.20.0.3 --columns='hostname prefix nexthopIps protocol'
```

### Interfaces

```bash
docker exec clab-ansible-workshop-suzieq suzieq-cli interface show --hostname=srl-01 --columns='ifname type state adminState ipAddressList'
```

### Built-in assertion

SuzieQ can check BGP for you: AS numbers, session state, and address-family agreement.

```bash
docker exec clab-ansible-workshop-suzieq suzieq-cli bgp assert
```

Every row should say `pass`. Because SuzieQ sees both ends of each session, a failure is reported
from both sides.

## 3. The REST API

The same data is available over HTTP on `127.0.0.1:8000`. Requests need the lab API key in an
`access_token` header (it is set in `configs/suzieq/suzieq-cfg.yml`).

```bash
curl -s -H 'access_token: 496157e6e869ef7f3d6ecb24a6f6d847b224ee4f' \
  'http://127.0.0.1:8000/api/v2/bgp/show?view=latest&columns=hostname&columns=peer&columns=state'
```

```json
[{"hostname":"frr-leaf","peer":"10.1.0.6","state":"Established"}, ...]
```

The URL is `/api/v2/<table>/<verb>`. Try `route/show`, `route/lpm`, `interface/show` and
`bgp/assert`.

## 4. The validation playbook

It targets `localhost` and calls SuzieQ. It never logs in to a router.

```yaml title="playbooks/validate_network.yml (excerpt)"
- name: Validate the fabric with SuzieQ
  hosts: localhost
  gather_facts: false
  vars:
    suzieq_url: http://127.0.0.1:8000/api/v2
    suzieq_headers:
      access_token: 496157e6e869ef7f3d6ecb24a6f6d847b224ee4f
  tasks:
    - name: Ask SuzieQ for every BGP session
      ansible.builtin.uri:
        url: "{{ suzieq_url }}/bgp/show?view=latest"
        headers: "{{ suzieq_headers }}"
        return_content: true
      register: sq_bgp

    - name: Every session is Established
      ansible.builtin.assert:
        that: item.state == 'Established'
        fail_msg: "{{ item.hostname }} -> {{ item.peer }} is {{ item.state }}"
      loop: "{{ sq_bgp.json }}"
```

The full playbook has these checks:

1. SuzieQ **polls every router** in the inventory and they are all alive.
2. SuzieQ knows the **expected number of sessions**, calculated from `host_vars/`, and each one is
   `Established`.
3. **Every router** learned every other router's service loopback **through BGP**, `srl-01`
   included.
4. SuzieQ's own `bgp/assert` passes on every session.

## 5. Run it on a healthy network

Make sure you ran `deploy_bgp.yml` in Module 2, then:

```bash
ansible-playbook playbooks/validate_network.yml
```

You should see passes for every check and `failed=0`.

## 6. Exercise: break it on purpose

Make `frr-spine` expect the wrong AS number for `frr-leaf`.

1. In `host_vars/frr-spine.yml`, change the `frr-leaf` neighbor from `asn: 65002` to
   `asn: 65999`.
2. Push the change:

    ```bash
    ansible-playbook playbooks/deploy_bgp.yml --diff
    ```

3. Wait about a minute: SuzieQ polls every 15 seconds, and BGP takes a moment to give up. Then run:

    ```bash
    ansible-playbook playbooks/validate_network.yml
    ```

4. The playbook fails. Look for the `msg:` line, which names the session:

    ```text
    msg: frr-spine -> 10.1.0.5 is NotEstd (no reason given)
    ```

5. Restore `asn: 65002`, run `deploy_bgp.yml` again, wait a minute, and validate again. Everything
   should be green.

??? tip "The playbook still passes right after the change"
    SuzieQ shows what it **last polled**, so it can report the old state for up to 15 seconds. If
    the validation passes straight after step 2, wait and run it again. This is the same issue
    you would handle in a CI/CD pipeline.

??? tip "Stuck? Check the API address and key"
    The REST API listens on `127.0.0.1:8000` and answers `401` without the `access_token` header.
    `curl -s -H 'access_token: <key>' http://127.0.0.1:8000/api/v2/bgp/show` is a quick test.

## 7. Check your understanding

1. How does using SuzieQ simplify the playbook when you add a Cisco or Arista node?
2. Why did the validation pass right after the change, and how would you handle that in a
   pipeline?
3. What is the difference between checking `/bgp/show` yourself and calling `/bgp/assert`?

??? tip "Answers"
    1. The playbook asks the same question of the same schema. Only the SuzieQ poller needs to
       support the new platform.
    2. SuzieQ reports the last poll. A pipeline should retry (`until`/`retries`) or wait longer
       than the poll interval before judging the result.
    3. `/bgp/show` returns data and you decide what is correct, for example your expected
       neighbors. `/bgp/assert` applies SuzieQ's generic rules (session up, AS numbers agree) and
       knows nothing about your design.

Next: [Module 4: Observability & Telemetry](module-4.md).
