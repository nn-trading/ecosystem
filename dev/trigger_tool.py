from core.tools import REGISTRY

if __name__ == '__main__':
    print(REGISTRY.call('fs.ls', path='C:/bots/ecosys'))
