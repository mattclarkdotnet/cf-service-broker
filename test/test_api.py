from unittest import TestCase
import json
import base64
from time import sleep
import api
import broker
import service
from exceptions import *
import os
import shutil
import logging
from uuid import uuid4

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()


class DummyService(service.BaseService):
    @classmethod
    def _path(cls, instance_id, filename):
        return os.path.join(cls._dirname(instance_id), filename)

    @classmethod
    def _dirname(cls, instance_id):
        return os.path.join("/tmp/", instance_id)

    def create_instance(self, instance_id, plan, parameters, organization_guid, space_guid):
        if not plan.provisionable_synchronously:
            # The broker won't be waiting for us to return, so wait a bit in order that we don't complete
            # before any tests about async provisioning have done their thing
            sleep(1)
        os.mkdir(self._dirname(instance_id))
        with open(self._path(instance_id, plan.name), 'w+') as f:
            f.write(json.dumps(plan.as_dict()))

    def delete_instance(self, instance_id):
        shutil.rmtree(self._dirname(instance_id))

    def modify_instance(self, instance_id, plan, parameters, previous_values):
        with open(self._path(instance_id, plan.name), 'w+') as f:
            f.write(json.dumps(plan.as_dict()))

    def bind(self, instance_id, binding_id, plan_id, app_guid, parameters):
        binding_filename = self._path(instance_id, binding_id)
        with open(binding_filename, 'a') as f:
            f.close()
        return {"file": binding_filename}

    def unbind(self, instance_id, binding_id, plan_id):
        binding_filename = self._path(instance_id, binding_id)
        try:
            os.unlink(binding_filename)
        except FileNotFoundError:
            raise NoSuchEntityError


SERVICE1_GUID = '4d29b1b1-63c3-425e-97e4-913be8fdaf19'
PLAN1_GUID = 'e1697e2c-967e-4b4c-8eea-a20d0b2a41d0'
PLAN2_GUID = 'd9edc392-68d6-4622-a760-5be7d76efca3'


class APITestCase(TestCase):
    def setUp(self):
        self.tc = api.app.test_client()
        self.hdrs = {'X-Broker-Api-Version': '2.7',
                     'Content-Type': 'application/json',
                     'Authorization': 'Basic ' + base64.b64encode(b"u:p").decode("ascii")}
        self.org_guid = "org1"
        self.space_guid = "space1"
        self.app_guid = "app1"
        self.binding_id = "binding1"
        self.instance_guid = str(uuid4())
        plan_1 = service.Plan(guid=PLAN1_GUID, name="small plan", description="A small generic service plan")
        plan_2 = service.Plan(guid=PLAN2_GUID, name="large plan", description="A large generic service plan",
                              provisionable_synchronously=False)
        self.service = DummyService(guid=SERVICE1_GUID,
                                    name="generic_service",
                                    description="A service that gives generic service",
                                    bindable=True,
                                    plans={plan_1.guid: plan_1, plan_2.guid: plan_2},
                                    dashboard_client={"id": "client-id-1",
                                                      "secret": "secret-1",
                                                      "redirect_uri": "https://generic.service.somewhere/dashboard"})

        api.broker = broker.Broker(service_list=[self.service,])

    def tearDown(self):
        try:
            self.service.delete_instance(self.instance_guid)
        except OSError:
            pass

    def create_instance(self, async=False):
        req_data = {"organization_guid": self.org_guid,
                    "plan_id": PLAN1_GUID,
                    "service_id": SERVICE1_GUID,
                    "space_guid": self.space_guid}
        if async:
            req_data['accepts_incomplete'] = True
            req_data['plan_id'] = PLAN2_GUID
        return self.tc.put('/v2/service_instances/' + self.instance_guid, headers=self.hdrs, data=json.dumps(req_data))


class TestGetCatalog(APITestCase):
    def test_get_catalog(self):
        resp = self.tc.get('/v2/catalog', headers=self.hdrs)
        catalog = json.loads(resp.data.decode('ascii'))
        self.assertEqual(type(catalog), dict)
        svc_def = catalog['services'][0]
        self.assertEqual(svc_def['id'], SERVICE1_GUID)


class TestAuth(APITestCase):
    def test_auth_denied_noauth(self):
        hdrs = dict(self.hdrs)
        hdrs.pop('Authorization')
        resp = self.tc.get('/v2/catalog', headers=hdrs)
        self.assertEqual(resp.status_code, 401)

    def test_auth_denied_wrongauth(self):
        hdrs = dict(self.hdrs)
        hdrs['Authorization'] = 'Basic ' + base64.b64encode(b"wrong:creds").decode("ascii")
        resp = self.tc.get('/v2/catalog', headers=hdrs)
        self.assertEqual(resp.status_code, 401)


class TestInstance(APITestCase):
    def test_create_instance(self):
        resp = self.create_instance()
        self.assertEqual(resp.status_code, 201)

    def test_create_and_delete_instance(self):
        resp = self.create_instance()
        self.assertEqual(resp.status_code, 201)
        resp = self.tc.delete('/v2/service_instances/' + self.instance_guid + '?service_id=' + SERVICE1_GUID
                              + '&plan_id=' + PLAN1_GUID, headers=self.hdrs)
        self.assertEqual(resp.status_code, 200)

    def test_create_instance_async(self):
        resp = self.create_instance(async=True)
        self.assertEqual(resp.status_code, 202)
        resp = self.tc.get('/v2/service_instances/' + self.instance_guid + '/last_operation', headers=self.hdrs)
        d = json.loads(resp.data.decode(encoding='UTF-8'))
        self.assertEqual(d['state'], 'in progress')
        sleep(2)
        resp = self.tc.get('/v2/service_instances/' + self.instance_guid + '/last_operation', headers=self.hdrs)
        d = json.loads(resp.data.decode(encoding='UTF-8'))
        self.assertEqual(d['state'], 'succeeded')


class TestBinding(APITestCase):
    def bind_instance(self):
        req_data = {"plan_id": PLAN1_GUID,
                    "service_id": SERVICE1_GUID,
                    "app_guid": self.app_guid,
                    "parameters": {'a': 'b'}}
        resp = self.tc.put('/v2/service_instances/' + self.instance_guid + '/service_bindings/' + self.binding_id,
                           headers=self.hdrs, data=json.dumps(req_data))
        return resp

    def test_bind_instance(self):
        resp = self.create_instance()
        resp = self.bind_instance()
        self.assertEqual(resp.status_code, 201)
        d = json.loads(resp.data.decode(encoding='UTF-8'))
        self.assertIn('credentials', d)
        self.assertEqual(d['credentials'], {'file': self.service._path(self.instance_guid, self.binding_id)})

    def test_unbind_instance(self):
        resp = self.create_instance()
        resp = self.bind_instance()
        resp = self.tc.delete('/v2/service_instances/' + self.instance_guid + '/service_bindings/' + self.binding_id
                              + '?service_id=' + SERVICE1_GUID + '&plan_id=' + PLAN1_GUID,
                              headers=self.hdrs)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(os.path.exists(self.service._path(self.instance_guid, self.binding_id)))

    def test_unbind_instance_nosuchbinding(self):
        resp = self.tc.delete('/v2/service_instances/' + self.instance_guid + '/service_bindings/nosuchbinding111'
                              + '?service_id=' + SERVICE1_GUID + '&plan_id=' + PLAN1_GUID,
                              headers=self.hdrs)
        self.assertEqual(resp.status_code, 410)