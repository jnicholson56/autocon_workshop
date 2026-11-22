# Module 1: Foundations & Inventory

Ansible fundamentals and a multi-NOS inventory.

## Deploy the lab

```bash
sudo containerlab deploy -t workshop.clab.yml
```

## Inspect the inventory

```bash
ansible-inventory -i inventory.yml --graph
ansible all -i inventory.yml -m ping
```

??? tip "Ping fails?"
    Confirm the lab is running with `sudo containerlab inspect -t workshop.clab.yml`.
