from django import forms
from django.core.exceptions import ValidationError
from .models import DetailPembelian


class DetailPembelianForm(forms.ModelForm):
    class Meta:
        model = DetailPembelian
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        buah = cleaned_data.get('idBuah')
        kuantitas = cleaned_data.get('kuantitas')

        if not buah or not kuantitas:
            return cleaned_data

        # Get available stock
        stok_tersedia = buah.stokBuah

        # If editing an existing record, add back its current quantity
        # (it's already been deducted from stock)
        if self.instance and self.instance.pk:
            stok_tersedia += self.instance.kuantitas

        if kuantitas > stok_tersedia:
            if stok_tersedia <= 0:
                raise ValidationError(
                    f"Stok {buah.namaBuah} tidak tersedia (stok habis)."
                )
            else:
                raise ValidationError(
                    f"Stok {buah.namaBuah} tidak mencukupi. "
                    f"Stok tersedia: {stok_tersedia} kg, "
                    f"Anda meminta: {kuantitas} kg."
                )

        return cleaned_data
