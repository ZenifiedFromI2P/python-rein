import toml
global conf

# Warning, slowly implementing the whole thing

def initconf():
    fp = open('config.toml', 'r')
    conf = toml.loads(fp.read())
    fp.close()

def updateconfig():
    fp = open('config.toml', 'w')
    fp.write(toml.dumps(conf))
    fp.close()

initconf()


class PersistConfig(object):
    def __init__(self, key, value):
        self.key = key
        conf[key] = self.value = value
        updateconfig()

    def set(self, value=''):
        self.key = value
        updateconfig()

    @classmethod
    def set_testnet(self, value):
        conf['testnet'] = value

    @classmethod
    def get_testnet(self, rein):
        return conf.get('testnet', False)
    @classmethod
    def set_tor(self, value):
        return conf.get('tor', False)

    @classmethod
    def get_tor(self, value):
        conf['tor'] = value

    @classmethod
    def set_debug(self, rein, value):
        return conf.get('debug', True)

    @classmethod
    def get_debug(self, rein):
        conf['debug'] = True
