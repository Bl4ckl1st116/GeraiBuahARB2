from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.core.paginator import Paginator
from django.db import transaction
from functools import wraps
from datetime import datetime

from django.http import JsonResponse
from .models import (
    Buah, Pelanggan, Pembelian, DetailPembelian,
    Pemasok, Pengadaan, DetailPengadaan, Karyawan, LogAktivitasKaryawan,
    ProfilToko
)


# ======================================================
# DECORATOR KUSTOM
# ======================================================
def karyawan_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'karyawan_id' not in request.session:
            messages.error(request, 'Silakan login terlebih dahulu untuk mengakses portal karyawan.')
            return redirect('karyawan_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ======================================================
# LOGIKA AUTENTIKASI KARYAWAN
# ======================================================
def karyawan_login(request):
    if 'karyawan_id' in request.session:
        return redirect('karyawan_dashboard')

    if request.method == 'POST':
        no_hp = request.POST.get('noHp', '').strip()
        password = request.POST.get('password', '').strip()

        if not no_hp or not password:
            messages.error(request, 'Nomor HP dan Password wajib diisi.')
            return render(request, 'core/karyawan/login.html')

        karyawan = Karyawan.objects.filter(noHp=no_hp).first()
        if karyawan and check_password(password, karyawan.password):
            request.session['karyawan_id'] = karyawan.idKaryawan
            request.session['karyawan_nama'] = karyawan.namaKaryawan
            messages.success(request, f'Selamat datang kembali, {karyawan.namaKaryawan}!')
            return redirect('karyawan_dashboard')
        else:
            messages.error(request, 'Nomor HP atau Password salah.')

    return render(request, 'core/karyawan/login.html')


def karyawan_logout(request):
    request.session.pop('karyawan_id', None)
    request.session.pop('karyawan_nama', None)
    messages.success(request, 'Anda telah keluar dari Portal Karyawan.')
    return redirect('karyawan_login')


# ======================================================
# DASHBOARD PORTAL KARYAWAN
# ======================================================
@karyawan_required
def karyawan_dashboard(request):
    karyawan_id = request.session['karyawan_id']
    karyawan = Karyawan.objects.get(pk=karyawan_id)

    total_buah = Buah.objects.count()
    total_pembelian = Pembelian.objects.count()
    total_pelanggan = Pelanggan.objects.count()

    # Log aktivitas terbaru
    logs = LogAktivitasKaryawan.objects.all().order_by('-timestamp')[:10]

    context = {
        'karyawan': karyawan,
        'total_buah': total_buah,
        'total_pembelian': total_pembelian,
        'total_pelanggan': total_pelanggan,
        'logs': logs,
    }
    return render(request, 'core/karyawan/dashboard.html', context)


# ======================================================
# CRUD BUAH
# ======================================================
@karyawan_required
def buah_list(request):
    q = request.GET.get('q', '').strip()
    limit = request.GET.get('limit', '10')

    buah_queryset = Buah.objects.all().order_by('namaBuah')
    if q:
        buah_queryset = buah_queryset.filter(namaBuah__icontains=q)

    if limit == 'all':
        buah_items = buah_queryset
    else:
        try:
            limit_int = int(limit)
        except ValueError:
            limit_int = 10
        paginator = Paginator(buah_queryset, limit_int)
        page_number = request.GET.get('page')
        buah_items = paginator.get_page(page_number)

    return render(request, 'core/karyawan/buah_list.html', {
        'buah_items': buah_items,
        'q': q,
        'limit': limit
    })


@karyawan_required
def buah_create(request):
    if request.method == 'POST':
        nama = request.POST.get('namaBuah', '').strip()
        harga = request.POST.get('hargaBuah', '').strip()
        deskripsi = request.POST.get('deskripsiBuah', '').strip()
        diskon = request.POST.get('diskon', '0').strip()
        lama_kesegaran = request.POST.get('lamaKesegaraan', '').strip()
        foto = request.FILES.get('fotoBuah')

        if not all([nama, harga, deskripsi, lama_kesegaran, foto]):
            messages.error(request, 'Semua kolom data buah wajib diisi beserta foto buah.')
            return redirect('karyawan_buah_list')

        try:
            # Konversi persen diskon ke desimal
            diskon_dec = float(diskon) / 100.0 if float(diskon) > 0 else 0.0
            
            buah = Buah.objects.create(
                namaBuah=nama,
                hargaBuah=float(harga),
                deskripsiBuah=deskripsi,
                diskon=diskon_dec,
                lamaKesegaraan=int(lama_kesegaran),
                fotoBuah=foto
            )

            # Catat Log
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='CREATE',
                target_model='Buah',
                target_id=buah.idBuah,
                deskripsi=f"Karyawan {karyawan.namaKaryawan} menambahkan produk buah baru: '{buah.namaBuah}' dengan harga Rp {harga} ribu/kg."
            )
            messages.success(request, f"Buah '{buah.namaBuah}' berhasil ditambahkan.")
        except Exception as e:
            messages.error(request, f"Gagal menambahkan buah: {str(e)}")

    return redirect('karyawan_buah_list')


@karyawan_required
def buah_update(request, id_buah):
    buah = get_object_or_404(Buah, pk=id_buah)
    if request.method == 'POST':
        nama = request.POST.get('namaBuah', '').strip()
        harga = request.POST.get('hargaBuah', '').strip()
        deskripsi = request.POST.get('deskripsiBuah', '').strip()
        diskon = request.POST.get('diskon', '0').strip()
        lama_kesegaran = request.POST.get('lamaKesegaraan', '').strip()
        foto = request.FILES.get('fotoBuah')

        if not all([nama, harga, deskripsi, lama_kesegaran]):
            messages.error(request, 'Semua data wajib diisi kecuali foto.')
            return redirect('karyawan_buah_list')

        try:
            diskon_dec = float(diskon) / 100.0 if float(diskon) > 0 else 0.0
            
            buah.namaBuah = nama
            buah.hargaBuah = float(harga)
            buah.deskripsiBuah = deskripsi
            buah.diskon = diskon_dec
            buah.lamaKesegaraan = int(lama_kesegaran)
            
            if foto:
                buah.fotoBuah = foto

            buah.save()

            # Catat Log
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='UPDATE',
                target_model='Buah',
                target_id=buah.idBuah,
                deskripsi=f"Karyawan {karyawan.namaKaryawan} memperbarui data produk buah '{buah.namaBuah}'."
            )
            messages.success(request, f"Data buah '{buah.namaBuah}' berhasil diperbarui.")
        except Exception as e:
            messages.error(request, f"Gagal memperbarui buah: {str(e)}")

    return redirect('karyawan_buah_list')


@karyawan_required
def buah_delete(request, id_buah):
    buah = get_object_or_404(Buah, pk=id_buah)
    try:
        nama_buah = buah.namaBuah
        buah_id = buah.idBuah
        buah.delete()

        # Catat Log
        karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
        LogAktivitasKaryawan.objects.create(
            idKaryawan=karyawan,
            aksi='DELETE',
            target_model='Buah',
            target_id=buah_id,
            deskripsi=f"Karyawan {karyawan.namaKaryawan} menghapus produk buah '{nama_buah}'."
        )
        messages.success(request, f"Buah '{nama_buah}' berhasil dihapus.")
    except Exception as e:
        messages.error(request, f"Gagal menghapus buah: {str(e)}")

    return redirect('karyawan_buah_list')


# ======================================================
# CRUD PELANGGAN
# ======================================================
@karyawan_required
def pelanggan_list(request):
    q = request.GET.get('q', '').strip()
    limit = request.GET.get('limit', '10')

    pelanggan_queryset = Pelanggan.objects.all().order_by('namaPelanggan')
    if q:
        from django.db.models import Q
        pelanggan_queryset = pelanggan_queryset.filter(
            Q(namaPelanggan__icontains=q) | 
            Q(username__icontains=q) | 
            Q(noHp__icontains=q) |
            Q(alamat__icontains=q)
        )

    if limit == 'all':
        pelanggan_items = pelanggan_queryset
    else:
        try:
            limit_int = int(limit)
        except ValueError:
            limit_int = 10
        paginator = Paginator(pelanggan_queryset, limit_int)
        page_number = request.GET.get('page')
        pelanggan_items = paginator.get_page(page_number)

    return render(request, 'core/karyawan/pelanggan_list.html', {
        'pelanggan_items': pelanggan_items,
        'q': q,
        'limit': limit
    })


@karyawan_required
def pelanggan_create(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        nama = request.POST.get('namaPelanggan', '').strip()
        alamat = request.POST.get('alamat', '').strip()
        no_hp = request.POST.get('noHp', '').strip()

        if not all([username, password, nama, alamat, no_hp]):
            messages.error(request, 'Semua kolom data pelanggan wajib diisi.')
            return redirect('karyawan_pelanggan_list')

        if Pelanggan.objects.filter(username=username).exists():
            messages.error(request, 'Username pelanggan sudah terdaftar.')
            return redirect('karyawan_pelanggan_list')

        try:
            pelanggan = Pelanggan.objects.create(
                username=username,
                password=password,
                namaPelanggan=nama,
                alamat=alamat,
                noHp=no_hp
            )

            # Catat Log
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='CREATE',
                target_model='Pelanggan',
                target_id=pelanggan.idPelanggan,
                deskripsi=f"Karyawan {karyawan.namaKaryawan} mendaftarkan akun pelanggan baru: '{pelanggan.namaPelanggan}'."
            )
            messages.success(request, f"Pelanggan '{pelanggan.namaPelanggan}' berhasil ditambahkan.")
        except Exception as e:
            messages.error(request, f"Gagal menambahkan pelanggan: {str(e)}")

    return redirect('karyawan_pelanggan_list')


@karyawan_required
def pelanggan_update(request, id_pelanggan):
    pelanggan = get_object_or_404(Pelanggan, pk=id_pelanggan)
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        nama = request.POST.get('namaPelanggan', '').strip()
        alamat = request.POST.get('alamat', '').strip()
        no_hp = request.POST.get('noHp', '').strip()

        if not all([username, nama, alamat, no_hp]):
            messages.error(request, 'Username, Nama, Alamat, dan No HP wajib diisi.')
            return redirect('karyawan_pelanggan_list')

        try:
            pelanggan.username = username
            pelanggan.namaPelanggan = nama
            pelanggan.alamat = alamat
            pelanggan.noHp = no_hp
            
            if password:
                pelanggan.password = password

            pelanggan.save()

            # Catat Log
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='UPDATE',
                target_model='Pelanggan',
                target_id=pelanggan.idPelanggan,
                deskripsi=f"Karyawan {karyawan.namaKaryawan} memperbarui data pelanggan '{pelanggan.namaPelanggan}'."
            )
            messages.success(request, f"Data pelanggan '{pelanggan.namaPelanggan}' berhasil diperbarui.")
        except Exception as e:
            messages.error(request, f"Gagal memperbarui data pelanggan: {str(e)}")

    return redirect('karyawan_pelanggan_list')


@karyawan_required
def pelanggan_delete(request, id_pelanggan):
    pelanggan = get_object_or_404(Pelanggan, pk=id_pelanggan)
    try:
        nama_pelanggan = pelanggan.namaPelanggan
        pelanggan_id = pelanggan.idPelanggan
        pelanggan.delete()

        # Catat Log
        karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
        LogAktivitasKaryawan.objects.create(
            idKaryawan=karyawan,
            aksi='DELETE',
            target_model='Pelanggan',
            target_id=pelanggan_id,
            deskripsi=f"Karyawan {karyawan.namaKaryawan} menghapus akun pelanggan '{nama_pelanggan}'."
        )
        messages.success(request, f"Akun pelanggan '{nama_pelanggan}' berhasil dihapus.")
    except Exception as e:
        messages.error(request, f"Gagal menghapus pelanggan: {str(e)}")

    return redirect('karyawan_pelanggan_list')


# ======================================================
# CRUD PEMBELIAN (TRANSAKSI / PESANAN)
# ======================================================
@karyawan_required
def pembelian_list(request):
    q = request.GET.get('q', '').strip()
    limit = request.GET.get('limit', '10')

    pembelian_queryset = Pembelian.objects.all().order_by('-tanggalPembelian')
    if q:
        from django.db.models import Q
        query_filter = Q(idPelanggan__namaPelanggan__icontains=q) | Q(alamatPengiriman__icontains=q) | Q(statusPembelian__icontains=q) | Q(metodeBayar__icontains=q)
        if q.isdigit():
            query_filter |= Q(idPembelian=int(q))
        pembelian_queryset = pembelian_queryset.filter(query_filter)

    pelanggan_list = Pelanggan.objects.all().order_by('namaPelanggan')
    buah_list = Buah.objects.all().order_by('namaBuah')

    if limit == 'all':
        pembelian_items = pembelian_queryset
    else:
        try:
            limit_int = int(limit)
        except ValueError:
            limit_int = 10
        paginator = Paginator(pembelian_queryset, limit_int)
        page_number = request.GET.get('page')
        pembelian_items = paginator.get_page(page_number)

    profil_toko, created = ProfilToko.objects.get_or_create(pk=1, defaults={'nama_toko': 'GERAI BUAH ARB'})

    return render(request, 'core/karyawan/pembelian_list.html', {
        'pembelian_items': pembelian_items,
        'pelanggan_list': pelanggan_list,
        'buah_list': buah_list,
        'q': q,
        'limit': limit,
        'profil_toko': profil_toko
    })


@karyawan_required
def get_detail_struk(request, id_pembelian):
    pembelian = get_object_or_404(Pembelian, idPembelian=id_pembelian)
    items = []
    for det in pembelian.detailpembelian_set.all():
        items.append({
            'nama': det.idBuah.namaBuah,
            'qty': float(det.kuantitas),
            'harga': float(det.idBuah.hargaBuah),
            'subtotal': float(det.subHarga)
        })
    
    # logo url
    logo_url = ""
    profil_toko, created = ProfilToko.objects.get_or_create(pk=1, defaults={'nama_toko': 'GERAI BUAH ARB'})
    if profil_toko.logo_struk:
        logo_url = request.build_absolute_uri(profil_toko.logo_struk.url)

    data = {
        'id_pembelian': pembelian.idPembelian,
        'nama_pelanggan': pembelian.idPelanggan.namaPelanggan,
        'waktu_pembelian': pembelian.tanggalPembelian.strftime('%d-%m-%Y %H:%M'),
        'items': items,
        'total_harga': float(pembelian.totalHargaPembelian),
        'logo_url': logo_url
    }
    return JsonResponse(data)


def cetak_struk_print(request, id_pembelian):
    is_karyawan = 'karyawan_id' in request.session
    is_staff = request.user.is_authenticated and request.user.is_staff
    if not (is_karyawan or is_staff):
        messages.error(request, 'Akses ditolak.')
        return redirect('karyawan_login')
        
    pembelian = get_object_or_404(Pembelian, idPembelian=id_pembelian)
    profil_toko, created = ProfilToko.objects.get_or_create(pk=1, defaults={'nama_toko': 'GERAI BUAH ARB'})
    
    logo_url = None
    if profil_toko.logo_struk:
        logo_url = request.build_absolute_uri(profil_toko.logo_struk.url)
        
    kasir_nama = "KK KARTINI TARIGAN"
    if is_karyawan:
        kasir_nama = request.session.get('karyawan_nama', kasir_nama)
    elif is_staff:
        kasir_nama = request.user.get_full_name() or request.user.username
        
    return render(request, 'core/karyawan/struk_print.html', {
        'pembelian': pembelian,
        'profil_toko': profil_toko,
        'logo_url': logo_url,
        'kasir_nama': kasir_nama,
        'current_time': datetime.now().strftime('%d-%m-%Y %H:%M')
    })


@karyawan_required
def pembelian_create(request):
    if request.method == 'POST':
        id_pelanggan = request.POST.get('idPelanggan')
        metode_bayar = request.POST.get('metodeBayar', 'COD')
        alamat = request.POST.get('alamatPengiriman', '').strip()
        status = request.POST.get('statusPembelian', 'Menunggu')
        bukti = request.FILES.get('buktiBayar')

        if not id_pelanggan or not alamat:
            messages.error(request, 'Data Pelanggan dan Alamat Pengiriman wajib diisi.')
            return redirect('karyawan_pembelian_list')

        try:
            pelanggan = Pelanggan.objects.get(pk=id_pelanggan)
            pembelian = Pembelian.objects.create(
                idPelanggan=pelanggan,
                metodeBayar=metode_bayar,
                alamatPengiriman=alamat,
                statusPembelian=status
            )
            
            if bukti:
                pembelian.buktiBayar = bukti
                pembelian.save()

            # Catat Log
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='CREATE',
                target_model='Pembelian',
                target_id=pembelian.idPembelian,
                deskripsi=f"Karyawan {karyawan.namaKaryawan} membuat pesanan baru (ID: {pembelian.idPembelian}) untuk pelanggan '{pelanggan.namaPelanggan}'."
            )
            
            # Alihkan ke halaman edit untuk menambahkan item buah ke dalam pesanan ini
            messages.success(request, f"Pesanan ID {pembelian.idPembelian} berhasil dibuat. Silakan tambahkan buah.")
            return redirect('karyawan_pembelian_list')
        except Exception as e:
            messages.error(request, f"Gagal membuat pesanan: {str(e)}")

    return redirect('karyawan_pembelian_list')


@karyawan_required
def pembelian_update(request, id_pembelian):
    pembelian = get_object_or_404(Pembelian, pk=id_pembelian)
    if request.method == 'POST':
        metode_bayar = request.POST.get('metodeBayar')
        alamat = request.POST.get('alamatPengiriman', '').strip()
        status = request.POST.get('statusPembelian')
        bukti = request.FILES.get('buktiBayar')

        if not alamat or not status:
            messages.error(request, 'Alamat pengiriman dan Status wajib diisi.')
            return redirect('karyawan_pembelian_list')

        try:
            old_status = pembelian.statusPembelian
            
            pembelian.metodeBayar = metode_bayar
            pembelian.alamatPengiriman = alamat
            pembelian.statusPembelian = status
            
            if bukti:
                pembelian.buktiBayar = bukti
                
            pembelian.save()

            # Catat Log
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
            
            status_desc = f"dari '{old_status}' menjadi '{status}'" if old_status != status else f"status '{status}'"
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='UPDATE',
                target_model='Pembelian',
                target_id=pembelian.idPembelian,
                deskripsi=f"Karyawan {karyawan.namaKaryawan} memperbarui data pesanan ID {pembelian.idPembelian} ({status_desc})."
            )
            messages.success(request, f"Pesanan ID {pembelian.idPembelian} berhasil diperbarui.")
        except Exception as e:
            messages.error(request, f"Gagal memperbarui pesanan: {str(e)}")

    return redirect('karyawan_pembelian_list')


@karyawan_required
def pembelian_delete(request, id_pembelian):
    pembelian = get_object_or_404(Pembelian, pk=id_pembelian)
    try:
        pembelian_id = pembelian.idPembelian
        nama_pelanggan = pembelian.idPelanggan.namaPelanggan
        pembelian.delete()

        # Catat Log
        karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
        LogAktivitasKaryawan.objects.create(
            idKaryawan=karyawan,
            aksi='DELETE',
            target_model='Pembelian',
            target_id=pembelian_id,
            deskripsi=f"Karyawan {karyawan.namaKaryawan} menghapus pesanan ID {pembelian_id} milik pelanggan '{nama_pelanggan}'."
        )
        messages.success(request, f"Pesanan ID {pembelian_id} berhasil dihapus.")
    except Exception as e:
        messages.error(request, f"Gagal menghapus pesanan: {str(e)}")

    return redirect('karyawan_pembelian_list')


# ======================================================
# INLINE ITEM DETAIL PEMBELIAN (PENGELOLAAN ISI PESANAN)
# ======================================================
@karyawan_required
def tambah_detail_pembelian(request, id_pembelian):
    pembelian = get_object_or_404(Pembelian, pk=id_pembelian)
    if request.method == 'POST':
        id_buah = request.POST.get('idBuah')
        qty_str = request.POST.get('kuantitas', '').strip()

        if not id_buah or not qty_str:
            messages.error(request, 'Buah dan Kuantitas wajib dipilih/diisi.')
            return redirect('karyawan_pembelian_list')

        try:
            qty = int(qty_str)
            buah = Buah.objects.get(pk=id_buah)

            # Validasi stok secara programatik
            stok_tersedia = buah.stokBuah
            if qty > stok_tersedia:
                messages.error(request, f"Stok buah {buah.namaBuah} tidak mencukupi (stok tersedia: {stok_tersedia} kg).")
                return redirect('karyawan_pembelian_list')

            # Buat DetailPembelian (Akan mentrigger signal FIFO otomatis)
            with transaction.atomic():
                detail = DetailPembelian.objects.create(
                    idPembelian=pembelian,
                    idBuah=buah,
                    kuantitas=qty
                )
                # Panggil update_total secara manual untuk memicu re-kalkulasi
                pembelian.update_total()

            # Catat Log
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='UPDATE',
                target_model='Pembelian',
                target_id=pembelian.idPembelian,
                deskripsi=f"Karyawan {karyawan.namaKaryawan} menambahkan {qty} kg buah '{buah.namaBuah}' ke pesanan ID {pembelian.idPembelian}."
            )
            messages.success(request, f"Berhasil menambahkan '{buah.namaBuah}' sebanyak {qty} kg ke dalam pesanan.")
        except Exception as e:
            messages.error(request, f"Gagal menambahkan item buah: {str(e)}")

    return redirect('karyawan_pembelian_list')


@karyawan_required
def hapus_detail_pembelian(request, id_detail):
    detail = get_object_or_404(DetailPembelian, pk=id_detail)
    pembelian = detail.idPembelian
    buah = detail.idBuah
    qty = detail.kuantitas
    try:
        with transaction.atomic():
            detail.delete()
            pembelian.update_total()

        # Catat Log
        karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
        LogAktivitasKaryawan.objects.create(
            idKaryawan=karyawan,
            aksi='UPDATE',
            target_model='Pembelian',
            target_id=pembelian.idPembelian,
            deskripsi=f"Karyawan {karyawan.namaKaryawan} menghapus item {qty} kg buah '{buah.namaBuah}' dari pesanan ID {pembelian.idPembelian}."
        )
        messages.success(request, f"Berhasil menghapus item '{buah.namaBuah}' dari pesanan.")
    except Exception as e:
        messages.error(request, f"Gagal menghapus item buah: {str(e)}")

    return redirect('karyawan_pembelian_list')


@karyawan_required
def pelanggan_create_cepat(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        nama = request.POST.get('namaPelanggan', '').strip()
        alamat = request.POST.get('alamat', '').strip()
        no_hp = request.POST.get('noHp', '').strip()

        if not all([username, password, nama, alamat, no_hp]):
            from django.http import HttpResponse
            return HttpResponse('<option value="" disabled>Data tidak lengkap</option>', status=400)

        if Pelanggan.objects.filter(username=username).exists():
            from django.http import HttpResponse
            return HttpResponse('<option value="" disabled>Username sudah terdaftar</option>', status=400)

        try:
            pelanggan = Pelanggan.objects.create(
                username=username,
                password=password,
                namaPelanggan=nama,
                alamat=alamat,
                noHp=no_hp
            )

            # Catat Log
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='CREATE',
                target_model='Pelanggan',
                target_id=pelanggan.idPelanggan,
                deskripsi=f"Karyawan {karyawan.namaKaryawan} mendaftarkan akun pelanggan cepat: '{pelanggan.namaPelanggan}'."
            )
            
            # Kembalikan string HTML option murni
            from django.http import HttpResponse
            option_html = f'<option value="{pelanggan.idPelanggan}">{pelanggan.namaPelanggan} (HP: {pelanggan.noHp})</option>'
            return HttpResponse(option_html)
        except Exception as e:
            from django.http import HttpResponse
            return HttpResponse(f'<option value="" disabled>Error: {str(e)}</option>', status=500)

    from django.http import HttpResponseNotAllowed
    return HttpResponseNotAllowed(['POST'])
