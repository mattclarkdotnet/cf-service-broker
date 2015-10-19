class CannotProvisionSynchronouslyError(Exception):
    msg = {"error": "AsyncRequired",
           "description": "This service plan requires client support for asynchronous service operations."}


class BindingExistsError(Exception):
    msg = {"error": "BindingExistsError",
           "description": "binding already exists"}


class AppGUIDRequiredError(Exception):
    msg = {"error": "AppGUIDRequiredError",
           "description": "This service supports generation of credentials through binding an application only." }


class BindingNotSupportedError(Exception):
    msg = {"error": "BindingNotSupportedError",
           "description": "service does not support binding"}


class ServiceConflictError(Exception): pass


class ProvisioningAsynchronously(Exception): pass


class DashboardClient:
    def __init__(self, guid, secret, dashboard_uri):
        self.guid = guid
        self.secret = secret
        self.dashboard_uri = dashboard_uri

