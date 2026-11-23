# Module 4: Handlers, Tags & Error Handling

**Time:** 75 minutes (includes the lab exercise)

## Objectives

- Use handlers to trigger actions on change
- Apply tags for selective playbook execution
- Handle errors gracefully with block/rescue/always
- Complete the lab: deploy a web stack

## 1. Handlers

Handlers are tasks that run only when notified by other tasks.

```yaml title="playbooks/07_handlers_tags.yml (excerpt)"
- name: Configure services with handlers
  hosts: servers
  gather_facts: false

  tasks:
    - name: Deploy nginx configuration
      ansible.builtin.template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
        mode: "0644"
      notify: Restart nginx

    - name: Deploy site configuration
      ansible.builtin.template:
        src: site.conf.j2
        dest: /etc/nginx/sites-enabled/default
        mode: "0644"
      notify: Restart nginx

  handlers:
    - name: Restart nginx
      ansible.builtin.service:
        name: nginx
        state: restarted
```

### Key points

- Handlers run **once at the end** of the play, even if notified multiple times
- Handlers only run if a task reports `changed`
- Use `--handlers` to see which handlers would run

## 2. Tags

Tags let you run only specific parts of a playbook.

```yaml title="playbooks/07_handlers_tags.yml (excerpt)"
- name: Deploy web server with tags
  hosts: servers
  gather_facts: false

  tasks:
    - name: Install nginx
      ansible.builtin.package:
        name: nginx
        state: present
      tags: [install, packages]

    - name: Deploy configuration
      ansible.builtin.template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
        mode: "0644"
      tags: [config, deploy]

    - name: Start nginx
      ansible.builtin.service:
        name: nginx
        state: started
        enabled: true
      tags: [service, deploy]

    - name: Deploy index page
      ansible.builtin.template:
        src: index.html.j2
        dest: /var/www/html/index.html
        mode: "0644"
      tags: [content, deploy]
```

### Using tags

```bash
# Run only install tasks
ansible-playbook playbooks/07_handlers_tags.yml --tags install

# Run only deploy tasks (skips install)
ansible-playbook playbooks/07_handlers_tags.yml --tags deploy

# Skip content tasks
ansible-playbook playbooks/07_handlers_tags.yml --skip-tags content

# Run everything
ansible-playbook playbooks/07_handlers_tags.yml
```

## 3. Error Handling

### ignore_errors

Continue even if a task fails:

```yaml
- name: Try something that might fail
  ansible.builtin.command: /usr/bin/something
  ignore_errors: true
```

### failed_when

Define custom failure conditions:

```yaml
- name: Check if service is running
  ansible.builtin.command: systemctl is-active myservice
  register: result
  failed_when: "'inactive' in result.stdout"
```

### block / rescue / always

Like try/catch/finally:

```yaml title="playbooks/08_error_handling.yml (excerpt)"
- name: Graceful error handling
  hosts: servers
  gather_facts: false

  tasks:
    - name: Attempt to configure service
      block:
        - name: Deploy configuration
          ansible.builtin.template:
            src: service.conf.j2
            dest: /etc/service.conf
            mode: "0644"

        - name: Restart service
          ansible.builtin.service:
            name: myservice
            state: restarted

      rescue:
        - name: Log the failure
          ansible.builtin.debug:
            msg: "Configuration failed, rolling back..."

        - name: Restore backup configuration
          ansible.builtin.copy:
            src: /etc/service.conf.backup
            dest: /etc/service.conf
            mode: "0644"

      always:
        - name: Send notification
          ansible.builtin.debug:
            msg: "Task completed (success or failure)"
```

### Exercise: Write an error-handling playbook

Create `playbooks/08_error_handling.yml`:

```yaml title="playbooks/08_error_handling.yml"
- name: Error handling demonstration
  hosts: servers
  gather_facts: false

  tasks:
    - name: Attempt to create a file in a protected location
      block:
        - name: Try to write to /root (will fail)
          ansible.builtin.copy:
            content: "secret\n"
            dest: /root/protected.txt
            mode: "0600"

      rescue:
        - name: Write to a safe location instead
          ansible.builtin.copy:
            content: "This went to /tmp instead\n"
            dest: /tmp/fallback.txt
            mode: "0644"

        - name: Report the fallback
          ansible.builtin.debug:
            msg: "Failed to write to /root, wrote to /tmp/fallback.txt instead"

      always:
        - name: Always run this task
          ansible.builtin.debug:
            msg: "Error handling exercise completed"
```

Run it:

```bash
ansible-playbook playbooks/08_error_handling.yml
```

You should see the rescue block execute because writing to `/root` requires root privileges.

## 4. Lab: Deploy a Web Stack (30 minutes)

### Objective

Write a playbook that deploys a working web server on `server1`.

### Requirements

1. Install nginx
2. Deploy an `index.html` page via template with dynamic content
3. Ensure nginx is running and enabled at boot
4. Use tags to separate install vs. deploy steps

### Step 1: Create the template

Create `playbooks/templates/lab_index.html.j2`:

```jinja title="playbooks/templates/lab_index.html.j2"
<!DOCTYPE html>
<html>
<head>
    <title>{{ page_title | default('Ansible Workshop') }}</title>
</head>
<body>
    <h1>Hello from {{ ansible_hostname }}</h1>
    <p>This page was deployed by Ansible</p>
    <p>OS: {{ ansible_distribution }} {{ ansible_distribution_version }}</p>
    <p>IP Address: {{ ansible_default_ipv4.address | default('N/A') }}</p>
    <hr>
    <p><em>Managed with ❤️ by Ansible</em></p>
</body>
</html>
```

### Step 2: Create the playbook

Create `playbooks/lab_web_stack.yml`:

```yaml title="playbooks/lab_web_stack.yml"
- name: Deploy a web server
  hosts: servers
  gather_facts: true

  vars:
    page_title: "Ansible Workshop - {{ ansible_hostname }}"
    document_root: /var/www/html

  tasks:
    # --- Install phase ---
    - name: Install nginx
      ansible.builtin.package:
        name: nginx
        state: present
      tags: [install]

    # --- Deploy phase ---
    - name: Create document root
      ansible.builtin.file:
        path: "{{ document_root }}"
        state: directory
        mode: "0755"
      tags: [deploy]

    - name: Deploy index page
      ansible.builtin.template:
        src: lab_index.html.j2
        dest: "{{ document_root }}/index.html"
        mode: "0644"
      notify: Restart nginx
      tags: [deploy]

    - name: Ensure nginx is running
      ansible.builtin.service:
        name: nginx
        state: started
        enabled: true
      tags: [deploy, service]

  handlers:
    - name: Restart nginx
      ansible.builtin.service:
        name: nginx
        state: restarted
```

### Step 3: Run the playbook

```bash
# Full deployment
ansible-playbook playbooks/lab_web_stack.yml

# Just install (skip deploy)
ansible-playbook playbooks/lab_web_stack.yml --tags install

# Just deploy (skip install)
ansible-playbook playbooks/lab_web_stack.yml --tags deploy

# Preview changes without applying
ansible-playbook playbooks/lab_web_stack.yml --check --diff
```

### Step 4: Verify

Check that nginx is running:

```bash
ansible servers -m ansible.builtin.command -a "systemctl status nginx"
```

Check the deployed page:

```bash
ansible server1 -m ansible.builtin.command -a "cat /var/www/html/index.html"
```

If you have port forwarding set up, open `http://localhost:80` in your browser.

### Step 5: Idempotency check

Run the playbook again — everything should show `ok=... changed=0`:

```bash
ansible-playbook playbooks/lab_web_stack.yml
```

## 5. Beyond the Basics (15 minutes)

### Ansible Vault

Encrypt sensitive data (passwords, API keys):

```bash
# Create encrypted file
ansible-vault create vars/secrets.yml

# Edit encrypted file
ansible-vault edit vars/secrets.yml

# Run playbook with vault password
ansible-playbook playbooks/my_playbook.yml --ask-vault-pass

# Or provide the password file
ansible-playbook playbooks/my_playbook.yml --vault-password-file .vault_pass
```

### Ansible Galaxy

Install shared roles and collections:

```bash
# Install a collection
ansible-galaxy collection install community.general

# Install a role
ansible-galaxy role install geerlingguy.nginx

# Search for roles
ansible-galaxy search nginx
```

### Ansible Lint

Check your playbooks for best practices:

```bash
pip install ansible-lint
ansible-lint playbooks/lab_web_stack.yml
```

### CI/CD Integration

Run Ansible in GitHub Actions:

```yaml title=".github/workflows/ansible.yml"
name: Ansible Lint
on: [push]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install ansible-lint
        run: pip install ansible-lint
      - name: Lint playbooks
        run: ansible-lint playbooks/
```

## 6. Check your understanding

1. When do handlers run? Can they run multiple times in one play?
2. How do you skip a specific tag when running a playbook?
3. What is the difference between `rescue` and `always` blocks?

??? tip "Answers"
    1. Handlers run once at the end of the play, even if notified multiple times. Only tasks that report `changed` trigger handlers.
    2. Use `--skip-tags tagname`.
    3. `rescue` runs only when the `block` fails; `always` runs regardless of success or failure.

## Wrap-up

You've covered:
- **Module 1:** Playbook basics, inventory, ad-hoc commands
- **Module 2:** Variables, facts, loops, conditionals
- **Module 3:** Templates, Jinja2 filters, roles
- **Module 4:** Handlers, tags, error handling, and the web stack lab

You now have the foundation to automate real infrastructure. Next steps:
- Explore [Ansible Galaxy](https://galaxy.ansible.com) for shared roles
- Learn about [Ansible Vault](https://docs.ansible.com/ansible/latest/user_guide/vault.html) for secrets
- Try [Ansible Lint](https://ansible-lint.readthedocs.io/) for code quality
- Look into [Ansible Automation Platform](https://www.ansible.com/products/automation-platform) for enterprise features
