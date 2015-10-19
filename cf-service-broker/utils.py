from functools import wraps
from flask import request, make_response, jsonify


def json_response(o, code):
    return make_response((jsonify(o), code, {"Content-Type": "application/json"}))


def check_api_version(api_version):
    def check_specific_api_version(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_api_version = request.headers.get('X-Broker-Api-Version')
            if not client_api_version or float(client_api_version) < api_version:
                return make_response(("This broker implements version %s of the broker API, your client supports %s" %
                                     (api_version, client_api_version),
                                     409, {'Content-Type': 'text/plain'}))
            return f(*args, **kwargs)
        return decorated_function
    return check_specific_api_version


def basic_auth(username, password):
    def specific_basic_auth(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth = request.authorization
            if not auth or not (auth.username == username and auth.password == password):
                return make_response(("Not authorized", 401, {'Content-Type': 'text/plain'}))
            return f(*args, **kwargs)
        return decorated_function
    return specific_basic_auth


def json_data_in(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.content_type != 'application/json':
            return make_response(("Unsupported content type %s in request, application/json expected" % request.content_type,
                                  409, {"Content-Type": "text/plain"}))
        data = request.get_json(force=True)
        if data is None:
            raise Exception('No data in request body')
        return f(data, *args, **kwargs)
    return decorated_function