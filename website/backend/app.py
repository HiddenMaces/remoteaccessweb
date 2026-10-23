from flask import Flask, jsonify, request
import json, os, tempfile, threading, uuid

app = Flask(__name__)
DATA_FILE = os.getenv('DATA_FILE', '/data/links.json')

LOCK = threading.Lock()

LINK_FIELDS = ('label', 'url', 'description', 'category')
SETTING_FIELDS = ('title', 'email')
CATEGORIES = ('remote', 'local')

DEFAULT_DATA = {
    "settings": {"title": "Operational Gateway", "email": ""},
    "links": []
}


def load():
    if not os.path.exists(DATA_FILE):
        return {k: list(v) if isinstance(v, list) else dict(v) for k, v in DEFAULT_DATA.items()}
    with open(DATA_FILE) as f:
        return json.load(f)


def save(data):
    directory = os.path.dirname(DATA_FILE)
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, DATA_FILE)
    except BaseException:
        os.unlink(tmp)
        raise


class ValidationError(ValueError):
    pass


def body_dict():
    body = request.get_json(force=True, silent=True)
    if not isinstance(body, dict):
        raise ValidationError('body must be a JSON object')
    return body


def clean(body, fields, require=()):
    out = {}
    for k in fields:
        if k in body:
            v = body[k]
            if not isinstance(v, str):
                raise ValidationError(f'{k} must be a string')
            out[k] = v.strip()
    for k in require:
        if not out.get(k):
            raise ValidationError(f'{k} is required')
    return out


def clean_link(body, partial=False):
    link = clean(body, LINK_FIELDS, require=() if partial else ('label', 'url'))
    if 'label' in link and not link['label']:
        raise ValidationError('label is required')
    if 'url' in link:
        url = link['url']
        # Allow http(s) and site-relative paths only; blocks javascript:, data:, //host
        if not (url.lower().startswith(('http://', 'https://'))
                or (url.startswith('/') and not url.startswith('//'))):
            raise ValidationError('url must start with http://, https:// or /')
    if 'category' in link:
        if link['category'] not in CATEGORIES:
            raise ValidationError(f'category must be one of {CATEGORIES}')
    elif not partial:
        link['category'] = 'remote'
    if 'newTab' in body:
        if not isinstance(body['newTab'], bool):
            raise ValidationError('newTab must be a boolean')
        link['newTab'] = body['newTab']
    elif not partial:
        link['newTab'] = True
    return link


@app.errorhandler(ValidationError)
def on_validation_error(e):
    return jsonify({'error': str(e)}), 400


@app.route('/api/links', methods=['GET'])
def get_all():
    return jsonify(load())


@app.route('/api/links', methods=['POST'])
def create():
    link = clean_link(body_dict())
    link['id'] = str(uuid.uuid4())
    with LOCK:
        data = load()
        data['links'].append(link)
        save(data)
    return jsonify(link), 201


@app.route('/api/links/reorder', methods=['POST'])
def reorder():
    ids = body_dict().get('ids', [])
    if not isinstance(ids, list):
        raise ValidationError('ids must be a list')
    with LOCK:
        data = load()
        by_id = {l['id']: l for l in data['links']}
        ordered = [by_id[i] for i in ids if isinstance(i, str) and i in by_id]
        # keep any links the client didn't know about rather than dropping them
        seen = {l['id'] for l in ordered}
        data['links'] = ordered + [l for l in data['links'] if l['id'] not in seen]
        save(data)
    return jsonify({'ok': True})


@app.route('/api/links/<lid>', methods=['PUT'])
def update(lid):
    changes = clean_link(body_dict(), partial=True)
    with LOCK:
        data = load()
        for i, link in enumerate(data['links']):
            if link['id'] == lid:
                data['links'][i] = {**link, **changes, 'id': lid}
                save(data)
                return jsonify(data['links'][i])
    return jsonify({'error': 'not found'}), 404


@app.route('/api/links/<lid>', methods=['DELETE'])
def delete(lid):
    with LOCK:
        data = load()
        data['links'] = [l for l in data['links'] if l['id'] != lid]
        save(data)
    return '', 204


@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(load().get('settings', {}))


@app.route('/api/settings', methods=['PUT'])
def update_settings():
    changes = clean(body_dict(), SETTING_FIELDS)
    with LOCK:
        data = load()
        data['settings'] = {**data.get('settings', {}), **changes}
        save(data)
    return jsonify(data['settings'])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
