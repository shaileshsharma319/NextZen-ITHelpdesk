import re
from html.parser import HTMLParser
from markupsafe import Markup, escape

BRACKET_LINK_RE = re.compile(r'\[([^\]]+)\]<((?:https?://|mailto:|tel:)[^>]+)>')
ANGLE_LINK_RE = re.compile(r'([^<>\n]+)<((?:https?://|mailto:|tel:)[^>]+)>')
PLAIN_URL_RE = re.compile(r'(?<!["=])(https?://[^\s<]+)')
EMAIL_RE = re.compile(r'(?<![\w/@.-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![\w@.-])')
PHONE_RE = re.compile(r'(?<![\w>])(\+?\(?\d[\d\s().-]{7,}\d)(?![\w<])')
HTML_TAG_RE = re.compile(r'<\s*(?:html|body|div|p|br|table|span|img|a|font|b|strong|i|em)\b', re.I)

ICON_LABELS = {
    'logo', 'facebook icon', 'linkedin icon', 'twitter icon', 'youtube icon',
    'instagram icon', 'telephone', 'phone', 'web', 'website', 'location'
}
ICON_CLASSES = {
    'facebook icon': 'fab fa-facebook-f',
    'linkedin icon': 'fab fa-linkedin-in',
    'twitter icon': 'fab fa-x-twitter',
    'youtube icon': 'fab fa-youtube',
    'instagram icon': 'fab fa-instagram',
    'telephone': 'fas fa-phone',
    'phone': 'fas fa-phone',
    'web': 'fas fa-globe',
    'website': 'fas fa-globe',
    'location': 'fas fa-location-dot',
    'logo': 'fas fa-building',
}
ALLOWED_TAGS = {
    'a', 'abbr', 'b', 'blockquote', 'br', 'center', 'code', 'div', 'em', 'font',
    'h1', 'h2', 'h3', 'h4', 'hr', 'i', 'img', 'li', 'ol', 'p', 'pre', 'small',
    'input', 'span', 'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th', 'thead',
    'tr', 'u', 'ul'
}
VOID_TAGS = {'br', 'hr', 'img', 'input'}
ALLOWED_ATTRS = {
    'a': {'href', 'title', 'style'},
    'blockquote': {'style'},
    'div': {'style', 'data-helpdesk-signature'},
    'font': {'color'},
    'h1': {'style'},
    'h2': {'style'},
    'h3': {'style'},
    'img': {'src', 'alt', 'title', 'width', 'height', 'class', 'style'},
    'input': {'type', 'checked'},
    'li': {'style'},
    'ol': {'class', 'style'},
    'p': {'style'},
    'pre': {'style'},
    'span': {'style'},
    'table': {'class', 'style', 'width', 'cellpadding', 'cellspacing', 'border'},
    'td': {'colspan', 'rowspan', 'style', 'width', 'height'},
    'th': {'colspan', 'rowspan', 'style', 'width', 'height'},
    'ul': {'class', 'style'},
}
ALLOWED_CLASSES = {
    'email-message-img', 'email-signature-logo-img', 'email-signature-social-img',
    'rte-checklist', 'rte-table'
}
ALLOWED_STYLE_PROPS = {
    'color', 'background-color', 'font-size', 'text-align', 'font-weight',
    'font-style', 'text-decoration', 'font-family', 'line-height',
    'width', 'height', 'max-width', 'max-height', 'min-width', 'min-height',
    'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
    'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
    'border', 'border-top', 'border-right', 'border-bottom', 'border-left',
    'border-collapse', 'vertical-align', 'display'
}


def _safe_url(value):
    value = (value or '').strip()
    lower = value.lower()
    return lower.startswith(('http://', 'https://', 'mailto:', 'tel:'))


def _safe_img_src(value):
    value = (value or '').strip()
    lower = value.lower()
    if lower.startswith(('http://', 'https://', '/static/uploads/')):
        return True
    return bool(re.match(r'^data:image/(png|jpe?g|gif|webp);base64,[a-z0-9+/=\s]+$', lower))


def _icon_key(label):
    return (label or '').strip().lower().strip('[]')


def _safe_class(value):
    classes = [item for item in (value or '').split() if item in ALLOWED_CLASSES]
    return ' '.join(classes)


def _safe_style(value):
    clean = []
    for item in (value or '').split(';'):
        if ':' not in item:
            continue
        prop, val = item.split(':', 1)
        prop = prop.strip().lower()
        val = val.strip()
        lower_val = val.lower()
        if prop not in ALLOWED_STYLE_PROPS:
            continue
        if any(blocked in lower_val for blocked in ('expression', 'url(', 'javascript:', '<', '>')):
            continue
        clean.append(f'{prop}: {val}')
    return '; '.join(clean)


def _image_class(attrs):
    values = ' '.join((attrs.get('alt', ''), attrs.get('title', ''), attrs.get('src', ''))).lower()
    social = ('facebook', 'linkedin', 'twitter', 'youtube', 'instagram', 'whatsapp')
    if any(name in values for name in social):
        return 'email-signature-social-img'
    if 'logo' in values or 'brand' in values:
        return 'email-signature-logo-img'
    try:
        width = int(re.sub(r'\D', '', attrs.get('width', '') or '0') or 0)
        height = int(re.sub(r'\D', '', attrs.get('height', '') or '0') or 0)
    except ValueError:
        width = height = 0
    if width and height and max(width, height) <= 64:
        return 'email-signature-social-img'
    return 'email-message-img'


def _link(label, href):
    key = _icon_key(label)
    safe_label = escape((label or href).strip())
    safe_href = escape((href or '').strip())
    if key in ICON_CLASSES:
        return (
            f'<a class="email-signature-icon-link" href="{safe_href}" target="_blank" rel="noopener noreferrer" title="{safe_label}">'
            f'<i class="{ICON_CLASSES[key]}"></i><span class="sr-only">{safe_label}</span></a>'
        )
    return f'<a href="{safe_href}" target="_blank" rel="noopener noreferrer">{safe_label}</a>'


class EmailHTMLSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {'script', 'style', 'iframe', 'object', 'embed'}:
            self.skip_depth += 1
            return
        if self.skip_depth or tag not in ALLOWED_TAGS:
            return
        clean_attrs = []
        clean_attr_map = {}
        allowed = ALLOWED_ATTRS.get(tag, set())
        for name, value in attrs:
            name = name.lower()
            if name not in allowed:
                continue
            if tag == 'a' and name == 'href' and not _safe_url(value):
                continue
            if tag == 'img' and name == 'src' and not _safe_img_src(value):
                continue
            if name == 'class':
                value = _safe_class(value)
                if not value:
                    continue
            if name == 'style':
                value = _safe_style(value)
                if not value:
                    continue
            if tag == 'input' and name == 'type' and (value or '').lower() != 'checkbox':
                continue
            clean_attrs.append(f'{name}="{escape(value or "")}"')
            clean_attr_map[name] = value or ''
        if tag == 'img' and not any(attr.startswith('src=') for attr in clean_attrs):
            return
        if tag == 'img':
            classes = [clean_attr_map.get('class', ''), _image_class(clean_attr_map)]
            clean_attr_map['class'] = _safe_class(' '.join(classes))
            clean_attrs = [attr for attr in clean_attrs if not attr.startswith('class=')]
            if clean_attr_map['class']:
                clean_attrs.append(f'class="{clean_attr_map["class"]}"')
        if tag == 'input':
            if not any(attr == 'type="checkbox"' for attr in clean_attrs):
                return
            clean_attrs.append('disabled="disabled"')
        if tag == 'a':
            clean_attrs.extend(['target="_blank"', 'rel="noopener noreferrer"'])
        attrs_text = (' ' + ' '.join(clean_attrs)) if clean_attrs else ''
        self.parts.append(f'<{tag}{attrs_text}>')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {'script', 'style', 'iframe', 'object', 'embed'}:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if not self.skip_depth and tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.parts.append(f'</{tag}>')

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(str(escape(data)))

    def handle_entityref(self, name):
        if not self.skip_depth:
            self.parts.append(f'&{name};')

    def handle_charref(self, name):
        if not self.skip_depth:
            self.parts.append(f'&#{name};')

    def html(self):
        return ''.join(self.parts)


def _sanitize_html(value):
    sanitizer = EmailHTMLSanitizer()
    sanitizer.feed(value or '')
    return Markup('<div class="email-rendered-content email-html-content">' + sanitizer.html() + '</div>')


def _tokenize_links(line):
    tokens = []

    def keep(match):
        tokens.append(_link(match.group(1), match.group(2)))
        return f'@@LINK{len(tokens) - 1}@@'

    line = BRACKET_LINK_RE.sub(keep, line)
    line = ANGLE_LINK_RE.sub(keep, line)
    escaped = str(escape(line))
    for idx, token in enumerate(tokens):
        escaped = escaped.replace(f'@@LINK{idx}@@', token)
    return escaped


def _format_line(line):
    raw_label = line.strip()
    plain = _icon_key(raw_label)
    if plain in ICON_LABELS:
        return f'<span class="email-signature-label" title="{escape(plain.title())}"><i class="{ICON_CLASSES.get(plain, "fas fa-circle")}"></i></span>'

    text = _tokenize_links(line)
    text = PLAIN_URL_RE.sub(lambda m: _link(m.group(1), m.group(1)), text)
    text = EMAIL_RE.sub(lambda m: _link(m.group(1), 'mailto:' + m.group(1)), text)
    text = PHONE_RE.sub(lambda m: _link(m.group(1), 'tel:' + re.sub(r'[^+\d]', '', m.group(1))), text)
    return text


def _format_plain(value):
    value = str(value).replace('\r\n', '\n').replace('\r', '\n')
    value = re.sub(r'\n{4,}', '\n\n\n', value)
    blocks = []
    current = []
    for line in value.split('\n'):
        if line.strip():
            current.append(_format_line(line))
        else:
            if current:
                blocks.append('<p>' + '<br>'.join(current) + '</p>')
                current = []
    if current:
        blocks.append('<p>' + '<br>'.join(current) + '</p>')
    return Markup('<div class="email-rendered-content">' + ''.join(blocks) + '</div>')


def email_content(value):
    if not value:
        return Markup('')
    value = str(value).strip()
    if HTML_TAG_RE.search(value):
        return _sanitize_html(value)
    return _format_plain(value)
