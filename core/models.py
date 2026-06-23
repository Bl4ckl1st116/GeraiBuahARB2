from django.db import models
from datetime import timedelta

from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
# Create your models here.

# class Admin(models.Model):
#     idAdmin = models.AutoField(primary_key=True)
#     username = models.CharField(max_length=30, unique=True)
#     password = models.CharField(max_length=30)
#     namaAdmin = models.CharField(max_length=70)

#     def __str__(self):
#         return f"{self.namaAdmin} - {self.username}"

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
    diskon = models.DecimalField(max_digits=3, decimal_places=2, default=0)  # dalam persen
    lamaKesegaraan = models.IntegerField()  # dalam hari max_length=2
   # tanggalKadaluarsa = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Buah"

    @property
    def stokBuah(self):
        return sum(
            detailPengadaan.kuantitas for detailPengadaan in self.detail_pengadaan.filter(status=True)
        )

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
    buktiBayar = models.ImageField(upload_to='bukti_bayar/')
    tanggalPembelian = models.DateTimeField(auto_now_add=True)
       

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

        # Jika ada diskon, terapkan diskon
        if self.idBuah.diskon:
            harga_asli = harga_asli - (harga_asli * self.idBuah.diskon)

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
    totalHarga = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # dalam ribu rupiah
    

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
    # idBuah = models.ForeignKey(Buah, on_delete=models.CASCADE)
    idBuah = models.ForeignKey(Buah, on_delete=models.CASCADE, related_name="detail_pengadaan")
    kuantitas = models.IntegerField()  # max_length=4
    # tipekuantitass = [
    #     ('perkilo', 'perkilo'),
    #     ('perbuah', 'perbuah'),
    #     ('perbungkus', 'perbungkus'),
    #     ('perbox', 'perbox'),
    # ]
    # tipeKuantitas = models.CharField(max_length=10, choices=tipekuantitass, default='perkilo')
    subHarga = models.DecimalField(max_digits=9, decimal_places=2)  # dalam ribu rupiah
    tanggalMasuk = models.DateField(auto_now_add=True)
    # statss = [
    #     ('True', 'True'),
    #     ('False', 'False'),
    # ]
    status = models.BooleanField(default='True')
    

    class Meta:
        verbose_name_plural = "Detail Pengadaan"

    def __str__(self):
        return f"Detail Pengadaan {self.idDetailPengadaan} - ID:{self.idPengadaan} - Buah: {self.idBuah.namaBuah} - Kuantitas: {self.kuantitas} kilo - Subtotal: {self.subHarga} ribu"
    
@receiver(post_save, sender=DetailPembelian)
@receiver(post_delete, sender=DetailPembelian)
def update_total_pembelian(sender, instance, **kwargs):instance.idPembelian.update_total()

@receiver(post_save, sender=DetailPengadaan)
@receiver(post_delete, sender=DetailPengadaan)
def update_total_pengadaan(sender, instance, **kwargs):instance.idPengadaan.update_total()

@receiver(post_save, sender=DetailPembelian)
@receiver(post_delete, sender=DetailPembelian)
def update_total_pembelian(sender, instance, **kwargs):instance.idPembelian.update_total()

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

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

        if batch.kuantitas >= qty:
            batch.kuantitas -= qty
            if batch.kuantitas == 0:
                batch.status = False
            batch.save()
            qty = 0
        else:
            qty -= batch.kuantitas
            batch.kuantitas = 0
            batch.status = False
            batch.save()



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

            # kembalikan ke batch terbaru (LIFO)
            batch = buah.detail_pengadaan.order_by('-tanggalMasuk').first()

            if batch:
                batch.kuantitas += qty
                batch.status = True
                batch.save()

        instance.stok_dikembalikan = True