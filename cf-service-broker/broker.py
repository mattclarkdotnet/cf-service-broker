from concurrent.futures import ProcessPoolExecutor
from exceptions import *
import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()


class Broker(object):
    def __init__(self, service_list=None):
        if service_list is None:
            service_list = []
        self.services = {s.guid: s for s in service_list}
        self.async_ops = {}

    def service_catalog(self):
        return {"services": [s.as_dict() for s in self.services.values()]}

    def create_instance(self, instance_id, organization_guid, plan_id, service_id, space_guid,
                        parameters=None,
                        accepts_incomplete=False):
        service = self.services[service_id]
        plan = service.plans[plan_id]
        sync = self._will_provision_synchronously(plan, accepts_incomplete)
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(service.create_instance, instance_id, plan, parameters,
                                     organization_guid, space_guid)  # org and space are usually ignored
            if sync:
                service_instance = future.result(timeout=59)
                if service_instance.dashboard_url:
                    return {"dashboard_url": service_instance.dashboard_url}
                else:
                    return dict()
            else:
                self.async_ops[instance_id] = future
                raise ProvisioningAsynchronously

    def get_provisioning_state(self, instance_id):
        future = self.async_ops[instance_id]
        if future.running():
            return "in progress"
        if future.exception():
            return "failed"
        if future.done():
            return "succeeded"

    def bind_instance(self, instance_id, binding_id, service_id, plan_id, app_guid=None, parameters=None):
        return self.services[service_id].bind(instance_id, binding_id, plan_id, app_guid, parameters)

    @staticmethod
    def _will_provision_synchronously(plan, accepts_incomplete):
        # accepts_incomplete=False and provisionable_synchronously=False -> CannotProvisionSynchronouslyException
        # accepts_incomplete=False and provisionable_synchronously=True  -> sync
        # accepts_incomplete=True  and provisionable_synchronously=False -> async
        # accepts_incomplete=True  and provisionable_synchronously=True  -> sync
        if not accepts_incomplete and not plan.provisionable_synchronously:
            raise CannotProvisionSynchronouslyError
        return plan.provisionable_synchronously
