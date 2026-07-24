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
    ProfilToko, CatatanKerusakan, ProdukOlahan, PenjualanOlahan
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

    from datetime import date
    from django.db.models import Sum

    today = date.today()
    kerugian_bulan_ini = CatatanKerusakan.objects.filter(
        tanggalDicatat__year=today.year,
        tanggalDicatat__month=today.month
    ).aggregate(total=Sum('nilai_kerugian'))['total'] or 0

    pendapatan_olahan = ProdukOlahan.objects.filter(
        tanggal__year=today.year,
        tanggal__month=today.month
    ).aggregate(total=Sum('total_pendapatan'))['total'] or 0

    from django.db.models import Q
    stok_bermasalah = DetailPengadaan.objects.filter(
        Q(qty_hampir_rusak__gt=0) | Q(qty_rusak__gt=0), status=True
    ).count()

    context = {
        'karyawan': karyawan,
        'total_buah': total_buah,
        'total_pembelian': total_pembelian,
        'total_pelanggan': total_pelanggan,
        'logs': logs,
        'kerugian_bulan_ini': kerugian_bulan_ini,
        'pendapatan_olahan': pendapatan_olahan,
        'stok_bermasalah': stok_bermasalah,
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


# ──────────────────────────────────────────────────────────────



@karyawan_required
def buah_detail(request, id_buah):
    """Halaman detail buah: lihat & kelola semua batch per grade."""
    buah = get_object_or_404(Buah, pk=id_buah)
    from datetime import date

    batches = buah.detail_pengadaan.all().order_by('status', 'tanggalMasuk')

    batch_data = []
    for b in batches:
        hari_berjalan = (date.today() - b.tanggalMasuk).days
        sisa_hari = buah.lamaKesegaraan - hari_berjalan
        batch_data.append({
            'batch': b,
            'hari_berjalan': hari_berjalan,
            'sisa_hari': sisa_hari,
        })

    context = {
        'buah': buah,
        'batch_data': batch_data,
    }
    return render(request, 'core/karyawan/buah_detail.html', context)


@karyawan_required
def buah_create(request):
    if request.method == 'POST':
        nama = request.POST.get('namaBuah', '').strip()
        harga = request.POST.get('hargaBuah', '').strip()
        deskripsi = request.POST.get('deskripsiBuah', '').strip()
        lama_kesegaran = request.POST.get('lamaKesegaraan', '').strip()
        foto = request.FILES.get('fotoBuah')

        if not all([nama, harga, deskripsi, lama_kesegaran, foto]):
            messages.error(request, 'Semua kolom data buah wajib diisi beserta foto buah.')
            return redirect('karyawan_buah_list')

        try:
            buah = Buah.objects.create(
                namaBuah=nama,
                hargaBuah=float(harga),
                deskripsiBuah=deskripsi,
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
        'logo_url': logo_url,
        # Data jasa kirim & ongkos kirim
        'jasa_kirim': pembelian.jasa_kirim or '',
        'nama_kurir': pembelian.nama_kurir or '',
        'ongkos_kirim': float(pembelian.ongkos_kirim),
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

        # Field baru: jasa kirim & ongkos kirim
        jasa_kirim = request.POST.get('jasa_kirim')
        nama_kurir = request.POST.get('nama_kurir')
        ongkos_kirim_str = request.POST.get('ongkos_kirim', '').replace(',', '.')

        if not alamat or not status:
            messages.error(request, 'Alamat pengiriman dan Status wajib diisi.')
            return redirect('karyawan_pembelian_list')

        try:
            old_status = pembelian.statusPembelian

            pembelian.metodeBayar = metode_bayar
            pembelian.alamatPengiriman = alamat
            pembelian.statusPembelian = status
            
            if jasa_kirim:
                pembelian.jasa_kirim = jasa_kirim.strip()
            if nama_kurir:
                pembelian.nama_kurir = nama_kurir.strip()
            if ongkos_kirim_str and ongkos_kirim_str.strip() != '':
                try:
                    pembelian.ongkos_kirim = float(ongkos_kirim_str.strip())
                except ValueError:
                    pass

            if bukti:
                pembelian.buktiBayar = bukti

            pembelian.save()

            # Catat Log
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])

            status_desc = f"dari '{old_status}' menjadi '{status}'" if old_status != status else f"status '{status}'"
            ongkir_desc = f", ongkir {pembelian.jasa_kirim} Rp {pembelian.ongkos_kirim}" if pembelian.ongkos_kirim > 0 else ""
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='UPDATE',
                target_model='Pembelian',
                target_id=pembelian.idPembelian,
                deskripsi=f"Karyawan {karyawan.namaKaryawan} memperbarui data pesanan ID {pembelian.idPembelian} ({status_desc}{ongkir_desc})."
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

# ======================================================
# FITUR BARU: MANAJEMEN GRADE, KERUSAKAN, OLAHAN
# ======================================================
@karyawan_required
def update_qty_batch(request, id_detail):
    if request.method == 'POST':
        batch = get_object_or_404(DetailPengadaan, pk=id_detail)
        qty_segar = int(request.POST.get('qty_segar', batch.qty_segar))
        qty_menengah = int(request.POST.get('qty_menengah', batch.qty_menengah))
        qty_hampir_rusak = int(request.POST.get('qty_hampir_rusak', batch.qty_hampir_rusak))
        qty_rusak = int(request.POST.get('qty_rusak', batch.qty_rusak))
        
        batch.qty_segar = qty_segar
        batch.qty_menengah = qty_menengah
        batch.qty_hampir_rusak = qty_hampir_rusak
        batch.qty_rusak = qty_rusak
        
        if batch.kuantitas == 0:
            batch.status = False
        else:
            batch.status = True
            
        batch.save(update_fields=['qty_segar', 'qty_menengah', 'qty_hampir_rusak', 'qty_rusak', 'status'])
        
        karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
        LogAktivitasKaryawan.objects.create(
            idKaryawan=karyawan,
            aksi='UPDATE',
            target_model='DetailPengadaan',
            target_id=batch.pk,
            deskripsi=f"Mengupdate alokasi qty grade batch ID {batch.pk}."
        )
        messages.success(request, f"Alokasi kuantitas batch berhasil diperbarui.")
    return redirect('karyawan_buah_detail', id_buah=batch.idBuah.idBuah)

@karyawan_required
def catat_kerusakan(request, id_detail):
    if request.method == 'POST':
        batch = get_object_or_404(DetailPengadaan, pk=id_detail)
        qty_rusak = int(request.POST.get('qty_rusak', 0))
        alasan = request.POST.get('alasan')
        grade_target = request.POST.get('grade_target')
        
        valid_grades = ['qty_segar', 'qty_menengah', 'qty_hampir_rusak', 'qty_rusak']
        
        if grade_target in valid_grades:
            stok_grade = getattr(batch, grade_target)
            if 0 < qty_rusak <= stok_grade:
                karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
                kerusakan = CatatanKerusakan.objects.create(
                    idDetailPengadaan=batch,
                    qty_rusak=qty_rusak,
                    alasan=alasan,
                    idKaryawan=karyawan
                )
                
                # Kurangi stok berdasarkan grade_target
                setattr(batch, grade_target, stok_grade - qty_rusak)
                if batch.stok_sisa == 0:
                    batch.status = False
                batch.save(update_fields=[grade_target, 'status'])
                
                LogAktivitasKaryawan.objects.create(
                    idKaryawan=karyawan,
                    aksi='CREATE',
                    target_model='CatatanKerusakan',
                    target_id=kerusakan.pk,
                    deskripsi=f"Mencatat kerusakan {qty_rusak}kg buah {batch.idBuah.namaBuah} dari {grade_target} (alasan: {alasan})."
                )
                messages.success(request, f"Kerusakan {qty_rusak}kg berhasil dicatat dari grade yang dipilih.")
            else:
                messages.error(request, "Jumlah tidak valid atau melebihi stok grade yang dipilih.")
        else:
            messages.error(request, "Silakan pilih sumber grade yang valid.")
    return redirect('karyawan_buah_list')

@karyawan_required
def catat_olahan(request, id_detail):
    if request.method == 'POST':
        batch = get_object_or_404(DetailPengadaan, pk=id_detail)
        nama_produk = request.POST.get('nama_produk')
        qty_bahan_dipakai = int(request.POST.get('qty_bahan_dipakai', 0))
        qty_produk_jadi = int(request.POST.get('qty_produk_jadi', 0))
        harga_jual_per_unit = request.POST.get('harga_jual_per_unit', 0)
        
        if 0 < qty_bahan_dipakai <= batch.kuantitas and qty_produk_jadi > 0:
            from datetime import date
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
            olahan = ProdukOlahan.objects.create(
                idDetailPengadaan=batch,
                nama_produk=nama_produk,
                qty_bahan_dipakai=qty_bahan_dipakai,
                qty_produk_jadi=qty_produk_jadi,
                harga_jual_per_unit=harga_jual_per_unit,
                tanggal=date.today(),
                idKaryawan=karyawan
            )
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='CREATE',
                target_model='ProdukOlahan',
                target_id=olahan.pk,
                deskripsi=f"Mencatat olahan '{nama_produk}' menggunakan {qty_bahan_dipakai}kg {batch.idBuah.namaBuah}."
            )
            messages.success(request, f"Produk olahan '{nama_produk}' berhasil dicatat.")
        else:
            messages.error(request, "Input tidak valid, pastikan stok bahan mencukupi.")
    return redirect('karyawan_buah_list')

# ======================================================
# CRUD PRODUK OLAHAN
# ======================================================
@karyawan_required
def olahan_list(request):
    q = request.GET.get('q', '').strip()
    
    olahan_items = ProdukOlahan.objects.select_related('idDetailPengadaan__idBuah').order_by('-tanggal')
    if q:
        olahan_items = olahan_items.filter(Q(nama_produk__icontains=q) | Q(idDetailPengadaan__idBuah__namaBuah__icontains=q))
        
    batches = DetailPengadaan.objects.filter(status=True, qty_hampir_rusak__gt=0).select_related('idBuah')
        
    context = {
        'olahan_items': olahan_items,
        'q': q,
        'batches': batches,
    }
    return render(request, 'core/karyawan/olahan_list.html', context)

@karyawan_required
def olahan_create(request):
    if request.method == 'POST':
        try:
            id_detail = request.POST.get('idDetailPengadaan')
            batch = get_object_or_404(DetailPengadaan, pk=id_detail)
            nama_produk = request.POST.get('nama_produk')
            qty_bahan = int(request.POST.get('qty_bahan_dipakai', 0))
            qty_hasil = int(request.POST.get('qty_produk_jadi', 0))
            harga_jual = int(request.POST.get('harga_jual_per_unit', 0))
            
            olahan = ProdukOlahan(
                idDetailPengadaan=batch,
                nama_produk=nama_produk,
                qty_bahan_dipakai=qty_bahan,
                qty_produk_jadi=qty_hasil,
                harga_jual_per_unit=harga_jual
            )
            olahan.full_clean()
            olahan.save()
            
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='CREATE',
                target_model='ProdukOlahan',
                target_id=olahan.pk,
                deskripsi=f"Menambahkan produk olahan {nama_produk} ({qty_hasil} unit)."
            )
            messages.success(request, f"Produk Olahan {nama_produk} berhasil ditambahkan.")
        except ValidationError as e:
            messages.error(request, str(e.message_dict if hasattr(e, 'message_dict') else e))
        except Exception as e:
            messages.error(request, f"Gagal menambahkan: {str(e)}")
            
    return redirect('karyawan_olahan_list')

@karyawan_required
def olahan_update(request, id_olahan):
    olahan = get_object_or_404(ProdukOlahan, pk=id_olahan)
    if request.method == 'POST':
        try:
            olahan.nama_produk = request.POST.get('nama_produk')
            # qty_bahan_dipakai usually shouldn't be edited easily because it affects stock deduction. We'll skip editing bahan qty for simplicity/safety unless necessary, but let's allow qty_produk_jadi and harga.
            olahan.qty_produk_jadi = int(request.POST.get('qty_produk_jadi', olahan.qty_produk_jadi))
            olahan.harga_jual_per_unit = int(request.POST.get('harga_jual_per_unit', olahan.harga_jual_per_unit))
            olahan.save()
            
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='UPDATE',
                target_model='ProdukOlahan',
                target_id=olahan.pk,
                deskripsi=f"Mengubah data produk olahan {olahan.nama_produk}."
            )
            messages.success(request, f"Produk Olahan {olahan.nama_produk} berhasil diperbarui.")
        except Exception as e:
            messages.error(request, f"Gagal memperbarui: {str(e)}")
            
    return redirect('karyawan_olahan_list')

@karyawan_required
def olahan_delete(request, id_olahan):
    olahan = get_object_or_404(ProdukOlahan, pk=id_olahan)
    if request.method == 'POST':
        nama = olahan.nama_produk
        
        # Restore stock logic if needed, but standard django delete on ProdukOlahan doesn't restore stock unless programmed. Let's just delete.
        olahan.delete()
        
        karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
        LogAktivitasKaryawan.objects.create(
            idKaryawan=karyawan,
            aksi='DELETE',
            target_model='ProdukOlahan',
            target_id=id_olahan,
            deskripsi=f"Menghapus produk olahan {nama}."
        )
        messages.success(request, f"Produk Olahan {nama} berhasil dihapus.")
    return redirect('karyawan_olahan_list')


# ======================================================
# CRUD PENJUALAN OLAHAN
# ======================================================
@karyawan_required
def penjualan_list(request):
    q = request.GET.get('q', '').strip()
    
    penjualan_items = PenjualanOlahan.objects.select_related('idProdukOlahan').order_by('-tanggal')
    if q:
        penjualan_items = penjualan_items.filter(Q(nama_pelanggan__icontains=q) | Q(idProdukOlahan__nama_produk__icontains=q) | Q(pencatat__icontains=q))
        
    olahans = ProdukOlahan.objects.filter(qty_produk_jadi__gt=0)
        
    context = {
        'penjualan_items': penjualan_items,
        'q': q,
        'olahans': olahans,
    }
    return render(request, 'core/karyawan/penjualan_list.html', context)

@karyawan_required
def penjualan_create(request):
    if request.method == 'POST':
        try:
            id_olahan = request.POST.get('idProdukOlahan')
            olahan = get_object_or_404(ProdukOlahan, pk=id_olahan)
            nama_pelanggan = request.POST.get('nama_pelanggan', '')
            qty = int(request.POST.get('qty', 0))
            
            # The model's clean() method will handle validation (stok tak mencukupi)
            # The model's save() method will handle deducting stok
            penjualan = PenjualanOlahan(
                idProdukOlahan=olahan,
                nama_pelanggan=nama_pelanggan,
                qty=qty,
                pencatat=request.session.get('karyawan_nama', 'Sistem')
            )
            penjualan.full_clean()
            penjualan.save()
            
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='CREATE',
                target_model='PenjualanOlahan',
                target_id=penjualan.pk,
                deskripsi=f"Mencatat penjualan {qty} unit {olahan.nama_produk} ke {nama_pelanggan}."
            )
            messages.success(request, f"Penjualan {olahan.nama_produk} berhasil dicatat.")
        except ValidationError as e:
            # e is a ValidationError dict or list
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Gagal mencatat penjualan: {str(e)}")
            
    return redirect('karyawan_penjualan_list')

@karyawan_required
def penjualan_update(request, id_penjualan):
    penjualan = get_object_or_404(PenjualanOlahan, pk=id_penjualan)
    if request.method == 'POST':
        try:
            penjualan.nama_pelanggan = request.POST.get('nama_pelanggan', penjualan.nama_pelanggan)
            # Not updating qty directly via Karyawan UI to avoid complex restock math unless necessary.
            penjualan.save(update_fields=['nama_pelanggan'])
            
            karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
            LogAktivitasKaryawan.objects.create(
                idKaryawan=karyawan,
                aksi='UPDATE',
                target_model='PenjualanOlahan',
                target_id=penjualan.pk,
                deskripsi=f"Mengubah data penjualan #{penjualan.pk}."
            )
            messages.success(request, f"Data penjualan berhasil diperbarui.")
        except Exception as e:
            messages.error(request, f"Gagal memperbarui: {str(e)}")
            
    return redirect('karyawan_penjualan_list')

@karyawan_required
def penjualan_delete(request, id_penjualan):
    penjualan = get_object_or_404(PenjualanOlahan, pk=id_penjualan)
    if request.method == 'POST':
        
        # Restore stock of olahan
        olahan = penjualan.idProdukOlahan
        olahan.qty_produk_jadi += penjualan.qty
        olahan.save(update_fields=['qty_produk_jadi'])
        
        penjualan.delete()
        
        karyawan = Karyawan.objects.get(pk=request.session['karyawan_id'])
        LogAktivitasKaryawan.objects.create(
            idKaryawan=karyawan,
            aksi='DELETE',
            target_model='PenjualanOlahan',
            target_id=id_penjualan,
            deskripsi=f"Menghapus penjualan #{id_penjualan}."
        )
        messages.success(request, f"Penjualan berhasil dihapus dan stok dikembalikan.")
    return redirect('karyawan_penjualan_list')

