from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse
from django.contrib.humanize.templatetags.humanize import intcomma
from datetime import datetime

# Create your views here.
from .models import Buah, Pelanggan, Pembelian, DetailPembelian, Pemasok, Pengadaan, DetailPengadaan
from .utils.pdf import generate_pdf


def authenticated_user(request):
    return render(request, 'core/auth.html')


def register_pelanggan(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        nama = request.POST.get('namaPelanggan')
        alamat = request.POST.get('alamat')
        no_hp = request.POST.get('noHp')

        if not all([username, password, nama, alamat, no_hp]):
            messages.error(request, 'Semua field wajib diisi')
            return redirect('auth')

        # Cek username sudah dipakai atau belum
        if Pelanggan.objects.filter(username=username).exists():
            messages.error(request, 'Username sudah digunakan')
            return redirect('auth')

        Pelanggan.objects.create(
            username=username,
            password=password,
            namaPelanggan=nama,
            alamat=alamat,
            noHp=no_hp,
        )
        messages.success(request, 'Registrasi berhasil, silakan login')
        return redirect('auth')

    return redirect('auth')


def login_pelanggan(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        pelanggan = Pelanggan.objects.filter(username=username, password=password).first()
        if pelanggan:
            request.session['pelanggan_id'] = pelanggan.idPelanggan
            request.session['nama_pelanggan'] = pelanggan.namaPelanggan
            messages.success(request, f'Selamat datang, {pelanggan.namaPelanggan}')
            return redirect('index')

        messages.error(request, 'Username atau password salah')
        return redirect('auth')

    return redirect('auth')


def logout_pelanggan(request):
    request.session.pop('pelanggan_id', None)
    request.session.pop('nama_pelanggan', None)
    messages.success(request, 'Anda telah logout')
    return redirect('index')

def index(request):
    bestseller_list = Buah.objects.order_by('-idBuah')[:4]
    return render(request, 'core/home.html', {'bestseller_list': bestseller_list})

def buah(request):
    query = request.GET.get('q', '').strip()
    if query:
        buah_list = Buah.objects.filter(namaBuah__icontains=query)
    else:
        buah_list = Buah.objects.all()
    for b in buah_list:
        if b.diskon:
            b.harga_setelah_diskon = b.hargaBuah - (b.hargaBuah * b.diskon)
            b.diskon_persen = int(b.diskon * 100)
        else:
            b.harga_setelah_diskon = b.hargaBuah
            b.diskon_persen = 0
    return render(request, 'core/buah.html', {'buah_list': buah_list, 'search_query': query})


def tambah_ke_keranjang(request, id_buah):
    cart = request.session.get('cart', {})
    buah_id_str = str(id_buah)
    
    # Ambil quantity dari request (GET atau POST)
    qty_input = request.GET.get('qty') or request.POST.get('qty') or 1
    try:
        quantity_to_add = int(qty_input)
    except (ValueError, TypeError):
        quantity_to_add = 1

    # Stock validation
    try:
        buah_obj = Buah.objects.get(idBuah=id_buah)
    except Buah.DoesNotExist:
        messages.error(request, 'Buah tidak ditemukan')
        return redirect(request.META.get('HTTP_REFERER', 'buah'))

    stok = buah_obj.stokBuah
    current_quantity = cart.get(buah_id_str, 0)
    new_quantity = current_quantity + quantity_to_add

    if stok <= 0:
        messages.error(request, f'Stok {buah_obj.namaBuah} sudah habis')
        return redirect(request.META.get('HTTP_REFERER', 'buah'))

    if new_quantity > stok:
        messages.error(request, f'Stok {buah_obj.namaBuah} tidak mencukupi. Stok tersedia: {stok} kg, di keranjang: {current_quantity} kg')
        return redirect(request.META.get('HTTP_REFERER', 'buah'))

    cart[buah_id_str] = new_quantity
    
    request.session['cart'] = cart
    messages.success(request, f'Berhasil menambahkan {quantity_to_add} item ke keranjang')
    
    # Kembali ke halaman sebelumnya
    return redirect(request.META.get('HTTP_REFERER', 'buah'))


def keranjang(request):
    cart = request.session.get('cart', {})
    buah_ids = [int(bid) for bid in cart.keys()]
    items = []
    total = 0
    has_stock_issue = False

    if buah_ids:
        buah_queryset = Buah.objects.filter(idBuah__in=buah_ids)
        for buah in buah_queryset:
            qty = cart.get(str(buah.idBuah), 0)
            if qty <= 0:
                continue
            harga = buah.hargaBuah
            if buah.diskon:
                harga = harga - (harga * buah.diskon)
            subtotal = harga * qty
            total += subtotal
            diskon_persen = int(buah.diskon * 100) if buah.diskon else 0

            # Check stock availability
            stok = buah.stokBuah
            stok_habis = stok <= 0
            melebihi_stok = qty > stok

            if stok_habis or melebihi_stok:
                has_stock_issue = True

            items.append({
                'buah': buah,
                'qty': qty,
                'harga_setelah_diskon': harga,
                'subtotal': subtotal,
                'diskon_persen': diskon_persen,
                'stok_habis': stok_habis,
                'melebihi_stok': melebihi_stok,
                'stok_tersedia': stok,
            })

    context = {
        'cart_items': items,
        'cart_total': total,
        'has_stock_issue': has_stock_issue,
    }
    return render(request, 'core/cart.html', context)


def hapus_item_keranjang(request, id_buah):
    cart = request.session.get('cart', {})
    buah_id_str = str(id_buah)
    if buah_id_str in cart:
        cart.pop(buah_id_str)
        request.session['cart'] = cart
        messages.success(request, 'Item berhasil dihapus dari keranjang')
    return redirect('keranjang')


def checkout(request):
    if not request.session.get('pelanggan_id'):
        messages.error(request, 'Silakan login terlebih dahulu')
        return redirect('auth')

    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, 'Keranjang belanja masih kosong')
        return redirect('keranjang')

    pelanggan = Pelanggan.objects.get(pk=request.session['pelanggan_id'])

    buah_ids = [int(bid) for bid in cart.keys()]
    items = []
    total = 0
    stock_issues = []

    buah_queryset = Buah.objects.filter(idBuah__in=buah_ids)
    for buah in buah_queryset:
        qty = cart.get(str(buah.idBuah), 0)
        if qty <= 0:
            continue
        harga = buah.hargaBuah
        if buah.diskon:
            harga = harga - (harga * buah.diskon)
        subtotal = harga * qty
        total += subtotal
        diskon_persen = int(buah.diskon * 100) if buah.diskon else 0

        # Check stock availability
        stok = buah.stokBuah
        if stok <= 0:
            stock_issues.append(f'Stok {buah.namaBuah} sudah habis. Silakan hapus dari keranjang.')
        elif qty > stok:
            stock_issues.append(f'Stok {buah.namaBuah} tidak mencukupi. Tersedia: {stok} kg, di keranjang: {qty} kg.')

        items.append({
            'buah': buah,
            'qty': qty,
            'harga_setelah_diskon': harga,
            'subtotal': subtotal,
            'diskon_persen': diskon_persen,
        })

    # Block access to checkout page if stock issues exist
    if stock_issues:
        for issue in stock_issues:
            messages.error(request, issue)
        return redirect('keranjang')

    if request.method == 'POST':
        if not items:
            messages.error(request, 'Keranjang belanja masih kosong')
            return redirect('keranjang')

        # Re-validate stock right before creating order (prevent race condition)
        recheck_issues = []
        for item in items:
            buah = Buah.objects.get(pk=item['buah'].idBuah)
            stok = buah.stokBuah
            if stok <= 0:
                recheck_issues.append(f'Stok {buah.namaBuah} sudah habis.')
            elif item['qty'] > stok:
                recheck_issues.append(f'Stok {buah.namaBuah} tidak mencukupi. Tersedia: {stok} kg, di keranjang: {item["qty"]} kg.')

        if recheck_issues:
            for issue in recheck_issues:
                messages.error(request, issue)
            return redirect('keranjang')

        alamat_pengiriman = request.POST.get('alamat')
        metode_bayar = request.POST.get('metode_bayar')
        bukti_bayar = request.FILES.get('buktiBayar')

        pembelian = Pembelian.objects.create(
            idPelanggan=pelanggan,
            alamatPengiriman=alamat_pengiriman if alamat_pengiriman else pelanggan.alamat,
            metodeBayar=metode_bayar,
            buktiBayar=bukti_bayar if metode_bayar != 'COD' else None
        )

        for item in items:
            DetailPembelian.objects.create(
                idPembelian=pembelian,
                idBuah=item['buah'],
                kuantitas=item['qty'],
            )

        pembelian.update_total()

        request.session.pop('cart', None)
        messages.success(request, 'Order berhasil dibuat')
        return redirect('shop-detail')

    context = {
        'cart_items': items,
        'cart_total': total,
        'pelanggan': pelanggan,
    }
    return render(request, 'core/chackout.html', context)


def kontak(request):
    return render(request, 'core/contact.html')


def shop_detail(request):
    if not request.session.get('pelanggan_id'):
        messages.error(request, 'Silakan login terlebih dahulu untuk melihat riwayat')
        return redirect('auth')
    
    pelanggan_id = request.session['pelanggan_id']
    riwayat_pembelian = Pembelian.objects.filter(idPelanggan=pelanggan_id).prefetch_related('detailpembelian_set', 'detailpembelian_set__idBuah').order_by('-tanggalPembelian')
    
    return render(request, 'core/shop-detail.html', {'riwayat_pembelian': riwayat_pembelian})


def update_cart(request, id_buah, action):
    cart = request.session.get('cart', {})
    buah_id_str = str(id_buah)
    
    if buah_id_str in cart:
        if action == 'tambah':
            # Stock validation before incrementing
            try:
                buah_obj = Buah.objects.get(idBuah=id_buah)
                stok = buah_obj.stokBuah
                if cart[buah_id_str] + 1 > stok:
                    messages.error(request, f'Stok {buah_obj.namaBuah} tidak mencukupi. Stok tersedia: {stok} kg')
                    return redirect('keranjang')
            except Buah.DoesNotExist:
                pass
            cart[buah_id_str] += 1
        elif action == 'kurang':
            cart[buah_id_str] -= 1
            if cart[buah_id_str] <= 0:
                cart.pop(buah_id_str)
        
        request.session['cart'] = cart
    
    return redirect('keranjang')


# ======================================================
# REPORTING SYSTEM (MENU -> PREVIEW -> CETAK)
# ======================================================
@staff_member_required
def laporan_dashboard(request):
    """Dashboard untuk memilih jenis laporan yang ingin dibuat."""
    return render(request, 'core/admin/laporan_dashboard.html')


@staff_member_required
def preview_laporan(request, tipe):
    """
    Fungsi universal untuk preview laporan dengan filter.
    Tipe yang didukung: 'buah', 'pelanggan', 'pembelian', 'pemasok', 'pengadaan'
    """
    # Ambil filter dari GET request
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    status_filter = request.GET.get('status', '')
    
    # Konfigurasi berdasarkan tipe laporan
    config = {
        'buah': {
            'title': 'Laporan Data Buah',
            'model': Buah,
            'columns': ['Nama Buah', 'Harga', 'Stok', 'Diskon', 'Kadaluarsa'],
            'date_field': None,
        },
        'pelanggan': {
            'title': 'Laporan Data Pelanggan',
            'model': Pelanggan,
            'columns': ['Nama', 'Username', 'No HP', 'Alamat'],
            'date_field': None,
        },
        'pembelian': {
            'title': 'Laporan Pembelian',
            'model': Pembelian,
            'columns': ['ID', 'Pelanggan', 'Total Buah', 'Total Harga', 'Status', 'Tanggal'],
            'date_field': 'tanggalPembelian',
        },
        'pemasok': {
            'title': 'Laporan Data Pemasok',
            'model': Pemasok,
            'columns': ['Nama', 'No HP', 'Alamat'],
            'date_field': None,
        },
        'pengadaan': {
            'title': 'Laporan Pengadaan',
            'model': Pengadaan,
            'columns': ['ID', 'Pemasok', 'Total Harga', 'Tanggal'],
            'date_field': 'detailpengadaan__tanggalMasuk',
        },
    }
    
    if tipe not in config:
        messages.error(request, 'Tipe laporan tidak valid')
        return redirect('admin:index')
    
    cfg = config[tipe]
    queryset = cfg['model'].objects.all()
    
    # Terapkan filter tanggal jika ada
    if cfg['date_field'] and start_date and end_date:
        if tipe == 'pengadaan':
            queryset = queryset.filter(
                **{f"{cfg['date_field']}__range": (start_date, end_date)}
            ).distinct()
        else:
            queryset = queryset.filter(
                **{f"{cfg['date_field']}__date__range": (start_date, end_date)}
            )
    
    # Terapkan filter status untuk pembelian
    if tipe == 'pembelian' and status_filter:
        queryset = queryset.filter(statusPembelian=status_filter)
    
    # Format data untuk ditampilkan di template
    data_rows = []
    if tipe == 'buah':
        for obj in queryset:
            data_rows.append([
                obj.namaBuah,
                f"Rp {intcomma(obj.hargaBuah)}",
                obj.stokBuah,
                f"{obj.diskon * 100:.0f}%" if obj.diskon else "0%",
                obj.tanggalKadaluarsa or "-"
            ])
    elif tipe == 'pelanggan':
        for obj in queryset:
            data_rows.append([
                obj.namaPelanggan,
                obj.username,
                obj.noHp,
                obj.alamat
            ])
    elif tipe == 'pembelian':
        for obj in queryset:
            data_rows.append([
                obj.idPembelian,
                obj.idPelanggan.namaPelanggan,
                obj.totalBuah,
                f"Rp {intcomma(obj.totalHargaPembelian)}",
                obj.statusPembelian,
                obj.tanggalPembelian.strftime('%Y-%m-%d %H:%M')
            ])
    elif tipe == 'pemasok':
        for obj in queryset:
            data_rows.append([
                obj.namaPemasok,
                obj.noHp,
                obj.alamat
            ])
    elif tipe == 'pengadaan':
        for obj in queryset:
            detail = obj.detailpengadaan_set.order_by('tanggalMasuk').first()
            tanggal = detail.tanggalMasuk.strftime('%d/%m/%Y') if detail else '-'
            data_rows.append([
                obj.idPengadaan,
                obj.idPemasok.namaPemasok,
                f"Rp {intcomma(obj.totalHarga)}",
                tanggal
            ])
    
    # Generate judul dinamis
    title = cfg['title']
    if start_date and end_date:
        title += f" ({start_date} s/d {end_date})"
    
    # Status choices untuk filter dropdown pembelian
    status_choices = ['Menunggu', 'Diproses', 'Selesai', 'Dibatalkan']
    
    context = {
        'tipe': tipe,
        'title': title,
        'columns': cfg['columns'],
        'data_rows': data_rows,
        'start_date': start_date,
        'end_date': end_date,
        'show_date_filter': cfg['date_field'] is not None,
        'status_filter': status_filter,
        'status_choices': status_choices if tipe == 'pembelian' else [],
    }
    
    return render(request, 'core/admin/report_preview.html', context)


@staff_member_required
def cetak_laporan_final(request, tipe):
    """
    Fungsi untuk mengunduh laporan dalam format PDF.
    """
    # Ambil filter dari GET request
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    status_filter = request.GET.get('status', '')
    
    # Konfigurasi berdasarkan tipe laporan (sama seperti preview)
    config = {
        'buah': {
            'title': 'LAPORAN DATA BUAH',
            'model': Buah,
            'columns': ['Nama', 'Harga', 'Stok', 'Diskon', 'Kadaluarsa'],
            'date_field': None,
            'filename': 'laporan_buah.pdf'
        },
        'pelanggan': {
            'title': 'LAPORAN DATA PELANGGAN',
            'model': Pelanggan,
            'columns': ['Nama', 'Username', 'No HP', 'Alamat'],
            'date_field': None,
            'filename': 'laporan_pelanggan.pdf'
        },
        'pembelian': {
            'title': 'LAPORAN PEMBELIAN',
            'model': Pembelian,
            'columns': ['ID', 'Pelanggan', 'Total Buah', 'Total Harga', 'Status', 'Tanggal'],
            'date_field': 'tanggalPembelian',
            'filename': 'laporan_pembelian.pdf'
        },
        'pemasok': {
            'title': 'LAPORAN DATA PEMASOK',
            'model': Pemasok,
            'columns': ['Nama', 'No HP', 'Alamat'],
            'date_field': None,
            'filename': 'laporan_pemasok.pdf'
        },
        'pengadaan': {
            'title': 'LAPORAN PENGADAAN',
            'model': Pengadaan,
            'columns': ['ID', 'Pemasok', 'Total Harga', 'Tanggal'],
            'date_field': 'detailpengadaan__tanggalMasuk',
            'filename': 'laporan_pengadaan.pdf'
        },
    }
    
    if tipe not in config:
        messages.error(request, 'Tipe laporan tidak valid')
        return redirect('admin:index')
    
    cfg = config[tipe]
    queryset = cfg['model'].objects.all()
    
    # Terapkan filter tanggal jika ada
    if cfg['date_field'] and start_date and end_date:
        if tipe == 'pengadaan':
            queryset = queryset.filter(
                **{f"{cfg['date_field']}__range": (start_date, end_date)}
            ).distinct()
        else:
            queryset = queryset.filter(
                **{f"{cfg['date_field']}__date__range": (start_date, end_date)}
            )
    
    # Terapkan filter status untuk pembelian
    if tipe == 'pembelian' and status_filter:
        queryset = queryset.filter(statusPembelian=status_filter)
    
    # Siapkan data untuk PDF
    data = [cfg['columns']]
    
    if tipe == 'buah':
        for obj in queryset:
            data.append([
                obj.namaBuah,
                f"Rp {intcomma(obj.hargaBuah)}",
                obj.stokBuah,
                f"{obj.diskon * 100:.0f}%" if obj.diskon else "0%",
                obj.tanggalKadaluarsa or "-"
            ])
    elif tipe == 'pelanggan':
        for obj in queryset:
            data.append([
                obj.namaPelanggan,
                obj.username,
                obj.noHp,
                obj.alamat
            ])
    elif tipe == 'pembelian':
        for obj in queryset:
            data.append([
                obj.idPembelian,
                obj.idPelanggan.namaPelanggan,
                obj.totalBuah,
                f"Rp {intcomma(obj.totalHargaPembelian)}",
                obj.statusPembelian,
                obj.tanggalPembelian.strftime('%Y-%m-%d')
            ])
    elif tipe == 'pemasok':
        for obj in queryset:
            data.append([
                obj.namaPemasok,
                obj.noHp,
                obj.alamat
            ])
    elif tipe == 'pengadaan':
        for obj in queryset:
            detail = obj.detailpengadaan_set.order_by('tanggalMasuk').first()
            tanggal = detail.tanggalMasuk.strftime('%d/%m/%Y') if detail else '-'
            data.append([
                obj.idPengadaan,
                obj.idPemasok.namaPemasok,
                f"Rp {intcomma(obj.totalHarga)}",
                tanggal
            ])
    
    # Generate judul dengan rentang tanggal jika ada
    title = cfg['title']
    if start_date and end_date:
        title += f" {start_date} - {end_date}"
    
    # Generate PDF
    user_name = request.user.get_full_name() or request.user.username
    pdf_buffer = generate_pdf(title, data, generated_by=user_name)
    return FileResponse(pdf_buffer, as_attachment=True, filename=cfg['filename'])