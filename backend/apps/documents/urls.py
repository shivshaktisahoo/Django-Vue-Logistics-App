from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("", views.DocumentViewSet, basename="document")

urlpatterns = router.urls
