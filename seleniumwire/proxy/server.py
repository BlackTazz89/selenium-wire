import os
import socket
from collections import namedtuple
from urllib.request import _parse_proxy

from .modifier import RequestModifier
from .proxy2 import ThreadingHTTPServer
from .storage import RequestStorage


class ProxyHTTPServer(ThreadingHTTPServer):
    address_family = socket.AF_INET

    def __init__(self, *args, proxy_config=None, options=None, **kwargs):
        # Each server instance gets its own storage
        self.storage = RequestStorage()

        # Each server instance gets a request modifier
        self.modifier = RequestModifier()

        # The server's upstream proxy configuration (if any)
        self.proxy_config = self._sanitise_proxy_config(
            self._merge_with_env(proxy_config or {}))

        # Additional proxy server configuration
        self.options = options or {}

        # A scope for proxy to be interested
        self.scopes = []

        super().__init__(*args, **kwargs)

    def _merge_with_env(self, proxy_config):
        """Merge upstream proxy configuration with configuration loaded
        from the environment.
        """
        http_proxy = os.environ.get('HTTP_PROXY')
        https_proxy = os.environ.get('HTTPS_PROXY')
        no_proxy = os.environ.get('NO_PROXY')

        merged = {}

        if http_proxy:
            merged['http'] = http_proxy
        if https_proxy:
            merged['https'] = https_proxy
        if no_proxy:
            merged['no_proxy'] = no_proxy

        merged.update(proxy_config)

        return merged

    def _sanitise_proxy_config(self, proxy_config):
        """Parse the proxy configuration into something more usable."""
        conf = namedtuple('ProxyConf', 'scheme username password hostport')

        for proxy_type in ('http', 'https'):
            # Parse the upstream proxy URL into (scheme, username, password, hostport)
            # for ease of access.
            if proxy_config.get(proxy_type) is not None:
                proxy_config[proxy_type] = conf(*_parse_proxy(proxy_config[proxy_type]))

        return proxy_config

    def shutdown(self):
        super().shutdown()
        self.storage.cleanup()
