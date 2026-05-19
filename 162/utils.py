import string
import secrets
import io
import csv
from urllib.parse import urlparse
from user_agents import parse
import qrcode


def generate_short_code(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def generate_secure_short_code(length=8, max_attempts=10):
    chars = string.ascii_letters + string.digits
    for attempt in range(max_attempts):
        code = ''.join(secrets.choice(chars) for _ in range(length + attempt))
        if not code.isdigit() and not code.isalpha():
            return code
    return ''.join(secrets.choice(chars) for _ in range(length + 3))


def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def get_client_ip(request):
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    else:
        ip = request.remote_addr
    return ip


def parse_user_agent(user_agent_string):
    try:
        ua = parse(user_agent_string)
        return {
            'browser': f'{ua.browser.family} {ua.browser.version_string}'.strip(),
            'os': f'{ua.os.family} {ua.os.version_string}'.strip(),
            'device': ua.device.family or 'Unknown',
            'is_mobile': ua.is_mobile,
            'is_tablet': ua.is_tablet,
            'is_pc': ua.is_pc
        }
    except Exception:
        return {
            'browser': 'Unknown',
            'os': 'Unknown',
            'device': 'Unknown',
            'is_mobile': False,
            'is_tablet': False,
            'is_pc': False
        }


def generate_qrcode(url, size=10):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io


def generate_csv(short_urls):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Short Code', 'Original URL', 'Short URL', 'Created At', 'Expires At', 'Access Count', 'Has Password'])
    for url in short_urls:
        writer.writerow([
            url.short_code,
            url.original_url,
            '',
            url.created_at.isoformat() if url.created_at else '',
            url.expires_at.isoformat() if url.expires_at else '',
            url.access_count,
            url.has_password
        ])
    output.seek(0)
    return output
