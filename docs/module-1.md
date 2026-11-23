# Module 1: Foundations & Inventory
#
# **Time:** 60 minutes
#
# ## Objectives
#
# - Understand what Ansible is and why it matters
# - Write and run your first playbook
# - Read and modify the inventory
# - Run ad-hoc commands to query state without writing a playbook

## 1. What is Ansible?

Ansible is an open-source automation tool that:

- **Agentless** — no software to install on target machines, uses SSH
- **Push-based** — runs from a control machine to remote targets
- **Idempotent** — running the same playbook twice produces the same result
- **Declarative** — you describe *what* you want, not *how* to do it

```text
┌─────────────┐     SSH      ┌──────────┐
│  Control    │──────────────▶│  Target   │
│  Machine    │               │  Host     │
└─────────────┘               └──────────┘
   (your laptop)                  (server)
```

## 2. Your First Playbook

Create a file called `first_playbook.yml`:

```yaml title="playbooks/01_first_playbook.yml"
- name: My first Ansible playbook
  hosts: servers
  gather_facts: false

  tasks:
    - name: Print a greeting
      ansible.builtin.debug:
        msg: "Hello from Ansible!"

    - name: Create a directory
      ansible.builtin.file:
        path: /tmp/workshop
        state: directory
        mode: "0755"

    - name: Create a file
      ansible.builtin.copy:
        content: "This file was created by Ansible\n"
        dest: /tmp/workshop/hello.txt
        mode: "0644"
```

### Run it

```bash
ansible-playbook playbooks/01_first_playbook.yml
```

You should see output like:

```text
PLAY [My first Ansible playbook] ***********************************************

TASK [Print a greeting] ********************************************************
ok: [server1] => {
    "msg": "Hello from Ansible!"
}

TASK [Create a directory] ******************************************************
changed: [server1]

TASK [Create a file] ***********************************************************
changed: [server1]

PLAY RECAP *********************************************************************
server1                  : ok=3    changed=2    unreachable=0    failed=0
```

### Run it again (idempotency)

```bash
ansible-playbook playbooks/01_first_playbook.yml
```

Now you should see `changed=0` for the directory and file tasks — nothing changed because the desired state already exists.

## 3. The Inventory

The inventory defines which hosts Ansible can manage. Look at `inventory.yml`:

```yaml title="inventory.yml"
all:
  children:
    srl:
      hosts:
        r1:
          ansible_host: 172.20.20.11
        r2:
          ansible_host: 172.20.20.12
    servers:
      hosts:
        server1:
          ansible_host: 172.20.20.13
```

### Explore the inventory

```bash
# List all hosts and groups
ansible-inventory --list

# Show a graph view
ansible-inventory --graph
```

Output:

```text
@all:
  |--@srl:
  |  |--r1
  |  --r2
  --@servers:
     --server1
```

### Exercise: Add a new host

1. Open `inventory.yml`
2. Add a new host to the `servers` group:

```yaml
    servers:
      hosts:
        server1:
          ansible_host: 172.20.20.13
        server2:            # <-- add this
          ansible_host: 172.20.20.14  # <-- and this
```

3. Verify with `ansible-inventory --graph`

## 4. Ad-hoc Commands

Ad-hoc commands let you run single tasks without writing a playbook.

### Exercise 4.1: Check connectivity

```bash
ansible all -m ping
```

All three hosts should return `pong`.

### Exercise 4.2: Run a command on one group

```bash
ansible servers -m ansible.builtin.command -a "uptime"
```

### Exercise 4.3: Run on all hosts

```bash
ansible all -m ansible.builtin.command -a "whoami"
```

### Exercise 4.4: Target a single host

```bash
ansible r1 -m ansible.builtin.command -a "hostname"
```

## 5. Check your understanding

1. What does "idempotent" mean in Ansible?
2. Why might you use `gather_facts: false` in a playbook?
3. How do you run an ad-hoc command against just the `srl` group?

??? tip "Answers"
    1. Running the same task multiple times produces the same result — no unintended changes on subsequent runs.
    2. Skipping fact gathering speeds up execution when you don't need system information.
    3. `ansible srl -m ping`

Next: [Module 2: Variables, Facts & Loops](module-2.md).
