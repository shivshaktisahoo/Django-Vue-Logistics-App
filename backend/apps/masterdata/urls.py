from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("parties", views.PartyViewSet, basename="party")
router.register("locations", views.LocationViewSet, basename="location")
router.register("carriers", views.CarrierViewSet, basename="carrier")
router.register("vehicles", views.VehicleViewSet, basename="vehicle")
router.register("drivers", views.DriverViewSet, basename="driver")

urlpatterns = router.urls
