from unittest import TestCase
import json
import base64
import api
import broker
import service
import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()


class TestService(service.BaseService):
    def create_instance(self, instance_id, plan, parameters, organization_guid, space_guid):
        with open('/tmp/'+instance_id, 'w+') as f:
            f.write(json.dumps(plan.as_dict()))
        return service.BaseServiceInstance(plan, parameters)

    def bind(self, instance_id, binding_id, plan_id, app_guid, parameters):
        creds = {"file": "/tmp/"+instance_id}
        return creds


SERVICE1_GUID = '4d29b1b1-63c3-425e-97e4-913be8fdaf19'
PLAN1_GUID = 'e1697e2c-967e-4b4c-8eea-a20d0b2a41d0'
PLAN2_GUID = 'd9edc392-68d6-4622-a760-5be7d76efca3'

plan_1 = service.Plan(guid=PLAN1_GUID, name="small plan", description="A small generic service plan")
plan_2 = service.Plan(guid=PLAN2_GUID, name="large plan", description="A large generic service plan",
                      provisionable_synchronously=False)
service_1 = TestService(guid=SERVICE1_GUID,
                        name="generic_service",
                        description="A service that gives generic service",
                        bindable=True,
                        plans={plan_1.guid: plan_1, plan_2.guid: plan_2},
                        dashboard_client={"id": "client-id-1",
                                          "secret": "secret-1",
                                          "redirect_uri": "https://generic.service.somewhere/dashboard"})

api.broker = broker.Broker(service_list=[service_1,])


class APITestCase(TestCase):
    def setUp(self):
        self.tc = api.app.test_client()
        self.hdrs = {'X-Broker-Api-Version': '2.7',
                     'Content-Type': 'application/json',
                     'Authorization': 'Basic ' + base64.b64encode(b"u:p").decode("ascii")}


class TestGetCatalog(APITestCase):
    def test_get_catalog(self):
        resp = self.tc.get('/v2/catalog', headers=self.hdrs)
        log.debug(resp.data)
        catalog = json.loads(resp.data.decode('ascii'))
        self.assertEqual(type(catalog), dict)
        service_1 = catalog['services'][0]
        self.assertEqual(service_1['id'], SERVICE1_GUID)


class TestAuth(APITestCase):
    def test_auth_denied(self):
        hdrs = dict(self.hdrs)
        hdrs.pop('Authorization')
        resp = self.tc.get('/v2/catalog', headers=hdrs)
        self.assertEqual(resp.status_code, 401)


class TestCreateInstance(APITestCase):
    def setUp(self):
        super(TestCreateInstance, self).setUp()
        self.instance_guid = '1234'
        self.org_guid = '2345'
        self.space_guid = '3456'
        self.app_guid = '4567'
        self.binding_id = '5678'

    def test_create_instance(self):
        req_data = {"organization_guid": self.org_guid,
                    "plan_id": PLAN1_GUID,
                    "service_id": SERVICE1_GUID,
                    "space_guid": self.space_guid}
        resp = self.tc.put('/v2/service_instances/' + self.instance_guid, headers=self.hdrs, data=json.dumps(req_data))
        self.assertEqual(resp.status_code, 201)

    def test_create_instance_noasync(self):
        req_data = {"organization_guid": self.org_guid,
                    "plan_id": PLAN2_GUID,
                    "service_id": SERVICE1_GUID,
                    "space_guid": self.space_guid,
                    "accepts_incomplete": False}
        resp = self.tc.put('/v2/service_instances/' + self.instance_guid, headers=self.hdrs, data=json.dumps(req_data))
        self.assertEqual(resp.status_code, 422)

    def test_bind_instance(self):
        req_data = {"plan_id": PLAN1_GUID,
                    "service_id": SERVICE1_GUID,
                    "app_guid": self.app_guid,
                    "parameters": {'a': 'b'}}
        resp = self.tc.put('/v2/service_instances/' + self.instance_guid + '/service_bindings/' + self.binding_id,
                           headers=self.hdrs, data=json.dumps(req_data))
        self.assertEqual(resp.status_code, 201)
        d = json.loads(resp.data.decode(encoding='UTF-8'))
        self.assertIn('credentials', d)
        self.assertEqual(d['credentials'], {'file': '/tmp/'+self.instance_guid})