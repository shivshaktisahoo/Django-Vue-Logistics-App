from rest_framework import serializers


class TenantPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """A FK input that only accepts rows from the request's organization.

    Without this, a client could attach another tenant's party or location by UUID.
    Pass `scope=callable(request) -> queryset` to narrow further (e.g. a customer's
    own address book).
    """

    def __init__(self, model=None, scope=None, **kwargs):
        self.model = model
        self.scope = scope
        if not kwargs.get("read_only"):
            kwargs.setdefault("queryset", model.objects.none())
        super().__init__(**kwargs)

    def get_queryset(self):
        request = self.context.get("request")
        org = getattr(request, "org", None)
        if org is None:
            return self.model.objects.none()
        if self.scope is not None:
            return self.scope(request)
        return self.model.objects.for_org(org)
