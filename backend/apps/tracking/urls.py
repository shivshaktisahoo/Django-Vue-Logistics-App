from django.urls import path

from . import views

urlpatterns = [
    path("live/", views.LiveMapView.as_view(), name="tracking-live"),
    path("shipments/<uuid:pk>/", views.ShipmentRouteView.as_view(), name="tracking-shipment"),
]

public_urlpatterns = [
    path("track/<str:tracking_number>/", views.PublicTrackView.as_view(), name="public-track"),
]
