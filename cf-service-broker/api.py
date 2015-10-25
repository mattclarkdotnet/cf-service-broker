from flask import Flask, request
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
    try:
        return json_response({"state": broker.get_provisioning_state(instance_id)}, 202)
    except AsyncOperationStateNotHandledError:
        return json_response({"error": "The async operation was not in a state the broker could understand"}, 500)


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


@app.route('/v2/service_instances/<instance_id>', methods=('DELETE',))
@api_version
@broker_auth
def delete_delete_instance(instance_id):
    try:
        service_id = request.args['service_id']
        plan_id = request.args['plan_id']
    except KeyError:
        return json_response({"description": "either service_id or plan_id missing from request query params"}, 400)
    accepts_incomplete = request.args.get('accepts_incomplete', False)
    try:
        broker.delete_instance(instance_id, service_id, plan_id, accepts_incomplete)
    except ProvisioningAsynchronously:
        return json_response({}, 202)
    except CannotProvisionSynchronouslyError as e:
        return json_response(e.msg, 422)
    except NoSuchEntityError:
        return json_response({}, 410)
    else:
        return json_response({}, 200)


@app.route('/v2/service_instances/<instance_id>', methods=('PATCH',))
@api_version
@broker_auth
@json_data_in
def patch_modify_instance(data, instance_id):
    try:
        broker.modify_instance(instance_id=instance_id, **data)
    except NotImplementedError:
        return json_response({}, 501)
    except ProvisioningAsynchronously:
        return json_response({}, 202)
    except CannotProvisionSynchronouslyError as e:
        return json_response(e.msg, 422)
    except UnsupportedPlanChangeError as e:
        return json_response(e.msg, 422)
    except CurrentlyNotPossiblePlanChangeError as e:
        return json_response(e.msg, 422)
    else:
        return json_response({}, 201)


@app.route('/v2/service_instances/<instance_id>/service_bindings/<binding_id>', methods=('PUT',))
@api_version
@broker_auth
@json_data_in
def put_bind(data, instance_id, binding_id):
    try:
        credentials = broker.bind_instance(instance_id=instance_id, binding_id=binding_id, **data)
    except BindingNotSupportedError as e:
        return json_response(e.msg, 400)
    except BindingExistsError as e:
        return json_response(e.msg, 409)
    except AppGUIDRequiredError as e:
        return json_response(e.msg, 422)
    else:
        return json_response({"credentials": credentials}, 201)


@app.route('/v2/service_instances/<instance_id>/service_bindings/<binding_id>', methods=('DELETE',))
@api_version
@broker_auth
def delete_unbind(instance_id, binding_id):
    try:
        service_id = request.args['service_id']
        plan_id = request.args['plan_id']
    except KeyError:
        return json_response({"description": "either service_id or plan_id missing from request query params"}, 400)
    try:
        broker.unbind_instance(instance_id=instance_id, binding_id=binding_id, service_id=service_id, plan_id=plan_id)
    except NoSuchEntityError:
        return json_response({}, 410)
    else:
        return json_response({}, 200)

if __name__ == '__main__':
    app.run(debug=1)
