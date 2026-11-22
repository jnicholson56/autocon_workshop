#!/bin/sh
#
# This script contains the 'ip' commands needed to set up container
# interfaces and route table. It's executed within the container
# network namespace on the container host.
#
#  /etc/hosts file is generated as a clab bind.
#
set -e

### One-Shot configuration (non-Ubuntu VM or container)
#
# Send ARP requests from a sane source IP address
sysctl -w net.ipv4.conf.all.arp_announce=2

#
# Enable or disable IPv4 and IPv6 forwarding
#
sysctl -w net.ipv4.ip_forward=0
sysctl -w net.ipv6.conf.all.forwarding=0
sysctl -w net.ipv4.fib_multipath_hash_policy=1
#
# Disable RA-derived IPv6 default route on management interface. We need it for intra-lab connectivity
#
if ip -6 addr show dev eth0 | grep inet6; then
  echo "Disabling IPv6 RA listener on management interface"
  sysctl -w net/ipv6/conf/eth0/accept_ra=0
  sysctl -w net/ipv6/conf/eth0/accept_ra_defrtr=0 || echo "Cannot disable RA-based default route"
  ip -6 route flush default
fi
#
# Interface addressing, create any bond devices
#
ip link set dev eth1 up
set +e
ip addr del 172.16.1.5/24 dev eth1 2>/dev/null
set -e
ip addr add 172.16.1.5/24 dev eth1
sysctl -w net.ipv6.conf.eth1.disable_ipv6=1
ip link set dev eth1 mtu 1500


#!/bin/sh
#
# Add static routes (usually IPv4 routes pointing to the first usable gateway)
#
#
echo Removing existing IPv4 routes
while ip route del 172.16.0.0/16 2>/dev/null; do
  : ; done
while ip route del 10.0.0.0/24 2>/dev/null; do
  : ; done
while ip route del 10.1.0.0/16 2>/dev/null; do
  : ; done
while ip route del 10.2.0.0/24 2>/dev/null; do
  : ; done
#
#
#
echo Adding direct static routes
ip route add 172.16.0.0/16 via 172.16.1.3 dev eth1 protocol static
ip route add 10.0.0.0/24 via 172.16.1.3 dev eth1 protocol static
ip route add 10.1.0.0/16 via 172.16.1.3 dev eth1 protocol static
ip route add 10.2.0.0/24 via 172.16.1.3 dev eth1 protocol static
