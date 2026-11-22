#!/bin/sh
# Interface counters only; CPU/memory would be the container host's, not the router's.
node_exporter --web.listen-address=:9100 --collector.disable-defaults --collector.netdev --collector.netclass \
  --collector.netdev.device-exclude='^(lo|eth0)$' --collector.netclass.ignored-devices='^(lo|eth0)$' >/var/log/node_exporter.log 2>&1 &
frr_exporter --web.listen-address=:9342 >/var/log/frr_exporter.log 2>&1 &
ssh-keygen -A >/dev/null 2>&1
/usr/sbin/sshd
exec /usr/lib/frr/docker-start
