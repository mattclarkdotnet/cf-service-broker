from concurrent.futures import ProcessPoolExecutor
from typing import Optional, Iterable
from exceptions import *
from service import Plan
import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()


class Broker:
    def __init__(self, service_list: Iterable=None):
        if service_list is None:
            self.services = {}
        else:
            self.services = {s.guid: s for s in service_list}
        self.async_ops = {}

    def service_catalog(self) -> dict:
        return {"services": [s.as_dict() for s in self.services.values()]}

    def create_instance(self, instance_id: str, organization_guid: str, plan_id: str, service_id: str, space_guid: str,
                        parameters: dict=None,
                        accepts_incomplete: bool=False) -> dict:
        service = self.services[service_id]
        plan = service.plans[plan_id]
        sync = self._match_synchronicity(plan, accepts_incomplete)
        executor = ProcessPoolExecutor(max_workers=1)
        future = executor.submit(service.create_instance, instance_id, plan, parameters,
                                 organization_guid, space_guid)  # org and space are usually ignored
        if sync:
            dashboard_url = future.result(timeout=59)
            if dashboard_url:
                return {"dashboard_url": dashboard_url}
            else:
                return {}
        else:
            self.async_ops[instance_id] = future
            raise ProvisioningAsynchronously

    def delete_instance(self, instance_id: str, service_id: str, plan_id: str,
                        accepts_incomplete: bool=False) -> dict:
        service = self.services[service_id]
        plan = service.plans[plan_id]
        sync = self._match_synchronicity(plan, accepts_incomplete)
        executor = ProcessPoolExecutor(max_workers=1)
        future = executor.submit(service.delete_instance, instance_id)
        if sync:
            _ = future.result(timeout=59)
            return {}
        else:
            self.async_ops[instance_id] = future
            raise ProvisioningAsynchronously

    def modify_instance(self, instance_id: str, service_id: str, plan_id: str, parameters: str, previous_values: str,
                        accepts_incomplete: bool=False) -> dict:
        service = self.services[service_id]
        if not service.plan_updateable:
            raise UnsupportedPlanChangeError
        plan = service.plans[plan_id]
        sync = self._match_synchronicity(plan, accepts_incomplete)
        executor = ProcessPoolExecutor(max_workers=1)
        future = executor.submit(service.modify_instance, instance_id, plan, parameters, previous_values)
        if sync:
            _ = future.result(timeout=59)
            return {}
        else:
            self.async_ops[instance_id] = future
            raise ProvisioningAsynchronously

    def bind_instance(self, instance_id: str, binding_id: str, service_id: str, plan_id: str,
                      app_guid: str=None, parameters: dict=None) -> dict:
        return self.services[service_id].bind(instance_id, binding_id, plan_id, app_guid, parameters)

    def unbind_instance(self, instance_id: str, binding_id: str, service_id: str, plan_id: str):
        self.services[service_id].unbind(instance_id, binding_id, plan_id)

    def get_provisioning_state(self, instance_id: str) -> str:
        future = self.async_ops[instance_id]
        if future.running():
            return "in progress"
        if future.exception():
            return "failed"
        if future.done():
            return "succeeded"
        raise AsyncOperationStateNotHandledError

    @staticmethod
    def _match_synchronicity(plan: Plan, accepts_incomplete: bool=False) -> bool:
        # accepts_incomplete=False and provisionable_synchronously=False -> CannotProvisionSynchronouslyException
        # accepts_incomplete=False and provisionable_synchronously=True  -> sync
        # accepts_incomplete=True  and provisionable_synchronously=False -> async
        # accepts_incomplete=True  and provisionable_synchronously=True  -> sync
        if not accepts_incomplete and not plan.provisionable_synchronously:
            raise CannotProvisionSynchronouslyError
        return plan.provisionable_synchronously
