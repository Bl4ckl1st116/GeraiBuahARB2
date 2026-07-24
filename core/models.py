from django.db import models
from datetime import timedelta
from django.core.exceptions import ValidationError

from django.db.models import Sum
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
# Create your models here.



class Pelanggan(models.Model):
    idPelanggan = models.AutoField(primary_key=True)
    username = models.CharField(max_length=30, unique=True)
    password = models.CharField(max_length=30)
    namaPelanggan = models.CharField(max_length=70)
    alamat = models.TextField()
    noHp = models.CharField(max_length=12)

    class Meta:
        verbose_name_plural = "Pelanggan"

    def __str__(self):
        return f"{self.namaPelanggan} - {self.username}"



class Buah(models.Model):
    idBuah = models.AutoField(primary_key=True)
    namaBuah = models.CharField(max_length=50)
    fotoBuah = models.ImageField(upload_to='buah_images/')
    hargaBuah = models.DecimalField(max_digits=8, decimal_places=2)  # dalam ribu rupiah
   # stokBuah = models.IntegerField()  # dalam kilogram max_length=4
    deskripsiBuah = models.TextField()
    lamaKesegaraan = models.IntegerField()  # dalam hari max_length=2
   # tanggalKadaluarsa = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Buah"

    @property
    def stokBuah(self):
        return sum(
            (d.qty_segar + d.qty_menengah) for d in self.detail_pengadaan.filter(status=True)
        )

    @property
    def stokPerGrade(self):
        stok = {'segar': 0, 'menengah': 0, 'hampir_rusak': 0, 'rusak': 0}
        for d in self.detail_pengadaan.filter(status=True):
            stok['segar'] += d.qty_segar
            stok['menengah'] += d.qty_menengah
            stok['hampir_rusak'] += d.qty_hampir_rusak
            stok['rusak'] += d.qty_rusak
        return stok

    @property
    def tanggalKadaluarsa(self):
        batch_aktif= self.detail_pengadaan.filter(status=True).order_by('tanggalMasuk').first()
        if batch_aktif:
            return batch_aktif.tanggalMasuk + timedelta(days=self.lamaKesegaraan)
        return None

    def __str__(self):
        return f"{self.namaBuah} - Rp{self.hargaBuah} - Stok: {self.stokBuah} kilo"
    
class Pembelian(models.Model):
    idPembelian = models.AutoField(primary_key=True)
    idPelanggan = models.ForeignKey(Pelanggan, on_delete=models.CASCADE)    
    totalBuah = models.IntegerField(default=0)  # dalam kilogram max_length=5
    totalHargaPembelian = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # dalam ribu rupiah 
    tipeBayar =[
        ('COD', 'COD'),
        ('Transfer Bank BRI', 'Transfer Bank BRI'),
    ]
    metodeBayar = models.CharField(max_length=20 , choices=tipeBayar, default='COD')
    alamatPengiriman = models.TextField(default='')
    statsBayar =[
        ('Menunggu', 'Menunggu'),
        ('Diproses', 'Diproses'),
        ('Selesai', 'Selesai'),
        ('Dibatalkan', 'Dibatalkan'),
    ]
    statusPembelian = models.CharField(max_length=10, choices=statsBayar, default='Menunggu')
    buktiBayar = models.ImageField(upload_to='bukti_bayar/', null=True, blank=True)
    tanggalPembelian = models.DateTimeField(auto_now_add=True)

    # ── Jasa Kirim & Ongkos Kirim ──────────────────────────────────────
    # Ongkir dibayar cash langsung ke kurir, terpisah dari harga buah ke toko
    JENIS_KURIR_CHOICES = [
        ('', 'Tidak Ada / Belum Ditentukan'),
        ('Grab', 'Grab'),
        ('Maxim', 'Maxim'),
        ('GoSend', 'GoSend / Gojek'),
        ('Lalamove', 'Lalamove'),
        ('Kurir Sendiri', 'Kurir Sendiri'),
        ('Ambil Sendiri', 'Ambil Sendiri'),
        ('Lainnya', 'Lainnya'),
    ]
    jasa_kirim = models.CharField(
        max_length=30, choices=JENIS_KURIR_CHOICES, blank=True, default='',
        verbose_name='Jasa Kirim'
    )
    nama_kurir = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name='Nama Kurir',
        help_text='Opsional: nama pengemudi atau kontak kurir'
    )
    ongkos_kirim = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name='Ongkos Kirim',
        help_text='Dibayar cash langsung ke kurir, terpisah dari harga buah'
    )
    # ────────────────────────────────────────────────────────────────────
       

    stok_dikembalikan = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Pembelian"


    def update_total(self):
        total = self.detailpembelian_set.aggregate(total=Sum('subHarga'))['total'] or 0
        self.totalHargaPembelian = total
        self.save(update_fields=['totalHargaPembelian'])

    def update_total(self):
        from django.db.models import Sum
        
        total_qty = self.detailpembelian_set.aggregate(total=Sum('kuantitas'))['total'] or 0
        total_sub = self.detailpembelian_set.aggregate(total=Sum('subHarga'))['total'] or 0

        self.totalBuah = total_qty
        self.totalHargaPembelian = total_sub
        self.save()


    def __str__(self):
        return f"Pembelian {self.idPembelian} - Pelanggan: {self.idPelanggan.namaPelanggan} - Total: {self.totalHargaPembelian} ribu"
        
class DetailPembelian(models.Model):
    idDetailPembelian = models.AutoField(primary_key=True)
    idPembelian = models.ForeignKey(Pembelian, on_delete=models.CASCADE)
    idBuah = models.ForeignKey(Buah, on_delete=models.CASCADE)
    kuantitas = models.IntegerField()  # max_length=4
    subHarga = models.DecimalField(max_digits=9, decimal_places=2, default=0)  # dalam ribu rupiah
    

    def save(self, *args, **kwargs):
        # Hitung otomatis harga buah x kuantitas
        harga_asli = self.idBuah.hargaBuah

        self.subHarga = harga_asli * self.kuantitas

        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Detail Pembelian"


    def __str__(self):
        return f"Detail Pembelian {self.idDetailPembelian} - ID: {self.idPembelian} - Buah: {self.idBuah.namaBuah} - Kuantitas: {self.kuantitas} kilo - Subtotal: {self.subHarga} ribu"
        
class Pemasok(models.Model):
    idPemasok = models.AutoField(primary_key=True)
    namaPemasok = models.CharField(max_length=70)
    noHp = models.CharField(max_length=12)
    alamat = models.TextField()

    class Meta:
        verbose_name_plural = "Pemasok"

    def __str__(self):
        return f"{self.namaPemasok} - {self.noHp}"

class Pengadaan(models.Model):
    idPengadaan = models.AutoField(primary_key=True)
    idPemasok = models.ForeignKey(Pemasok, on_delete=models.CASCADE)
    totalHarga = models.DecimalField(max_digits=15, decimal_places=2, default=0, blank=True, null=True)
    

    def update_total(self):
        total = self.detailpengadaan_set.aggregate(total=Sum('subHarga'))['total'] or 0
        self.totalHarga = total
        self.save(update_fields=['totalHarga'])

    class Meta:
        verbose_name_plural = "Pengadaan"


    def __str__(self):
        return f"Pengadaan {self.idPengadaan}  - Pemasok: {self.idPemasok.namaPemasok} - Total Harga: {self.totalHarga} ribu"
    
class DetailPengadaan(models.Model):
    idDetailPengadaan = models.AutoField(primary_key=True)
    idPengadaan = models.ForeignKey(Pengadaan, on_delete=models.CASCADE)
    idBuah = models.ForeignKey(Buah, on_delete=models.CASCADE, related_name="detail_pengadaan")
    qty_segar = models.IntegerField(default=0)
    qty_menengah = models.IntegerField(default=0)
    qty_hampir_rusak = models.IntegerField(default=0)
    qty_rusak = models.IntegerField(default=0)
    kuantitas = models.IntegerField(default=0, help_text="Kuantitas total kotor nota")
    subHarga = models.DecimalField(max_digits=9, decimal_places=2, default=0)  # dalam ribu rupiah
    tanggalMasuk = models.DateField(auto_now_add=True)
    status = models.BooleanField(default=True)

    @property
    def stok_sisa(self):
        return self.qty_segar + self.qty_menengah + self.qty_hampir_rusak + self.qty_rusak

    @property
    def harga_beli_per_kg(self):
        if self.kuantitas and self.kuantitas > 0:
            return self.subHarga / self.kuantitas
        return self.subHarga / self.stok_sisa if self.stok_sisa else 0

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Detail Pengadaan"

    def __str__(self):
        return f"Detail Pengadaan {self.idDetailPengadaan} - ID:{self.idPengadaan} - Buah: {self.idBuah.namaBuah} - Kuantitas Kotor: {self.kuantitas} kg - Sisa: {self.stok_sisa} kg"
    
@receiver(post_save, sender=DetailPembelian)
@receiver(post_delete, sender=DetailPembelian)
def update_total_pembelian(sender, instance, **kwargs):instance.idPembelian.update_total()

@receiver(post_save, sender=DetailPengadaan)
@receiver(post_delete, sender=DetailPengadaan)
def update_total_pengadaan(sender, instance, **kwargs):instance.idPengadaan.update_total()

# Signal FIFO Penjualan
@receiver(post_save, sender=DetailPembelian)
def kurangi_stok_fifo(sender, instance, created, **kwargs):
    if not created:
        return

    qty = instance.kuantitas
    buah = instance.idBuah

    batch_list = buah.detail_pengadaan.filter(status=True).order_by('tanggalMasuk')

    for batch in batch_list:
        if qty <= 0:
            break

        # Deduct from qty_menengah first
        if batch.qty_menengah > 0:
            if batch.qty_menengah >= qty:
                batch.qty_menengah -= qty
                qty = 0
            else:
                qty -= batch.qty_menengah
                batch.qty_menengah = 0

        # Then deduct from qty_segar
        if qty > 0 and batch.qty_segar > 0:
            if batch.qty_segar >= qty:
                batch.qty_segar -= qty
                qty = 0
            else:
                qty -= batch.qty_segar
                batch.qty_segar = 0

        if batch.qty_segar == 0 and batch.qty_menengah == 0 and batch.qty_hampir_rusak == 0 and batch.qty_rusak == 0:
            batch.status = False
            
        batch.save(update_fields=['qty_segar', 'qty_menengah', 'status'])



@receiver(pre_save, sender=Pembelian)
def pembatalan_pembelian(sender, instance, **kwargs):

    # pembelian baru → tidak usah diproses
    if not instance.pk:
        return

    lama = Pembelian.objects.get(pk=instance.pk)

    # status berubah menjadi dibatalkan
    if lama.statusPembelian != 'Dibatalkan' and instance.statusPembelian == 'Dibatalkan':

        # sudah pernah dikembalikan?
        if instance.stok_dikembalikan:
            return

        for d in instance.detailpembelian_set.all():

            buah = d.idBuah
            qty = d.kuantitas

            # kembalikan ke batch terbaru (LIFO) yang aktif
            batch = buah.detail_pengadaan.filter(status=True).order_by('-tanggalMasuk').first()

            if batch:
                batch.qty_segar += qty
                batch.status = True
                batch.save(update_fields=['qty_segar', 'status'])

        instance.stok_dikembalikan = True


class Karyawan(models.Model):
    idKaryawan = models.AutoField(primary_key=True)
    namaKaryawan = models.CharField(max_length=70)
    noHp = models.CharField(max_length=12, unique=True)
    password = models.CharField(max_length=128)

    class Meta:
        verbose_name_plural = "Karyawan"

    def __str__(self):
        return f"{self.namaKaryawan} - {self.noHp}"

    def save(self, *args, **kwargs):
        from django.contrib.auth.hashers import make_password
        if self.password and not self.password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2$')):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)


class LogAktivitasKaryawan(models.Model):
    AKSI_CHOICES = [
        ('CREATE', 'CREATE'),
        ('UPDATE', 'UPDATE'),
        ('DELETE', 'DELETE'),
    ]
    TARGET_MODEL_CHOICES = [
        ('Buah', 'Buah'),
        ('Pembelian', 'Pembelian'),
        ('Pelanggan', 'Pelanggan'),
        ('DetailPengadaan', 'DetailPengadaan'),
        ('CatatanKerusakan', 'CatatanKerusakan'),
        ('ProdukOlahan', 'ProdukOlahan'),
    ]
    idLog = models.AutoField(primary_key=True)
    idKaryawan = models.ForeignKey(Karyawan, on_delete=models.CASCADE)
    aksi = models.CharField(max_length=10, choices=AKSI_CHOICES)
    target_model = models.CharField(max_length=20, choices=TARGET_MODEL_CHOICES)
    target_id = models.IntegerField()
    deskripsi = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Log Aktivitas Karyawan"

    def __str__(self):
        return f"{self.timestamp} - {self.idKaryawan.namaKaryawan} - {self.aksi} {self.target_model} ({self.target_id})"


class ProfilToko(models.Model):
    nama_toko = models.CharField(max_length=100, default="GERAI BUAH ARB")
    alamat = models.TextField()
    telepon = models.CharField(max_length=20)
    footer_pesan = models.TextField()
    logo_struk = models.ImageField(upload_to='logo_struk/', null=True, blank=True)
    qris_image = models.ImageField(upload_to='qris/', null=True, blank=True)

    class Meta:
        verbose_name_plural = "Profil Toko"

    def __str__(self):
        return self.nama_toko

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class CatatanKerusakan(models.Model):
    ALASAN_CHOICES = [
        ('busuk_kadaluarsa', 'Busuk / Kadaluarsa'),
        ('rusak_fisik', 'Rusak Fisik / Jatuh'),
        ('hama', 'Hama / Ulat'),
        ('lainnya', 'Lainnya'),
    ]

    idKerusakan = models.AutoField(primary_key=True)
    idDetailPengadaan = models.ForeignKey(
        DetailPengadaan, on_delete=models.PROTECT,
        related_name='catatan_kerusakan',
        verbose_name='Batch Pengadaan'
    )
    qty_rusak = models.IntegerField(verbose_name='Jumlah Rusak (kg)')
    kuantitas_sebelum = models.IntegerField(
        default=0, verbose_name='Stok Sebelum Dicatat',
        help_text='Snapshot kuantitas batch sebelum kerusakan dicatat'
    )
    alasan = models.CharField(
        max_length=20, choices=ALASAN_CHOICES,
        verbose_name='Alasan Kerusakan'
    )
    keterangan = models.TextField(
        blank=True, default='',
        verbose_name='Keterangan Tambahan'
    )
    nilai_kerugian = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Nilai Kerugian (ribu Rp)'
    )
    tanggalDicatat = models.DateTimeField(auto_now_add=True)
    idKaryawan = models.ForeignKey(
        Karyawan, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Dicatat Oleh'
    )

    class Meta:
        verbose_name = 'Catatan Kerusakan'
        verbose_name_plural = 'Catatan Kerusakan'
        ordering = ['-tanggalDicatat']

    def save(self, *args, **kwargs):
        batch = self.idDetailPengadaan
        if not self.pk:
            self.kuantitas_sebelum = batch.stok_sisa
            harga_per_kg = batch.harga_beli_per_kg
            self.nilai_kerugian = self.qty_rusak * harga_per_kg
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Kerusakan #{self.idKerusakan} — {self.idDetailPengadaan.idBuah.namaBuah} {self.qty_rusak} kg"


class ProdukOlahan(models.Model):
    idProdukOlahan = models.AutoField(primary_key=True)
    idDetailPengadaan = models.ForeignKey(
        DetailPengadaan, on_delete=models.PROTECT,
        related_name='produk_olahan',
        verbose_name='Batch Bahan'
    )
    nama_produk = models.CharField(max_length=100, verbose_name='Nama Produk Olahan')
    qty_bahan_dipakai = models.IntegerField(verbose_name='Bahan Dipakai (kg)')
    qty_produk_jadi = models.IntegerField(verbose_name='Produk Jadi (unit)')
    harga_jual_per_unit = models.DecimalField(
        max_digits=8, decimal_places=2,
        verbose_name='Harga Jual per Unit (ribu Rp)'
    )
    total_pendapatan = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Total Pendapatan (ribu Rp)'
    )
    tanggal = models.DateField(auto_now_add=True, verbose_name='Tanggal Olah')
    catatan = models.TextField(blank=True, default='', verbose_name='Catatan')
    idKaryawan = models.ForeignKey(
        Karyawan, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Dicatat Oleh'
    )

    class Meta:
        verbose_name = 'Produk Olahan'
        verbose_name_plural = 'Produk Olahan'
        ordering = ['-tanggal']

    def clean(self):
        super().clean()
        if not self.pk:
            batch = self.idDetailPengadaan
            if self.qty_bahan_dipakai > batch.qty_hampir_rusak:
                raise ValidationError({'qty_bahan_dipakai': f"Stok tidak mencukupi! Stok grade hampir rusak hanya {batch.qty_hampir_rusak} kg."})

    def save(self, *args, **kwargs):
        self.total_pendapatan = self.qty_produk_jadi * self.harga_jual_per_unit
        if not self.pk:  # Hanya potong saat create
            batch = self.idDetailPengadaan
            batch.qty_hampir_rusak -= self.qty_bahan_dipakai

            if batch.stok_sisa == 0:
                batch.status = False
            batch.save(update_fields=['qty_hampir_rusak', 'status'])
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Olahan #{self.idProdukOlahan} — {self.nama_produk}"

class PenjualanOlahan(models.Model):
    idPenjualanOlahan = models.AutoField(primary_key=True)
    nama_pelanggan = models.CharField(max_length=150, null=True, blank=True, verbose_name="Nama Pelanggan")
    idProdukOlahan = models.ForeignKey(ProdukOlahan, on_delete=models.CASCADE, verbose_name="Produk Olahan")
    qty = models.IntegerField(verbose_name="Kuantitas (Unit)")
    tanggal = models.DateTimeField(auto_now_add=True, verbose_name="Tanggal Penjualan")
    pencatat = models.CharField(max_length=150, verbose_name="Dicatat Oleh")
    bukti_pembelian = models.ImageField(upload_to='bukti_olahan/', null=True, blank=True, verbose_name="Bukti Pembayaran")

    def __str__(self):
        return f"Penjualan #{self.idPenjualanOlahan} - {self.idProdukOlahan.nama_produk}"

    def clean(self):
        super().clean()
        if not self.pk:
            if self.qty > self.idProdukOlahan.qty_produk_jadi:
                raise ValidationError({'qty': f"Stok produk olahan tidak mencukupi! Sisa stok hanya {self.idProdukOlahan.qty_produk_jadi} unit."})

    def save(self, *args, **kwargs):
        if not self.pk:
            produk = self.idProdukOlahan
            produk.qty_produk_jadi -= self.qty
            produk.save(update_fields=['qty_produk_jadi'])
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Penjualan Olahan"
        verbose_name_plural = "Penjualan Olahan"