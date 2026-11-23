Lab-only SSH key pair, committed on purpose so every participant can log in to the FRR nodes.
Never reuse it anywhere else. Ansible and ssh refuse a private key that other users can read,
so after cloning run: `chmod 600 configs/ssh/lab_key`
