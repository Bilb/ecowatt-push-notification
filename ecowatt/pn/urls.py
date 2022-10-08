from django.urls import re_path

from . import views

urlpatterns = [

    re_path(r'^register/(?P<device_type>A|I)', views.register, name='register'),
    re_path(r'^unregister/(?P<device_type>A|I)', views.unregister, name='unregister'),


]
