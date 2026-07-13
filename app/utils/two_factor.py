import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from io import BytesIO
from urllib.parse import quote

from werkzeug.security import check_password_hash, generate_password_hash


def generate_totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode('ascii').rstrip('=')


def _secret_bytes(secret):
    padding = '=' * ((8 - len(secret) % 8) % 8)
    return base64.b32decode((secret + padding).upper())


def totp_code(secret, for_time=None, interval=30):
    counter = int((for_time or time.time()) // interval)
    msg = struct.pack('>Q', counter)
    digest = hmac.new(_secret_bytes(secret), msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f'{code % 1000000:06d}'


def verify_totp(secret, code, window=1):
    clean_code = ''.join(ch for ch in str(code or '') if ch.isdigit())
    if len(clean_code) != 6 or not secret:
        return False
    now = time.time()
    return any(
        hmac.compare_digest(totp_code(secret, now + (offset * 30)), clean_code)
        for offset in range(-window, window + 1)
    )


def provisioning_uri(user, secret, issuer='IT HelpDesk'):
    label = quote(f'{issuer}:{user.email}')
    issuer_q = quote(issuer)
    return f'otpauth://totp/{label}?secret={secret}&issuer={issuer_q}&digits=6&period=30'


def qr_code_data_uri(uri):
    try:
        import qrcode
    except ImportError:
        return None

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(uri)
    qr.make(fit=True)

    image = qr.make_image(fill_color='black', back_color='white')
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def generate_backup_codes(count=8):
    return ['-'.join([secrets.token_hex(2), secrets.token_hex(2)]).upper() for _ in range(count)]


def hash_backup_codes(codes):
    return json.dumps([generate_password_hash(code) for code in codes])


def verify_backup_code(user, code):
    clean_code = str(code or '').strip().upper().replace(' ', '')
    if not clean_code or not user.two_factor_backup_codes:
        return False
    try:
        hashes = json.loads(user.two_factor_backup_codes)
    except (TypeError, ValueError):
        return False
    for index, code_hash in enumerate(hashes):
        if check_password_hash(code_hash, clean_code):
            hashes.pop(index)
            user.two_factor_backup_codes = json.dumps(hashes)
            return True
    return False


def backup_code_count(user):
    if not user.two_factor_backup_codes:
        return 0
    try:
        return len(json.loads(user.two_factor_backup_codes))
    except (TypeError, ValueError):
        return 0
