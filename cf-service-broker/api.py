from flask import Flask, abort as flask_abort
from utils import check_api_version, basic_auth, json_data_in, json_response
from broker import Broker
from exceptions import *
import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()

app = Flask(__name__)

api_version = check_api_version(2.7)
broker_auth = basic_auth('u', 'p')
broker = Broker()


@app.route('/v2/catalog', methods=('GET',))
@api_version
@broker_auth
def get_catalog():
    return json_response(broker.service_catalog(), 200)


@app.route('/v2/service_instances/<instance_id>/last_operation', methods=('GET',))
@api_version
@broker_auth
def get_last_operation(instance_id):
    return json_response({"state": broker.get_provisioning_state(instance_id)}, 202)


@app.route('/v2/service_instances/<instance_id>', methods=('PUT',))
@api_version
@broker_auth
@json_data_in
def put_create_instance(data, instance_id):
    try:
        broker.create_instance(instance_id=instance_id, **data)
    except ProvisioningAsynchronously:
        return json_response({}, 202)
    except CannotProvisionSynchronouslyError as e:
        return json_response(e.msg, 422)
    except ServiceConflictError:
        return json_response({}, 409)
    else:
        return json_response({}, 201)


@app.route('/v2/service_instances/<instance_id>', methods=('PATCH',))
@api_version
@broker_auth
def patch_modify_instance(instance_id):
    flask_abort(501)


@app.route('/v2/service_instances/<instance_id>/service_bindings/<binding_id>', methods=('PUT',))
@api_version
@broker_auth
@json_data_in
def put_bind(data, instance_id, binding_id):
    try:
        creds = broker.bind_instance(instance_id=instance_id, binding_id=binding_id, **data)
    except BindingNotSupportedError as e:
        return json_response(e.msg, 400)
    except BindingExistsError as e:
        return json_response(e.msg, 409)
    except AppGUIDRequiredError as e:
        return json_response(e.msg, 422)
    else:
        return json_response({"credentials": creds}, 201)


@app.route('/v2/service_instances/<instance_id>/service_bindings/<binding_id>', methods=('DELETE',))
@api_version
@broker_auth
def put_unbind(instance_id, binding_id):
    flask_abort(501)


if __name__ == '__main__':
    app.run(debug=1)
