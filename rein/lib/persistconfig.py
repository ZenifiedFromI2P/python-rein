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

    def set(self, rein, key, value=''):
        self.key = value
        updateconfig()

    @classmethod
    def set_testnet(self, rein, value):
        res = rein.session.query(PersistConfig).filter(PersistConfig.key == 'testnet').first()
        if res:
            res.value = value
        else:
            p = PersistConfig(rein.session, 'testnet', value)
            rein.session.add(p)
        rein.session.commit()

    @classmethod
    def get_testnet(self, rein):
        res = rein.session.query(PersistConfig).filter(PersistConfig.key == 'testnet').first()
        if res and res.value == 'true':
            return True
        else:
            return False

    @classmethod
    def set_tor(self, rein, value):
        res = rein.session.query(PersistConfig).filter(PersistConfig.key == 'tor').first()
        if res:
            res.value = value
        else:
            p = PersistConfig(rein.session, 'tor', value)
            rein.session.add(p)
        rein.session.commit()

    @classmethod
    def get_tor(self, rein):
        res = rein.session.query(PersistConfig).filter(PersistConfig.key == 'tor').first()
        if res and res.value == 'true':
            return True
        else:
            return False

    @classmethod
    def set_debug(self, rein, value):
        res = rein.session.query(PersistConfig).filter(PersistConfig.key == 'debug').first()
        if res:
            res.value = value
        else:
            p = PersistConfig(rein.session, 'debug', value)
            rein.session.add(p)
        rein.session.commit()

    @classmethod
    def get_debug(self, rein):
        res = rein.session.query(PersistConfig).filter(PersistConfig.key == 'debug').first()
        if res and res.value == 'true':
            return True
        else:
            return False
