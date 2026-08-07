from django.conf import settings


def google_maps(request):
    return {"GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY}
