from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("", views.AuditViewSet, basename="audit")

urlpatterns = router.urls
