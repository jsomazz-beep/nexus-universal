"""Build-time certificate checks; never disables TLS verification."""
import argparse
import ssl
import urllib.error
import urllib.request


def patched_certifi(version):
    return tuple(int(part) for part in version.split('.')) >= (2026, 10, 19)


def main(tls=False):
    import certifi
    import requests
    if not patched_certifi(certifi.__version__):
        raise RuntimeError('Unpatched certifi: ' + certifi.__version__)
    print('Security runtime: certifi ' + certifi.__version__ + ' patched', flush=True)
    if not tls:
        return
    requests.get('https://render.com', timeout=15).raise_for_status()
    with urllib.request.urlopen('https://render.com', timeout=15):
        pass
    for host in ('dv-g3b', 'dv-g3b-aaa'):
        url = 'https://' + host + '-emudhra.we-have-a-problem.com/'
        try:
            requests.get(url, timeout=15, allow_redirects=False)
        except requests.exceptions.SSLError:
            print('Security TLS: requests rejected ' + host, flush=True)
        else:
            raise RuntimeError('Requests accepted compromised certificate: ' + host)
        try:
            with urllib.request.urlopen(url, timeout=15):
                pass
        except urllib.error.URLError as error:
            if not isinstance(error.reason, ssl.SSLCertVerificationError):
                raise
            print('Security TLS: system store rejected ' + host, flush=True)
        else:
            raise RuntimeError('System store accepted compromised certificate: ' + host)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tls', action='store_true')
    main(parser.parse_args().tls)
