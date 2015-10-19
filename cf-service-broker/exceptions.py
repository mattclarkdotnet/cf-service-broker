class CannotProvisionSynchronouslyError(Exception):
    msg = {"error": "AsyncRequired",
           "description": "This service plan requires client support for asynchronous service operations."}


class BindingExistsError(Exception):
    msg = {"error": "BindingExistsError",
           "description": "binding already exists"}


class AppGUIDRequiredError(Exception):
    msg = {"error": "AppGUIDRequiredError",
           "description": "This service supports generation of credentials through binding an application only."}


class BindingNotSupportedError(Exception):
    msg = {"error": "BindingNotSupportedError",
           "description": "service does not support binding"}


class UnsupportedPlanChangeError(Exception):
    msg = {"error": "UnsupportedPlanChangeError",
           "description": "service does not support your requested change of plan"}


class CurrentlyNotPossiblePlanChangeError(Exception):
    msg = {"error": "CurrentlyNotPossiblePlanChangeError",
           "description": "service supports your requested change of plan but it is not possible right now"}


class ServiceConflictError(Exception):
    pass


class ProvisioningAsynchronously(Exception):
    pass


class NoSuchEntityError(Exception):
    pass