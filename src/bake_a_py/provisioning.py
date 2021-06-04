import prompt_toolkit as pt
import ruamel.yaml
import pathlib
import subprocess
import sys
import tempfile
import hashlib
import crypt

def hash_passwd(passwd):
    """Hash the user password.

    Raspberry Pi OS currently supports no better methon than sha256.
    """
    return crypt.crypt(passwd, salt=crypt.mksalt(crypt.METHOD_SHA256))

def hash_wifipasswd(passwd, ssid):
    dk = hashlib.pbkdf2_hmac('sha1', bytes(passwd, 'utf-8'),
        bytes(ssid, 'utf-8'), 4096, 32)
    return dk.hex()

def create(hidden_passwords=True):
    d = {}

    d['hostname'] = pt.prompt(pt.HTML(f'<b>hostname</b> '))

    with tempfile.TemporaryDirectory() as tmpdir:
        ssh_path = pathlib.Path(tmpdir).joinpath('etc', 'ssh')
        ssh_path.mkdir(parents=True)

        subprocess.run(['ssh-keygen', '-A', '-f', tmpdir], capture_output=True)
        for key in ['rsa', 'dsa', 'ecdsa', 'ed25519']:
            path = pathlib.Path(ssh_path).joinpath(f'ssh_host_{key}_key')
            subprocess.run(['ssh-keygen', '-c', '-C', 
                f'root@{d["hostname"]}', '-f', path], capture_output=True)
            with open(path, 'r') as fin:
                d[f'ssh_host_{key}'] = fin.read().strip()
            with open(path.with_suffix('.pub'), 'r') as fin:
                d[f'ssh_host_{key}_pub'] = fin.read().strip()

    user_passwd = pt.prompt(pt.HTML(f'<b>user password</b> '), 
        is_password=hidden_passwords)
    d['user_passwd'] = hash_passwd(user_passwd)

    ssh_dir = pathlib.Path('~/.ssh').expanduser()
    pub_keys = [str(p) for p in sorted(ssh_dir.glob('*.pub'))]
    pub_key = pt.prompt(pt.HTML(f'<b>user public key</b> '),
                                completer=pt.completion.WordCompleter(pub_keys))
    with open(pub_key, 'r') as fin:
        d['user_pubkey'] = fin.read().strip()

    with open(pathlib.Path(__file__).parent.joinpath('countries.txt')) as fin:
        countries = [s.strip() for s in fin.readlines()]
    d['wifi_country'] = pt.prompt(pt.HTML('<b>wifi country</b> '),
                                completer=pt.completion.WordCompleter(countries))

    d['wifi_ssid'] = pt.prompt(pt.HTML('<b>wifi ssid</b> '))

    wifi_passwd = pt.prompt(pt.HTML('<b>wifi password</b> '),
        is_password=hidden_passwords)
    d['wifi_passwd'] = hash_wifipasswd(wifi_passwd, d['wifi_ssid'])

    with open(pathlib.Path(__file__).parent.joinpath('timezones.txt')) as fin:
        timezones = [s.strip() for s in fin.readlines()]
    d['timezone'] = pt.prompt(pt.HTML('<b>timezone</b> '),
                            completer=pt.completion.WordCompleter(timezones))

    d['kbd_layout'] = pt.prompt(pt.HTML('<b>keyboard layout</b> '))

    yaml = ruamel.yaml.YAML()
    conf_fname = pathlib.Path(d['hostname']).with_suffix('.yml')
    yaml.dump(d, conf_fname)