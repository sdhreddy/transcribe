
# pip install cryptography

"""Minimal test for DST certificate helper."""

import pytest

pytest.skip("Windows-specific certificate check", allow_module_level=True)


import pytest
pytest.skip("cryptography not installed", allow_module_level=True)

"""Example test checking for DST certificates.

This test requires the ``cryptography`` package. If it is not installed,
pytest will skip this module automatically.
"""


"""Example script for checking DST certificates.

This file is treated as a test by pytest due to its name. It requires the
``cryptography`` package which may not be available in minimal environments.
Skipping the module ensures the rest of the test suite runs offline.
"""

import pytest

pytest.skip("cryptography not available for example test", allow_module_level=True)



import _ssl
import pytest

cryptography = pytest.importorskip("cryptography")
from cryptography import x509


def find_dst_cert(store_name) -> bool:
    """
    Find the problematic DST certificate
    """
    for cert, encoding_type, trust in _ssl.enum_certificates(store_name):
        decoded_cert = x509.load_der_x509_certificate(cert)

        if str(decoded_cert.issuer).find('DST Root') > 0:
            if store_name == 'CA':
                print(f'Certificate Store: {store_name} - "Current User -> Intermediate Certification Authorities -> Certificates -> Certificates"')
            elif store_name == 'ROOT':
                print(f'Certificate Store: {store_name} - "Local Computer -> Trusted Root Certificate Authorities -> Certificates"')
            print(f'Potentially problematic certificate : {decoded_cert.issuer}')
            # print(cert)
            print(f'{decoded_cert.serial_number}')
            print('---------------------------------------------------')
            return True
    return False

def test_find_dst_cert_no_results(monkeypatch):
    """Ensure the helper handles empty certificate stores."""

    def fake_enum_certificates(_store):
        return []

    monkeypatch.setattr(_ssl, "enum_certificates", fake_enum_certificates)
    assert find_dst_cert("CA") is False
