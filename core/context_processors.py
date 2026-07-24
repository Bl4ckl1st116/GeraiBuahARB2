from datetime import date, timedelta
import json
from .models import DetailPengadaan


def kesegaran_alert(request):
    """
    Context processor untuk mendeteksi batch buah yang mendekati atau sudah kadaluarsa.
    Hanya diaktifkan untuk staff admin di halaman dashboard utama (/admin/).
    """
    # Initialize default values
    kritis_buah = []
    peringatan_buah = []
    total_alerts = 0
    
    default_context = {
        'kritis_buah': kritis_buah,
        'peringatan_buah': peringatan_buah,
        'total_alerts': total_alerts,
    }
    
    # Only process for authenticated staff users on the admin index page
    if not request.user.is_authenticated or not request.user.is_staff:
        return default_context
    
    # Only run the expensive query on the admin dashboard page
    from django.urls import resolve
    try:
        resolved = resolve(request.path)
        if resolved.url_name != 'index' or not resolved.app_name == 'admin':
            return default_context
    except Exception:
        return default_context
    
    from django.db.models import Q
    # Ambil semua batch aktif dengan qty_hampir_rusak > 0 atau qty_rusak > 0
    active_batches = DetailPengadaan.objects.filter(
        Q(qty_hampir_rusak__gt=0) | Q(qty_rusak__gt=0),
        status=True
    ).select_related('idBuah')
    
    today = date.today()
    
    for batch in active_batches:
        # Hitung tanggal kadaluarsa (untuk referensi tampilan)
        exp_date = batch.tanggalMasuk + timedelta(days=batch.idBuah.lamaKesegaraan)
        sisa_hari = (exp_date - today).days
        
        if batch.qty_rusak > 0:
            batch_data = {
                'id': batch.idDetailPengadaan,
                'nama': batch.idBuah.namaBuah,
                'sisa_hari': sisa_hari,
                'kuantitas': batch.qty_rusak,
                'exp_date': exp_date.strftime('%d/%m/%Y'),
                'tanggal_masuk': batch.tanggalMasuk.strftime('%d/%m/%Y'),
                'grade': 'rusak',
            }
            kritis_buah.append(batch_data)
            total_alerts += 1
            
        if batch.qty_hampir_rusak > 0:
            batch_data = {
                'id': batch.idDetailPengadaan,
                'nama': batch.idBuah.namaBuah,
                'sisa_hari': sisa_hari,
                'kuantitas': batch.qty_hampir_rusak,
                'exp_date': exp_date.strftime('%d/%m/%Y'),
                'tanggal_masuk': batch.tanggalMasuk.strftime('%d/%m/%Y'),
                'grade': 'hampir_rusak',
            }
            peringatan_buah.append(batch_data)
            total_alerts += 1
    
    # Convert lists to JSON strings for safe JavaScript consumption
    kritis_buah_json = json.dumps(kritis_buah)
    peringatan_buah_json = json.dumps(peringatan_buah)
    
    return {
        'kritis_buah': kritis_buah,  # Keep original for template iteration
        'peringatan_buah': peringatan_buah,  # Keep original for template iteration
        'kritis_buah_json': kritis_buah_json,  # JSON string for JavaScript
        'peringatan_buah_json': peringatan_buah_json,  # JSON string for JavaScript
        'total_alerts': total_alerts,
    }
