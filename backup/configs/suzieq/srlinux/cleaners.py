"""Turn the raw SR Linux data into SuzieQ records.

Installed as suzieq/poller/worker/services/srlinux_cleaners.py by patch_suzieq.py. Each function
is attached to its service class as _clean_srlinux_data, which SuzieQ calls for devtype srlinux.

Only the default network instance is polled.
"""
import re
from datetime import datetime

_TIMESTAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T[\d:.]+Z')
_SPEED = re.compile(r'^(\d+(?:\.\d+)?)([MGT])$')


def _epoch(value, ms=False):
    """Seconds (or ms) since the epoch for '2026-11-22T00:19:40.600Z (3 hours ago)'"""
    match = _TIMESTAMP.match(value or '')
    if not match:
        return 0
    stamp = datetime.fromisoformat(match.group(0).replace('Z', '+00:00')).timestamp()
    return int(stamp * 1000) if ms else int(stamp)


def _speed_mbps(value):
    match = _SPEED.match(value or '')
    if not match:
        return -1
    return int(float(match.group(1)) * {'M': 1, 'G': 1000, 'T': 1000000}[match.group(2)])


def clean_device(self, processed_data, raw_data):
    for entry in processed_data:
        entry['bootupTimestamp'] = _epoch(entry.get('bootupTimestamp'))
        entry['version'] = entry.get('version', '').split('-')[0].lstrip('v')
        arch = re.search(r'Kernel \S+\.(\w+) #', entry.pop('_description', ''))
        entry['architecture'] = arch.group(1) if arch else ''
        entry['vendor'] = 'Nokia'
        entry['os'] = 'srlinux'
    return self._common_data_cleaner(processed_data, raw_data)


def _interface_type(name):
    if name.startswith(('lo', 'system')):
        return 'loopback'
    return 'ethernet'


def _addresses(subif, family):
    return [a['ip-prefix'] for a in subif.get(family, {}).get('address', [])]


def clean_interfaces(self, processed_data, _):
    records = []
    for entry in processed_data:
        subifs = entry.pop('_subifs', None) or []
        admin = entry.pop('_admin', '')
        oper = entry.pop('_oper', '')
        speed = entry.pop('_speed', '')
        changed = _epoch(entry.pop('_lastChange', ''), ms=True)

        # SR Linux lists every port of the chassis. Skip the ones nobody configured.
        if admin != 'enable' and not subifs:
            continue

        entry.update({
            'type': _interface_type(entry['ifname']),
            'adminState': 'up' if admin == 'enable' else 'down',
            'state': 'up' if oper == 'up' else 'down',
            'speed': _speed_mbps(speed),
            'statusChangeTimestamp': changed,
            'portmode': 'routed' if subifs else '',
        })
        records.append(entry)

        # Each subinterface carries the IP addresses, so BGP can find the peer behind an address
        for subif in subifs:
            records.append({
                'ifname': subif.get('name', ''),
                'ifindex': subif.get('ifindex', 0),
                'type': 'subinterface',
                'description': subif.get('description', ''),
                'adminState': 'up' if subif.get('admin-state') == 'enable' else 'down',
                'state': 'up' if subif.get('oper-state') == 'up' else 'down',
                'mtu': subif.get('ip-mtu', 0),
                'speed': -1,
                'macaddr': entry.get('macaddr', ''),
                'ipAddressList': _addresses(subif, 'ipv4'),
                'ip6AddressList': _addresses(subif, 'ipv6'),
                'statusChangeTimestamp': _epoch(subif.get('last-change', ''), ms=True),
                'portmode': 'routed',
            })
    return records


# BGP address families as SuzieQ names them
_AFI_SAFI = {
    'ipv4-unicast': ('ipv4', 'unicast'),
    'ipv6-unicast': ('ipv6', 'unicast'),
    'evpn': ('l2vpn', 'evpn'),
}


def clean_bgp(self, processed_data, _):
    records = []
    for entry in processed_data:
        afisafis = entry.pop('_afisafi', None) or []
        established = entry.pop('_session', '') == 'established'
        last_event = entry.pop('_lastEvent', '')
        estd_ms = _epoch(entry.pop('_established', ''), ms=True)
        reflector = entry.pop('_rr', '')

        entry.update({
            'vrf': 'default',
            'state': 'Established' if established else 'NotEstd',
            'bfdStatus': 'disabled',
            'rrclient': str(bool(reflector)),
            'reason': '' if established else last_event,
        })

        if not established:
            entry.update({'afi': '', 'safi': ''})
            records.append(entry)
            continue

        entry['estdTime'] = estd_ms
        for family in afisafis:
            names = _AFI_SAFI.get(family.get('afi-safi-name'))
            if not names or family.get('oper-state') != 'up':
                continue
            record = dict(entry)
            record.update({
                'afi': names[0],
                'safi': names[1],
                'pfxRx': int(family.get('received-routes') or 0),
                'pfxTx': int(family.get('sent-routes') or 0),
            })
            records.append(record)
    return records


# SR Linux route types as SuzieQ names the protocol
_PROTOCOL = {'host': 'connected', 'local': 'connected'}


def clean_routes(self, processed_data, _):
    groups = {e['_index']: e.get('_nhs') or []
              for e in processed_data if e.get('_entryType') == 'nhg'}
    next_hops = {e['_index']: e
                 for e in processed_data if e.get('_entryType') == 'nh'}

    records = []
    for entry in processed_data:
        # The parser turns a false 'active' into an empty string
        if entry.get('_entryType') != 'route' or not entry.get('_active'):
            continue

        hops = [next_hops[i] for i in groups.get(entry.get('_nhg'), []) if i in next_hops]
        prefix = entry['prefix']
        route_type = entry.get('_type', '')
        blackhole = any(h.get('_nhtype') == 'blackhole' for h in hops)
        records.append({
            'prefix': prefix,
            'prefixlen': int(prefix.split('/')[1]),
            'vrf': 'default',
            'ipvers': 6 if ':' in prefix else 4,
            'protocol': _PROTOCOL.get(route_type, route_type),
            'preference': entry.get('preference', 0),
            'metric': entry.get('metric', 0),
            'nexthopIps': [h['_ip'] for h in hops if h.get('_ip')],
            'oifs': [h['_oif'] for h in hops if h.get('_oif')],
            'numNexthops': len(hops),
            'action': 'blackhole' if blackhole else 'forward',
            'statusChangeTimestamp': _epoch(entry.get('_updated', ''), ms=True),
        })
    return records
