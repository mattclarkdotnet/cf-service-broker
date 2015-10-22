import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()


class BaseService:
    def __init__(self, guid, name, description, bindable, plans,
                 dashboard_client=None,
                 tags=None,
                 metadata=None,
                 requires=None,
                 plan_updateable=False,
                 ):
        self.guid = guid
        self.plans = plans
        self.name = name
        self.description = description
        self.bindable = bindable
        self.plans = plans
        # optional properties
        self.dashboard_client = dashboard_client
        self.tags = tags
        self.metadata = metadata
        self.requires = requires
        self.plan_updateable = plan_updateable

    def create_instance(self, instance_id, plan, parameters, organization_guid, space_guid):
        raise NotImplementedError

    def delete_instance(self, instance_id):
        raise NotImplementedError

    def modify_instance(self, instance_id, plan, parameters, previous_values):
        raise NotImplementedError

    def bind(self, instance_id, binding_id, plan_id, app_guid, parameters):
        raise NotImplementedError

    def unbind(self, instance_id, binding_id, plan_id):
        raise NotImplementedError

    def as_dict(self):
        d = {'id' if k == 'guid' else k: getattr(self, k) for k in ('guid', 'name', 'description', 'bindable')}
        d['plans'] = [p.as_dict() for p in self.plans.values()]
        return d


class Plan(object):
    def __init__(self, guid, name, description,
                 free=True,
                 metadata=None,
                 provisionable_synchronously=True,
                 provisionable_asynchronously=False,
                 ):
        self.guid = guid
        self.name = name
        self.description = description
        # optional properties
        self.free = free
        self.provisionable_synchronously = provisionable_synchronously
        self.provisionable_asynchronously = provisionable_asynchronously
        self.metadata = metadata

    def as_dict(self):
        return {'id' if k == 'guid' else k: getattr(self, k) for k in ('guid', 'name', 'description')}

