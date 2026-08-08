from django.urls import path

from .views import GeocodeAPIView, GeocodeSuggestAPIView, ReverseGeocodeAPIView, RouteAPIView


urlpatterns = [
    path("geocode", GeocodeAPIView.as_view(), name="geocode"),
    path("geocode/", GeocodeAPIView.as_view(), name="geocode-slash"),
    path("geocode/suggest", GeocodeSuggestAPIView.as_view(), name="geocode-suggest"),
    path("geocode/suggest/", GeocodeSuggestAPIView.as_view(), name="geocode-suggest-slash"),
    path("geocode/reverse", ReverseGeocodeAPIView.as_view(), name="geocode-reverse"),
    path("geocode/reverse/", ReverseGeocodeAPIView.as_view(), name="geocode-reverse-slash"),
    path("route", RouteAPIView.as_view(), name="route"),
    path("route/", RouteAPIView.as_view(), name="route-slash"),
]