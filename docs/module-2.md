# Module 2: Variables, Facts & Loops

**Time:** 45 minutes

## Objectives

- Understand variable precedence and how to use facts
- Use `set_fact` for runtime computation
- Write loops with the modern `loop:` syntax
- Apply conditionals with `when:`

## 1. Variables & Facts

### Gathering facts

Facts are system information collected from targets (OS, IP addresses, CPU, etc.).

```yaml title="playbooks/02_variables_facts.yml (excerpt)"
- name: Show system facts
  hosts: servers
  gather_facts: true

  tasks:
    - name: Display the OS family
      ansible.builtin.debug:
        msg: "This host runs on {{ ansible_os_family }}"

    - name: Display the hostname
      ansible.builtin.debug:
        msg: "Hostname is {{ ansible_hostname }}"

    - name: Display total memory
      ansible.builtin.debug:
        msg: "Total memory: {{ ansible_memtotal_mb }} MB"
```

Run it:

```bash
ansible-playbook playbooks/02_variables_facts.yml
```

### Variable precedence

Ansible loads variables from many sources. The order (low to high):

1. Role defaults
2. Inventory file variables
3. Host vars
4. Playbook vars
5. `set_fact` (runtime)
6. Extra vars (`-e`) — highest priority

### Exercise: Override a variable

1. Add a variable in `inventory.yml` under the `servers` group:

```yaml
    servers:
      hosts:
        server1:
          ansible_host: 172.20.20.13
      vars:
        welcome_message: "Welcome to the workshop!"
```

2. Use it in a playbook:

```yaml title="playbooks/02_variables_facts.yml (excerpt)"
- name: Use inventory variable
  hosts: servers
  gather_facts: false

  tasks:
    - name: Show the welcome message
      ansible.builtin.debug:
        msg: "{{ welcome_message }}"
```

3. Override it on the command line:

```bash
ansible-playbook playbooks/02_variables_facts.yml -e "welcome_message=Hello from CLI!"
```

### Runtime variables with `set_fact`

```yaml title="playbooks/02_variables_facts.yml (excerpt)"
- name: Compute a value at runtime
  hosts: servers
  gather_facts: true

  tasks:
    - name: Set a fact based on system info
      ansible.builtin.set_fact:
        is_ubuntu: "{{ 'Ubuntu' in ansible_distribution }}"

    - name: Show the computed fact
      ansible.builtin.debug:
        var: is_ubuntu
```

## 2. Loops

### The modern `loop:` syntax

```yaml title="playbooks/03_conditionals_loops.yml (excerpt)"
- name: Install packages
  hosts: servers
  gather_facts: false

  tasks:
    - name: Install a list of packages
      ansible.builtin.package:
        name: "{{ item }}"
        state: present
      loop:
        - curl
        - wget
        - vim
```

Run it:

```bash
ansible-playbook playbooks/03_conditionals_loops.yml --check
```

`--check` shows what would change without making changes.

### Looping over dictionaries

```yaml title="playbooks/03_conditionals_loops.yml (excerpt)"
- name: Create users
  hosts: servers
  gather_facts: false

  tasks:
    - name: Create system users
      ansible.builtin.user:
        name: "{{ item.name }}"
        state: "{{ item.state | default('present') }}"
      loop:
        - { name: workshop, state: present }
        - { name: backup, state: absent }
```

## 3. Conditionals

### Using `when:`

```yaml title="playbooks/03_conditionals_loops.yml (excerpt)"
- name: Conditional task
  hosts: servers
  gather_facts: true

  tasks:
    - name: Show OS-specific message
      ansible.builtin.debug:
        msg: "This is a Debian-based system"
      when: ansible_os_family == "Debian"

    - name: Show hostname on Ubuntu only
      ansible.builtin.debug:
        msg: "Ubuntu host: {{ ansible_hostname }}"
      when:
        - ansible_os_family == "Debian"
        - ansible_distribution == "Ubuntu"
```

### Exercise: Combine loops and conditionals

Write a playbook that:

1. Loops over a list of packages
2. Installs only those that are not already installed (use `when:` with `ansible_facts`)
3. Prints which packages were skipped

```yaml title="playbooks/03_conditionals_loops.yml"
- name: Conditional package installation
  hosts: servers
  gather_facts: true

  vars:
    packages_to_check:
      - nginx
      - python3
      - git

  tasks:
    - name: Check and install packages conditionally
      ansible.builtin.package:
        name: "{{ item }}"
        state: present
      loop: "{{ packages_to_check }}"
      when: not (item in ansible_pkg_mgr_facts.installed_packages | default([]))

    - name: Report skipped packages
      ansible.builtin.debug:
        msg: "{{ item }} is already installed"
      loop: "{{ packages_to_check }}"
      when: item in ansible_pkg_mgr_facts.installed_packages | default([])
```

## 4. Check your understanding

1. What is the difference between `set_fact` and a variable defined in `inventory.yml`?
2. How do you loop over a list of dictionaries?
3. Can you combine multiple conditions with `when:`? How?

??? tip "Answers"
    1. `set_fact` sets a variable at runtime during playbook execution; inventory variables are loaded before the play starts. `set_fact` takes precedence over inventory vars.
    2. Use `loop:` with a list of dictionaries, then access keys with `{{ item.key }}`.
    3. Yes — list multiple conditions under `when:` as a YAML list; they are ANDed together.

Next: [Module 3: Templates & Roles](module-3.md).
