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
    
    # Ambil semua batch aktif dengan kuantitas > 0
    active_batches = DetailPengadaan.objects.filter(
        status=True,
        kuantitas__gt=0
    ).select_related('idBuah')
    
    today = date.today()
    
    print("\n" + "="*60)
    print("🍎 FRUIT FRESHNESS ALERT SYSTEM - BATCH SCAN")
    print("="*60)
    
    for batch in active_batches:
        # Hitung tanggal kadaluarsa
        exp_date = batch.tanggalMasuk + timedelta(days=batch.idBuah.lamaKesegaraan)
        
        # Hitung sisa hari
        sisa_hari = (exp_date - today).days
        
        # Debugging output
        print(f"Checking Batch: {batch.idBuah.namaBuah} | "
              f"Exp: {exp_date.strftime('%Y-%m-%d')} | "
              f"Sisa: {sisa_hari} Hari | "
              f"Qty: {batch.kuantitas} kg")
        
        # Klasifikasi berdasarkan sisa hari
        batch_data = {
            'id': batch.idDetailPengadaan,
            'nama': batch.idBuah.namaBuah,
            'sisa_hari': sisa_hari,
            'kuantitas': batch.kuantitas,
            'exp_date': exp_date.strftime('%d/%m/%Y'),
            'tanggal_masuk': batch.tanggalMasuk.strftime('%d/%m/%Y'),
        }
        
        if sisa_hari <= 0:
            # Kritis: Sudah kadaluarsa atau hari ini
            kritis_buah.append(batch_data)
            total_alerts += 1
        elif 1 <= sisa_hari <= 2:
            # Peringatan: 1-2 hari lagi kadaluarsa
            peringatan_buah.append(batch_data)
            total_alerts += 1
    
    print(f"\n📊 SUMMARY: {len(kritis_buah)} Critical | {len(peringatan_buah)} Warning")
    print("="*60 + "\n")
    
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
