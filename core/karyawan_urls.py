from django.urls import path
from . import karyawan_views

urlpatterns = [
    path('login/', karyawan_views.karyawan_login, name='karyawan_login'),
    path('logout/', karyawan_views.karyawan_logout, name='karyawan_logout'),
    path('dashboard/', karyawan_views.karyawan_dashboard, name='karyawan_dashboard'),
    
    # CRUD Buah
    path('buah/', karyawan_views.buah_list, name='karyawan_buah_list'),
    path('buah/create/', karyawan_views.buah_create, name='karyawan_buah_create'),
    path('buah/update/<int:id_buah>/', karyawan_views.buah_update, name='karyawan_buah_update'),
    path('buah/delete/<int:id_buah>/', karyawan_views.buah_delete, name='karyawan_buah_delete'),
    
    # CRUD Pelanggan
    path('pelanggan/', karyawan_views.pelanggan_list, name='karyawan_pelanggan_list'),
    path('pelanggan/create/', karyawan_views.pelanggan_create, name='karyawan_pelanggan_create'),
    path('pelanggan/create-cepat/', karyawan_views.pelanggan_create_cepat, name='karyawan_pelanggan_create_cepat'),
    path('pelanggan/update/<int:id_pelanggan>/', karyawan_views.pelanggan_update, name='karyawan_pelanggan_update'),
    path('pelanggan/delete/<int:id_pelanggan>/', karyawan_views.pelanggan_delete, name='karyawan_pelanggan_delete'),
    
    # CRUD Pembelian
    path('pembelian/', karyawan_views.pembelian_list, name='karyawan_pembelian_list'),
    path('pembelian/create/', karyawan_views.pembelian_create, name='karyawan_pembelian_create'),
    path('pembelian/update/<int:id_pembelian>/', karyawan_views.pembelian_update, name='karyawan_pembelian_update'),
    path('pembelian/delete/<int:id_pembelian>/', karyawan_views.pembelian_delete, name='karyawan_pembelian_delete'),
    
    # Detail Pembelian (Item)
    path('pembelian/tambah-item/<int:id_pembelian>/', karyawan_views.tambah_detail_pembelian, name='karyawan_tambah_detail'),
    path('pembelian/hapus-item/<int:id_detail>/', karyawan_views.hapus_detail_pembelian, name='karyawan_hapus_detail'),
]
