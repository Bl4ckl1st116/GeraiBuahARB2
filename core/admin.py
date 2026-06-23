from django.contrib import admin
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
    Pemasok, Pengadaan, DetailPengadaan
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
    list_display = ("namaBuah", "harga_rupiah", "stokBuah", "diskon", "tanggalKadaluarsa", "show_actions")
    search_fields = ("namaBuah",)
    list_filter = ("diskon", "lamaKesegaraan")
    actions = ["export_pdf"]

    def show_actions(self, obj):
        return get_show_actions(obj, 'buah')
    show_actions.short_description = "Aksi"

    def harga_rupiah(self, obj):
        return f"Rp {intcomma(obj.hargaBuah)}"
    harga_rupiah.short_description = "Harga"

    def export_pdf(self, request, queryset):
        data = [["Nama", "Harga", "Stok", "Diskon", "Kadaluarsa"]]
        for b in queryset:
            data.append([
                b.namaBuah,
                f"Rp {intcomma(b.hargaBuah)}",
                b.stokBuah,
                f"{b.diskon * 100:.0f}%",
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
        "statusPembelian", "tanggalPembelian", "show_actions"
    )
    inlines = [DetailPembelianInline]
    list_filter = ("statusPembelian", "metodeBayar", ("tanggalPembelian", admin.DateFieldListFilter))
    list_editable = ("statusPembelian",)
    actions = ["export_pdf", "export_pdf_by_date"]

    def show_actions(self, obj):
        return get_show_actions(obj, 'pembelian')
    show_actions.short_description = "Aksi"

    def nama_pelanggan(self, obj):
        return obj.idPelanggan.namaPelanggan

    def total_harga_rupiah(self, obj):
        return f"Rp {intcomma(obj.totalHargaPembelian)}"
    total_harga_rupiah.short_description = "Total Harga"

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

    def export_pdf(self, request, queryset):
        data = [["Nama", "No HP", "Alamat"]]
        for s in queryset:
            data.append([s.namaPemasok, s.noHp, s.alamat])
        user_name = request.user.get_full_name() or request.user.username
        pdf_buffer = generate_pdf("LAPORAN DATA PEMASOK", data, generated_by=user_name)
        return FileResponse(pdf_buffer, as_attachment=True, filename="laporan_pemasok.pdf")


# ======================================================
# PENGADAAN
# ======================================================
class DetailPengadaanInline(admin.TabularInline):
    model = DetailPengadaan
    extra = 1


@admin.register(Pengadaan)
class PengadaanAdmin(admin.ModelAdmin):
    list_display = ("nama_pemasok", "total_harga_rupiah", "tanggal_pengadaan", "show_actions")
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

