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
        executor = ProcessPoolExecutor(max_workers=1)
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

    def delete_instance(self, instance_id, service_id, plan_id, accepts_incomplete):
        service = self.services[service_id]
        plan = service.plans[plan_id]
        sync = self._will_provision_synchronously(plan, accepts_incomplete)
        executor = ProcessPoolExecutor(max_workers=1)
        future = executor.submit(service.delete_instance, instance_id)
        if sync:
            _ = future.result(timeout=59)
            return dict()
        else:
            self.async_ops[instance_id] = future
            raise ProvisioningAsynchronously

    def modify_instance(self, instance_id, service_id, plan_id, parameters, previous_values, accepts_incomplete):
        service = self.services[service_id]
        if not service.plan_updateable:
            raise UnsupportedPlanChangeError
        plan = service.plans[plan_id]
        sync = self._will_provision_synchronously(plan, accepts_incomplete)
        executor = ProcessPoolExecutor(max_workers=1)
        future = executor.submit(service.modify_instance, instance_id, plan, parameters, previous_values)
        if sync:
            _ = future.result(timeout=59)
            return dict()
        else:
            self.async_ops[instance_id] = future
            raise ProvisioningAsynchronously

    def bind_instance(self, instance_id, binding_id, service_id, plan_id, app_guid=None, parameters=None):
        credentials = self.services[service_id].bind(instance_id, binding_id, plan_id, app_guid, parameters)
        return credentials

    def unbind_instance(self, instance_id, binding_id, service_id, plan_id):
        self.services[service_id].unbind(instance_id, binding_id, plan_id)

    def get_provisioning_state(self, instance_id):
        future = self.async_ops[instance_id]
        if future.running():
            return "in progress"
        if future.exception():
            return "failed"
        if future.done():
            return "succeeded"

    @staticmethod
    def _will_provision_synchronously(plan, accepts_incomplete):
        # accepts_incomplete=False and provisionable_synchronously=False -> CannotProvisionSynchronouslyException
        # accepts_incomplete=False and provisionable_synchronously=True  -> sync
        # accepts_incomplete=True  and provisionable_synchronously=False -> async
        # accepts_incomplete=True  and provisionable_synchronously=True  -> sync
        if not accepts_incomplete and not plan.provisionable_synchronously:
            raise CannotProvisionSynchronouslyError
        return plan.provisionable_synchronously
