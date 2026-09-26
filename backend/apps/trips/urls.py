from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("", views.TripViewSet, basename="trip")

urlpatterns = router.urls
