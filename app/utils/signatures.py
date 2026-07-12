import base64
import os
import re
import uuid
from flask import current_app


DEFAULT_SIGNATURE_HTML = (
    '<div class="helpdesk-signature" data-helpdesk-signature="1">'
    '<p>Thanks &amp; Regards,<br><strong>IT Support Team</strong></p>'
    '<p><strong>Winsoft Technologies</strong><br>'
    '<a href="https://www.winsoftech.com">www.winsoftech.com</a></p>'
    '</div>'
)

DATA_IMAGE_RE = re.compile(
    r'data:image/(?P<kind>png|jpe?g|gif|webp);base64,(?P<data>[A-Za-z0-9+/=\s]+)',
    re.I,
)
EMPTY_BLOCK_RE = re.compile(
    r'<(p|div)([^>]*)>(?:\s|&nbsp;|&#160;|<br\s*/?>)*</\1>',
    re.I,
)
MULTI_BR_RE = re.compile(r'(?:<br\s*/?>\s*){3,}', re.I)


def save_inline_signature_images(html, user_id):
    """Persist pasted data: image sources from signature HTML and return updated HTML."""
    if not html or 'data:image/' not in html:
        return html

    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'signatures', str(user_id))
    os.makedirs(folder, exist_ok=True)

    def replace(match):
        kind = match.group('kind').lower()
        ext = 'jpg' if kind in ('jpg', 'jpeg') else kind
        try:
            payload = base64.b64decode(re.sub(r'\s+', '', match.group('data')), validate=True)
        except Exception:
            return ''
        if not payload or len(payload) > 2 * 1024 * 1024:
            return ''
        stored = f'{uuid.uuid4().hex}.{ext}'
        with open(os.path.join(folder, stored), 'wb') as handle:
            handle.write(payload)
        return f'/static/uploads/signatures/{user_id}/{stored}'

    return DATA_IMAGE_RE.sub(replace, html)


def normalize_signature_html(html):
    """Remove common Outlook spacer blocks without flattening the real signature layout."""
    if not html:
        return ''
    html = html.replace('\r\n', '\n').replace('\r', '\n')
    previous = None
    while previous != html:
        previous = html
        html = EMPTY_BLOCK_RE.sub('', html)
    html = MULTI_BR_RE.sub('<br><br>', html)
    html = re.sub(r'(<br\s*/?>\s*)+(</?(?:table|tbody|tr|td|div|p)\b)', r'\2', html, flags=re.I)
    html = re.sub(r'(</(?:table|tbody|tr|td|div|p)>)\s*(<br\s*/?>\s*)+', r'\1', html, flags=re.I)
    return html.strip()
