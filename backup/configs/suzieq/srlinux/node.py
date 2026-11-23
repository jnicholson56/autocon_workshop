

class SrlinuxNode(Node):
    '''Nokia SR Linux node. Appended to suzieq/poller/worker/nodes/node.py by patch_suzieq.py.

    The router is polled over SSH. SR Linux's CLI runs the command given to ssh, so
    "info from state <path> | as json" returns the same data as gNMI.
    '''

    async def _rest_connect(self):
        raise NotImplementedError(
            f'{self.address}: REST transport is not supported')

    async def _rest_gather(self, service_callback, cmd_list, cb_token,
                           oformat="json", timeout=None, reconnect=True):
        raise NotImplementedError(
            f'{self.address}: REST transport is not supported')

    async def _fetch_init_dev_data_devtype(self, reconnect: bool):
        """Read the hostname, version and boot time"""
        await self._exec_cmd(self._parse_init_dev_data, ["show version"],
                             None, 'text', reconnect=reconnect)

    async def _parse_init_dev_data_devtype(self, output, cb_token) -> None:
        data = output[0]["data"]
        match = re.search(r'^Hostname\s*:\s*(\S+)', data, re.MULTILINE)
        if match:
            self.hostname = match.group(1)
        match = re.search(r'^Last Booted\s*:\s*(\S+)', data, re.MULTILINE)
        if match:
            booted = datetime.fromisoformat(match.group(1).replace('Z', '+00:00'))
            self.bootupTimestamp = int(booted.timestamp())
        self._extract_nos_version(data)

    def _extract_nos_version(self, data: str) -> None:
        match = re.search(r'Software Version\s*:\s*v?(\S+)', data)
        if match:
            self.version = match.group(1).strip()
        else:
            self.logger.warning(
                f'Cannot parse version from {self.address}:{self.port}')
            self.version = "all"
