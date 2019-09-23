from rest_framework import routers

from network.api import views

router = routers.DefaultRouter()

router.register(r'jobs', views.JobView, base_name='jobs')
router.register(r'data', views.ObservationView, base_name='data')
router.register(r'observations', views.ObservationView, base_name='observations')
router.register(r'stations', views.StationView, base_name='stations')
router.register(r'transmitters', views.TransmitterView, base_name='transmitters')

api_urlpatterns = router.urls
