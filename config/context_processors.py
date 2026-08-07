from django.conf import settings


def google_maps(request):
    return {"GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY}


def courier_tracking(request):
    return {"SIMULATE_COURIER_TRACKING": settings.SIMULATE_COURIER_TRACKING}
