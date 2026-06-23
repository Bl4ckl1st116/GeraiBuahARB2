from django.urls import path
from . import views

# URL patterns untuk sistem pelaporan
# Base path: 'admin/laporan/' (sudah didefinisikan di randiTA/urls.py)
urlpatterns = [
    path('', views.laporan_dashboard, name='laporan_dashboard'),
    path('<str:tipe>/', views.preview_laporan, name='preview_laporan'),
    path('<str:tipe>/cetak/', views.cetak_laporan_final, name='cetak_laporan_final'),
]
