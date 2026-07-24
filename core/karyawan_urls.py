from django.urls import path
from . import karyawan_views

urlpatterns = [
    path('login/', karyawan_views.karyawan_login, name='karyawan_login'),
    path('logout/', karyawan_views.karyawan_logout, name='karyawan_logout'),
    path('dashboard/', karyawan_views.karyawan_dashboard, name='karyawan_dashboard'),
    
    # CRUD Buah
    path('buah/', karyawan_views.buah_list, name='karyawan_buah_list'),
    path('buah/<int:id_buah>/detail/', karyawan_views.buah_detail, name='karyawan_buah_detail'),
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
    
    # Cetak Struk
    path('pembelian/detail-struk/<int:id_pembelian>/', karyawan_views.get_detail_struk, name='karyawan_detail_struk'),
    path('pembelian/cetak-print/<int:id_pembelian>/', karyawan_views.cetak_struk_print, name='karyawan_cetak_print'),

    # Manajemen Grade Stok, Kerusakan & Olahan
    path('buah/update-qty/<int:id_detail>/', karyawan_views.update_qty_batch, name='karyawan_update_qty'),
    path('catat-kerusakan/<int:id_detail>/', karyawan_views.catat_kerusakan, name='karyawan_catat_kerusakan'),
    path('catat-olahan/<int:id_detail>/', karyawan_views.catat_olahan, name='karyawan_catat_olahan'),

    # CRUD Produk Olahan
    path('olahan/', karyawan_views.olahan_list, name='karyawan_olahan_list'),
    path('olahan/create/', karyawan_views.olahan_create, name='karyawan_olahan_create'),
    path('olahan/update/<int:id_olahan>/', karyawan_views.olahan_update, name='karyawan_olahan_update'),
    path('olahan/delete/<int:id_olahan>/', karyawan_views.olahan_delete, name='karyawan_olahan_delete'),

    # CRUD Penjualan Olahan
    path('penjualan-olahan/', karyawan_views.penjualan_list, name='karyawan_penjualan_list'),
    path('penjualan-olahan/create/', karyawan_views.penjualan_create, name='karyawan_penjualan_create'),
    path('penjualan-olahan/update/<int:id_penjualan>/', karyawan_views.penjualan_update, name='karyawan_penjualan_update'),
    path('penjualan-olahan/delete/<int:id_penjualan>/', karyawan_views.penjualan_delete, name='karyawan_penjualan_delete'),
]
