from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("", views.TenderViewSet, basename="tender")

urlpatterns = router.urls
