"""Resolves the active organization for a request.

JWT authentication runs inside DRF (not Django middleware), so the org is resolved
in the view's `initial()` after authentication, from the `X-Org-Id` header.
Non-members get a 404 so org IDs cannot be probed.
"""

from rest_framework.exceptions import NotFound, PermissionDenied

ORG_HEADER = "HTTP_X_ORG_ID"


def resolve_membership(request):
    from apps.organizations.selectors import get_active_membership

    org_id = request.META.get(ORG_HEADER)
    if not org_id:
        raise PermissionDenied("X-Org-Id header is required.")
    membership = get_active_membership(user=request.user, org_id=org_id)
    if membership is None:
        raise NotFound("Organization not found.")
    return membership


class TenantScopedMixin:
    """Mixin for DRF views whose data belongs to one organization.

    Sets `request.org` / `request.membership`, then enforces `required_permissions`:
    a dict mapping the DRF action (or lowercase HTTP method) to a permission code,
    e.g. {"list": "shipments.view", "create": "shipments.manage"}. Actions missing
    from the dict are denied, so new endpoints are closed by default.
    """

    required_permissions: dict[str, str] = {}

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        membership = resolve_membership(request)
        request.membership = membership
        request.org = membership.org
        action = getattr(self, "action", None) or request.method.lower()
        if action == "metadata":
            return
        code = self.required_permissions.get(action)
        if code is None or not membership.has_perm(code):
            raise PermissionDenied("Your role does not allow this action.")
