from django.contrib import admin
from django import forms
from django.contrib.auth.models import Group
from django.http import FileResponse
from django.shortcuts import render
from django.contrib.humanize.templatetags.humanize import intcomma
from datetime import date, timedelta
from django.utils.functional import SimpleLazyObject
from django.utils.safestring import mark_safe
from django.urls import reverse
admin.site.unregister(Group)

from .models import (
    Buah, Pelanggan,
    Pembelian, DetailPembelian,
    Pemasok, Pengadaan, DetailPengadaan,
    Karyawan, LogAktivitasKaryawan,
    ProfilToko
)
from .utils.pdf import generate_pdf

# ======================================================
# HELPER: CUSTOM ACTIONS COLUMN
# ======================================================
def get_show_actions(obj, model_name):
    edit_url = reverse(f'admin:core_{model_name}_change', args=[obj.pk])
    delete_url = reverse(f'admin:core_{model_name}_delete', args=[obj.pk])
    return mark_safe(f'''
        <a href="{edit_url}" class="button btn-sm btn-warning text-white" style="background: #ffc107; padding: 2px 8px; border-radius: 4px;" title="Edit"><i class="fa fa-edit"></i></a>
        <a href="{edit_url}" class="button btn-sm btn-info text-white" style="background: #17a2b8; padding: 2px 8px; border-radius: 4px;" title="Detail"><i class="fa fa-eye"></i></a>
        <a href="{delete_url}" class="button btn-sm btn-danger text-white" style="background: #dc3545; padding: 2px 8px; border-radius: 4px;" title="Hapus"><i class="fa fa-trash"></i></a>
    ''')

# ======================================================
# USING DEFAULT DJANGO ADMIN
# ======================================================


# ======================================================
# UNREGISTER GROUP
# ======================================================
# custom_admin_site.unregister(Group)


# ======================================================
# BUAH
# ======================================================
@admin.register(Buah)
class BuahAdmin(admin.ModelAdmin):
    list_display = ("namaBuah", "harga_rupiah", "stokBuah", "stok_segar", "stok_menengah", "stok_hampir_rusak", "stok_rusak", "show_actions")
    search_fields = ("namaBuah",)
    list_filter = ("lamaKesegaraan",)
    actions = ["export_pdf"]

    def stok_segar(self, obj):
        return f"{obj.stokPerGrade.get('segar', 0)} kg"
    stok_segar.short_description = "Segar"

    def stok_menengah(self, obj):
        return f"{obj.stokPerGrade.get('menengah', 0)} kg"
    stok_menengah.short_description = "Menengah"

    def stok_hampir_rusak(self, obj):
        return f"{obj.stokPerGrade.get('hampir_rusak', 0)} kg"
    stok_hampir_rusak.short_description = "Hampir Rusak"

    def stok_rusak(self, obj):
        return f"{obj.stokPerGrade.get('rusak', 0)} kg"
    stok_rusak.short_description = "Rusak"

    def show_actions(self, obj):
        return get_show_actions(obj, 'buah')
    show_actions.short_description = "Aksi"

    def harga_rupiah(self, obj):
        return f"Rp {intcomma(obj.hargaBuah)}"
    harga_rupiah.short_description = "Harga"

    def export_pdf(self, request, queryset):
        data = [["Nama", "Harga", "Stok", "Kadaluarsa"]]
        for b in queryset:
            data.append([
                b.namaBuah,
                f"Rp {intcomma(b.hargaBuah)}",
                b.stokBuah,
                b.tanggalKadaluarsa or "-"
            ])
        user_name = request.user.get_full_name() or request.user.username
        pdf_buffer = generate_pdf("LAPORAN DATA BUAH", data, generated_by=user_name)
        return FileResponse(pdf_buffer, as_attachment=True, filename="laporan_buah.pdf")
    export_pdf.short_description = "Cetak Laporan PDF"


# ======================================================
# PELANGGAN
# ======================================================
@admin.register(Pelanggan)
class PelangganAdmin(admin.ModelAdmin):
    list_display = ("namaPelanggan", "username", "noHp", "alamat", "show_actions")
    search_fields = ("namaPelanggan", "username", "noHp", "alamat")
    list_filter = ("alamat",)
    actions = ["export_pdf"]

    def show_actions(self, obj):
        return get_show_actions(obj, 'pelanggan')
    show_actions.short_description = "Aksi"

    def export_pdf(self, request, queryset):
        data = [["Nama", "Username", "No HP", "Alamat"]]
        for p in queryset:
            data.append([p.namaPelanggan, p.username, p.noHp, p.alamat])
        user_name = request.user.get_full_name() or request.user.username
        pdf_buffer = generate_pdf("LAPORAN DATA PELANGGAN", data, generated_by=user_name)
        return FileResponse(pdf_buffer, as_attachment=True, filename="laporan_pelanggan.pdf")


# ======================================================
# PEMBELIAN
# ======================================================
from .forms import DetailPembelianForm

class DetailPembelianInline(admin.TabularInline):
    model = DetailPembelian
    form = DetailPembelianForm
    extra = 1


@admin.register(Pembelian)
class PembelianAdmin(admin.ModelAdmin):
    list_display = (
        "nama_pelanggan", "totalBuah", "total_harga_rupiah",
        "statusPembelian", "jasa_kirim", "ongkir_rupiah", "tanggalPembelian",
        "cetak_struk_admin", "show_actions"
    )
    inlines = [DetailPembelianInline]
    list_filter = ("statusPembelian", "metodeBayar", "jasa_kirim", ("tanggalPembelian", admin.DateFieldListFilter))
    list_editable = ("statusPembelian",)
    actions = ["export_pdf", "export_pdf_by_date"]
    readonly_fields = ("tanggalPembelian",)
    fieldsets = (
        ('Informasi Pesanan', {
            'fields': ('idPelanggan', 'statusPembelian', 'metodeBayar', 'alamatPengiriman', 'buktiBayar', 'tanggalPembelian')
        }),
        ('Pengiriman', {
            'fields': ('jasa_kirim', 'nama_kurir', 'ongkos_kirim'),
            'description': 'Isi info pengiriman setelah pesanan masuk. Ongkos kirim dibayar cash oleh pelanggan langsung ke kurir.'
        }),
    )

    def show_actions(self, obj):
        return get_show_actions(obj, 'pembelian')
    show_actions.short_description = "Aksi"

    def cetak_struk_admin(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('karyawan_cetak_print', args=[obj.pk])
        return format_html(
            '<a href="{}" target="_blank" class="button" style="background: #17a2b8; color: white; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-weight: bold; white-space: nowrap;"><i class="fa fa-print"></i> Cetak</a>',
            url
        )
    cetak_struk_admin.short_description = "Struk"

    def nama_pelanggan(self, obj):
        return obj.idPelanggan.namaPelanggan

    def total_harga_rupiah(self, obj):
        return f"Rp {intcomma(obj.totalHargaPembelian)}"
    total_harga_rupiah.short_description = "Total Harga Buah"

    def ongkir_rupiah(self, obj):
        if obj.ongkos_kirim and obj.ongkos_kirim > 0:
            kurir = f" ({obj.jasa_kirim})" if obj.jasa_kirim else ""
            return f"Rp {intcomma(obj.ongkos_kirim)}{kurir}"
        return "-"
    ongkir_rupiah.short_description = "Ongkir"

    def export_pdf(self, request, queryset):
        data = [["ID", "Pelanggan", "Total Buah", "Total Harga", "Status", "Tanggal"]]
        for pb in queryset:
            data.append([
                pb.idPembelian,
                pb.idPelanggan.namaPelanggan,
                pb.totalBuah,
                f"Rp {intcomma(pb.totalHargaPembelian)}",
                pb.statusPembelian,
                pb.tanggalPembelian
            ])
        user_name = request.user.get_full_name() or request.user.username
        pdf_buffer = generate_pdf("LAPORAN PEMBELIAN", data, generated_by=user_name)
        return FileResponse(pdf_buffer, as_attachment=True, filename="laporan_pembelian.pdf")

    def export_pdf_by_date(self, request, queryset):
        if "start_date" in request.POST and "end_date" in request.POST:
            start = request.POST["start_date"]
            end = request.POST["end_date"]
            qs = Pembelian.objects.filter(
                tanggalPembelian__date__range=(start, end)
            )

            data = [["ID", "Pelanggan", "Total", "Status", "Tanggal"]]
            for pb in qs:
                data.append([
                    pb.idPembelian,
                    pb.idPelanggan.namaPelanggan,
                    f"Rp {intcomma(pb.totalHargaPembelian)}",
                    pb.statusPembelian,
                    pb.tanggalPembelian
                ])

            user_name = request.user.get_full_name() or request.user.username
            pdf = generate_pdf(f"LAPORAN PEMBELIAN {start} - {end}", data, generated_by=user_name)
            return FileResponse(pdf, as_attachment=True, filename="laporan_pembelian_rentang.pdf")

        return render(request, "core/admin/pembelian/date_range_form.html")
    export_pdf_by_date.short_description = "Cetak Laporan (Rentang Tanggal)"


# ======================================================
# PEMASOK
# ======================================================
@admin.register(Pemasok)
class PemasokAdmin(admin.ModelAdmin):
    list_display = ("namaPemasok", "noHp", "alamat", "show_actions")
    actions = ["export_pdf"]

    def show_actions(self, obj):
        return get_show_actions(obj, 'pemasok')
    show_actions.short_description = "Aksi"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.pk = 1
        super().save_model(request, obj, form, change)

    def export_pdf(self, request, queryset):
        data = [["Nama", "No HP", "Alamat"]]
        for s in queryset:
            data.append([s.namaPemasok, s.noHp, s.alamat])
        user_name = request.user.get_full_name() or request.user.username
        pdf_buffer = generate_pdf("LAPORAN DATA PEMASOK", data, generated_by=user_name)
        return FileResponse(pdf_buffer, as_attachment=True, filename="laporan_pemasok.pdf")


# ======================================================
# CATATAN KERUSAKAN & PRODUK OLAHAN
# ======================================================
from .models import CatatanKerusakan, ProdukOlahan, PenjualanOlahan

@admin.register(CatatanKerusakan)
class CatatanKerusakanAdmin(admin.ModelAdmin):
    list_display = ('get_buah', 'get_grade_batch', 'qty_rusak', 'nilai_kerugian', 'alasan', 'get_karyawan', 'tanggalDicatat')

    def get_karyawan(self, obj):
        return obj.idKaryawan.namaKaryawan if obj.idKaryawan else "-"
    get_karyawan.short_description = "Karyawan"
    list_filter = ('alasan', 'tanggalDicatat', 'idKaryawan')
    readonly_fields = ('kuantitas_sebelum', 'nilai_kerugian', 'tanggalDicatat')
    search_fields = ('idDetailPengadaan__idBuah__namaBuah', 'keterangan')
    autocomplete_fields = []
    actions = ['action_auto_kerusakan_lewat_masa_segar']

    fieldsets = (
        ('Batch Pengadaan', {
            'fields': ('idDetailPengadaan',),
            'description': 'Pilih batch buah yang rusak. Stok batch akan dikurangi otomatis saat disimpan.'
        }),
        ('Detail Kerusakan', {
            'fields': ('qty_rusak', 'alasan', 'keterangan')
        }),
        ('Data Otomatis (Jangan Diubah)', {
            'fields': ('kuantitas_sebelum', 'nilai_kerugian', 'tanggalDicatat', 'idKaryawan'),
            'classes': ('collapse',)
        }),
    )

    def get_buah(self, obj):
        return obj.idDetailPengadaan.idBuah.namaBuah
    get_buah.short_description = 'Buah'

    def get_grade_batch(self, obj):
        return "Grade Berbasis Qty"
    get_grade_batch.short_description = 'Grade Batch'

    def save_model(self, request, obj, form, change):
        if not change and not obj.idKaryawan_id:
            # Saat admin tambah baru, kosongkan idKaryawan
            pass
        super().save_model(request, obj, form, change)

    def action_auto_kerusakan_lewat_masa_segar(self, request, queryset):
        """Action: otomatis catat kerusakan untuk batch yang sudah lewat masa segar."""
        from datetime import date
        from decimal import Decimal
        jumlah = 0
        batches_rusak = DetailPengadaan.objects.filter(status=True)
        for batch in batches_rusak:
            if batch.qty_rusak > 0:
                sudah_dicatat = batch.catatan_kerusakan.filter(qty_rusak=batch.qty_rusak).exists()
                if not sudah_dicatat:
                    CatatanKerusakan.objects.create(
                        idDetailPengadaan=batch,
                        qty_rusak=batch.qty_rusak,
                        alasan='busuk_kadaluarsa',
                        keterangan='Auto-catat oleh sistem: grade rusak.',
                    )
                    jumlah += 1
        self.message_user(request, f"{jumlah} batch berhasil dicatat kerusakannya secara otomatis.")
    action_auto_kerusakan_lewat_masa_segar.short_description = "⚙️ Auto-Catat Kerusakan (Untuk Batch Rusak)"


class CustomBatchChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"Batch #{obj.idDetailPengadaan} - {obj.idBuah.namaBuah} | Sisa HR: {obj.qty_hampir_rusak} kg"

@admin.register(ProdukOlahan)
class ProdukOlahanAdmin(admin.ModelAdmin):
    list_display = ('nama_produk', 'get_buah', 'qty_bahan_dipakai', 'qty_produk_jadi', 'harga_jual_per_unit', 'tanggal')
    list_filter = ('tanggal', 'idKaryawan')
    readonly_fields = ('total_pendapatan', 'tanggal')
    search_fields = ('nama_produk', 'idDetailPengadaan__idBuah__namaBuah')

    fieldsets = (
        ('Bahan Baku', {
            'fields': ('idDetailPengadaan', 'qty_bahan_dipakai'),
            'description': 'Pilih batch bergrade Hampir Rusak. Stok dikurangi otomatis.'
        }),
        ('Produk yang Dihasilkan', {
            'fields': ('nama_produk', 'qty_produk_jadi', 'harga_jual_per_unit', 'catatan')
        }),
        ('Data Otomatis', {
            'fields': ('total_pendapatan', 'tanggal', 'idKaryawan'),
            'classes': ('collapse',)
        }),
    )

    def get_buah(self, obj):
        return obj.idDetailPengadaan.idBuah.namaBuah
    get_buah.short_description = 'Buah'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "idDetailPengadaan":
            kwargs["form_class"] = CustomBatchChoiceField
            kwargs["queryset"] = DetailPengadaan.objects.filter(status=True, qty_hampir_rusak__gt=0).order_by('-tanggalMasuk')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(PenjualanOlahan)
class PenjualanOlahanAdmin(admin.ModelAdmin):
    list_display = ('nama_pelanggan', 'get_olahan', 'qty', 'total_pendapatan', 'tanggal', 'pencatat')
    list_filter = ('tanggal',)
    search_fields = ('nama_pelanggan', 'idProdukOlahan__nama_produk', 'pencatat')
    exclude = ('pencatat',)

    def save_model(self, request, obj, form, change):
        if not getattr(obj, 'pencatat', None):
            obj.pencatat = request.user.username
        super().save_model(request, obj, form, change)

    def get_olahan(self, obj):
        return obj.idProdukOlahan.nama_produk
    get_olahan.short_description = "Produk Olahan"

    def total_pendapatan(self, obj):
        return f"Rp {obj.qty * obj.idProdukOlahan.harga_jual_per_unit:,.2f}"
    total_pendapatan.short_description = "Pendapatan"


# ======================================================
# PENGADAAN
# ======================================================
class DetailPengadaanAdminForm(forms.ModelForm):
    class Meta:
        model = DetailPengadaan
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        kuantitas = cleaned_data.get('kuantitas') or 0
        segar = cleaned_data.get('qty_segar') or 0
        menengah = cleaned_data.get('qty_menengah') or 0
        hampir_rusak = cleaned_data.get('qty_hampir_rusak') or 0
        rusak = cleaned_data.get('qty_rusak') or 0
        total_alokasi = segar + menengah + hampir_rusak + rusak
        
        if total_alokasi != kuantitas:
            raise forms.ValidationError(f"Total alokasi grade ({total_alokasi} kg) harus sama dengan kuantitas kotor nota ({kuantitas} kg)!")
        return cleaned_data

class DetailPengadaanInline(admin.TabularInline):
    model = DetailPengadaan
    form = DetailPengadaanAdminForm
    extra = 1
    fields = ('idBuah', 'kuantitas', 'qty_segar', 'qty_menengah', 'qty_hampir_rusak', 'qty_rusak', 'subHarga')
    readonly_fields = ()


@admin.register(Pengadaan)
class PengadaanAdmin(admin.ModelAdmin):
    list_display = ("nama_pemasok", "total_harga_rupiah", "tanggal_pengadaan", "show_actions")
    readonly_fields = ('totalHarga',)
    inlines = [DetailPengadaanInline]
    list_filter = (("detailpengadaan__tanggalMasuk", admin.DateFieldListFilter),)
    actions = ["export_pdf", "export_pdf_by_date"]

    def show_actions(self, obj):
        return get_show_actions(obj, 'pengadaan')
    show_actions.short_description = "Aksi"

    def nama_pemasok(self, obj):
        return obj.idPemasok.namaPemasok

    def total_harga_rupiah(self, obj):
        return f"Rp {intcomma(obj.totalHarga)}"
    total_harga_rupiah.short_description = "Total Harga"

    def tanggal_pengadaan(self, obj):
        detail = obj.detailpengadaan_set.order_by('tanggalMasuk').first()
        if detail:
            return detail.tanggalMasuk.strftime('%d/%m/%Y')
        return "-"
    tanggal_pengadaan.short_description = "Tanggal Pengadaan"

    def export_pdf(self, request, queryset):
        data = [["ID", "Pemasok", "Total Harga"]]
        for pg in queryset:
            data.append([pg.idPengadaan, pg.idPemasok.namaPemasok, f"Rp {intcomma(pg.totalHarga)}"])
        user_name = request.user.get_full_name() or request.user.username
        pdf_buffer = generate_pdf("LAPORAN PENGADAAN", data, generated_by=user_name)
        return FileResponse(pdf_buffer, as_attachment=True, filename="laporan_pengadaan.pdf")

    def export_pdf_by_date(self, request, queryset):
        if "start_date" in request.POST and "end_date" in request.POST:
            start = request.POST["start_date"]
            end = request.POST["end_date"]

            qs = Pengadaan.objects.filter(
                detailpengadaan__tanggalMasuk__range=(start, end)
            ).distinct()

            data = [["ID", "Pemasok", "Total Harga"]]
            for pg in qs:
                data.append([pg.idPengadaan, pg.idPemasok.namaPemasok, f"Rp {intcomma(pg.totalHarga)}"])

            user_name = request.user.get_full_name() or request.user.username
            pdf = generate_pdf(f"LAPORAN PENGADAAN {start} - {end}", data, generated_by=user_name)
            return FileResponse(pdf, as_attachment=True, filename="laporan_pengadaan_rentang.pdf")

        return render(request, "core/admin/pengadaan/date_range_form.html")
    export_pdf_by_date.short_description = "Cetak Laporan (Rentang Tanggal)"


# ======================================================
# SAFE ADMIN INDEX WRAPPER
# ======================================================
from django.contrib import admin
from .models import Buah, Pembelian

# Save reference to original index function BEFORE override
_original_index = admin.site.index

def safe_admin_index(request, extra_context=None):
    extra_context = extra_context or {}
    try:
        extra_context["buah_count"] = Buah.objects.count()
        extra_context["pembelian_count"] = Pembelian.objects.count()
    except Exception:
        extra_context["buah_count"] = 0
        extra_context["pembelian_count"] = 0

    # Call the ORIGINAL index function, NOT the wrapped one
    return _original_index(request, extra_context)

# Apply the wrapper
admin.site.index = safe_admin_index


@admin.register(Karyawan)
class KaryawanAdmin(admin.ModelAdmin):
    # Kolom yang akan tampil di tabel depan
    list_display = ('namaKaryawan', 'noHp', 'status_password')
    
    # Menambahkan fitur pencarian berdasarkan nama dan no HP
    search_fields = ('namaKaryawan', 'noHp')
    
    # Agar layout form edit lebih rapi
    fieldsets = (
        ('Informasi Pribadi', {
            'fields': ('namaKaryawan', 'noHp')
        }),
        ('Autentikasi', {
            'fields': ('password',),
            'description': 'Teks password yang tampil di bawah adalah versi terenkripsi (acak). Untuk mereset password karyawan, hapus teks acak tersebut dan ketik password baru, lalu klik Save.'
        }),
    )

    # Fungsi kustom untuk menampilkan status password di tabel (agar tidak menuh-menuhin layar dengan teks acak)
    def status_password(self, obj):
        if obj.password:
            return "Terenkripsi (Aman)"
        return "Belum diatur"
    status_password.short_description = 'Password'


@admin.register(LogAktivitasKaryawan)
class LogAktivitasKaryawanAdmin(admin.ModelAdmin):
    # Kolom yang akan tampil di tabel depan
    list_display = ('timestamp', 'get_karyawan', 'aksi', 'target_model', 'potong_deskripsi')

    def get_karyawan(self, obj):
        return obj.idKaryawan.namaKaryawan if obj.idKaryawan else "-"
    get_karyawan.short_description = "Karyawan"
    
    # Filter di sidebar kanan untuk memudahkan pencarian log
    list_filter = ('aksi', 'target_model', 'timestamp', 'idKaryawan')
    
    # Fitur pencarian berdasarkan deskripsi dan nama karyawan
    search_fields = ('deskripsi', 'idKaryawan__namaKaryawan')
    
    # LOG TIDAK BOLEH DIEDIT (Keamanan Data)
    # Kita kunci semua field agar superuser hanya bisa melihat (Read Only)
    readonly_fields = ('idKaryawan', 'aksi', 'target_model', 'target_id', 'deskripsi', 'timestamp')

    # Mencegah admin menambahkan log secara manual dari panel admin
    def has_add_permission(self, request):
        return False

    # Fungsi untuk memotong deskripsi agar tabel tidak terlalu lebar
    def potong_deskripsi(self, obj):
        if len(obj.deskripsi) > 50:
            return f"{obj.deskripsi[:50]}..."
        return obj.deskripsi
    potong_deskripsi.short_description = 'Deskripsi Aktivitas'


@admin.register(ProfilToko)
class ProfilTokoAdmin(admin.ModelAdmin):
    list_display = ('nama_toko', 'telepon', 'alamat', 'footer_pesan')
