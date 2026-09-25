from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("current/members", views.MemberViewSet, basename="member")

urlpatterns = [
    path("", views.MyOrgsView.as_view(), name="my-orgs"),
    path("current/", views.CurrentOrgView.as_view(), name="current-org"),
    *router.urls,
]
