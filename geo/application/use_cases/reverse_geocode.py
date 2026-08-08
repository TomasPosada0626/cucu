from ...domain.services import GeocodingService


class ReverseGeocodeUseCase:
    def __init__(self, *, geocoding_service: GeocodingService | None = None):
        self._geocoding_service = geocoding_service or GeocodingService()

    def execute(self, *, latitud: float, longitud: float):
        return self._geocoding_service.reverse_geocode(latitud=latitud, longitud=longitud)
