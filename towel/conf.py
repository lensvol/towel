import ConfigParser

TOWEL_CONF_FILE = "towel/towel.settings"

TOWEL_CONF = ConfigParser.ConfigParser()
TOWEL_CONF.readfp(open(TOWEL_CONF_FILE))


def get_mock_server_url():
    server_url = TOWEL_CONF.get('mock_server', 'address')
    server_port = TOWEL_CONF.get('mock_server', 'port')
    return 'http://%(url)s:%(port)s' % {'url': server_url, 'port': server_port}
