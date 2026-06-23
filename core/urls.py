from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('auth/', views.authenticated_user, name='auth'),
    path('login-pelanggan/', views.login_pelanggan, name='login_pelanggan'),
    path('register-pelanggan/', views.register_pelanggan, name='register_pelanggan'),
    path('logout-pelanggan/', views.logout_pelanggan, name='logout_pelanggan'),
    path('tambah-ke-keranjang/<int:id_buah>/', views.tambah_ke_keranjang, name='tambah_ke_keranjang'),
    path('hapus-item-keranjang/<int:id_buah>/', views.hapus_item_keranjang, name='hapus_item_keranjang'),
    path('checkout/', views.checkout, name='checkout'),
    path('update-cart/<int:id_buah>/<str:action>/', views.update_cart, name='update_cart'),
    path('shop/', views.buah, name='buah'),
    path('shop-detail/', views.shop_detail, name='shop-detail'),
    path('cart/', views.keranjang, name='keranjang'),
    path('contact/', views.kontak, name='kontak'),
]