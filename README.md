# cf-service-broker

This project provides all the generic bits of a cloud foundry service broker so you can just implement your specifics.  It provides a functioning API and base classes that implement all core features.  To implement a functioning broker you need to create a class with your specific provisioning methods, then the core broker will automatically handle asynchronous provisioning and all error messaging.

## Getting started

First we need to get a local copy working:

```bash
# git clone https://github.com/mattclarkdotnet/cf-service-broker.git
# cd cf-service-broker/
# mkvirtualenv --python=`which python3` --no-site-packages cf-service-broker
# workon cf-service-broker
# pip install -r requirements.txt
# export PYTHONPATH=./cf-service-broker/
# nosetests
.....
----------------------------------------------------------------------
Ran 5 tests in 0.118s

OK
#
```

Now we can look in test/test_api.py to see how to make a simple service broker.  Here's the interface:

```python
def create_instance(self, instance_id, plan, parameters, organization_guid, space_guid):
    raise NotImplementedError

def modify_instance(self, instance_id, plan, parameters, previous_values):
    raise NotImplementedError

def bind(self, instance_id, binding_id, plan_id, app_guid, parameters):
    raise NotImplementedError

def unbind(self, instance_id, binding_id, plan_id):
    raise NotImplementedError
```

And here's the minimal service implementation used for basic testing:

```python
class TestService(service.BaseService):
    def _filename(self, instance_id):
        return "/tmp/"+instance_id

    def create_instance(self, instance_id, plan, parameters, organization_guid, space_guid):
        with open(self._filename(instance_id), 'w+') as f:
            f.write(json.dumps(plan.as_dict()))
        return service.BaseServiceInstance(plan, parameters)

    def bind(self, instance_id, binding_id, plan_id, app_guid, parameters):
        creds = {"file": self._filename(instance_id)}
        return creds

    def unbind(self, instance_id, binding_id, plan_id):
        pass
```



