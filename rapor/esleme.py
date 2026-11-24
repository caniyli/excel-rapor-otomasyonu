"""Sütun adı eşleme: farklı başlıkları ortak alan adlarına bağlar."""
import json
from pathlib import Path

from .hatalar import RaporHatasi

VARSAYILAN_ESLEME = Path(__file__).with_name("sutun_eslemesi.json")
ZORUNLU = ("tarih", "urun", "tutar")
ISTEGE_BAGLI = ("adet", "siparis_no", "sube")
_HARITA = str.maketrans({"İ": "i", "I": "ı", "ı": "i", "ş": "s", "Ş": "s",
                         "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u", "ö": "o",
                         "Ö": "o", "ç": "c", "Ç": "c"})


def baslik_normallestir(metin):
    """Karşılaştırma anahtarı: küçük harf, aksansız, noktalamasız, tek boşluk."""
    s = str(metin).translate(_HARITA).lower()
    s = "".join(c if c.isalnum() else " " for c in s)
    return " ".join(s.split())


def esleme_yukle(yol=None):
    """JSON eşleme dosyasını okur ve {alan: {normalleşmiş başlık, ...}} döndürür."""
    yol = Path(yol) if yol else VARSAYILAN_ESLEME
    try:
        with open(str(yol), encoding="utf-8") as f:
            ham = json.load(f)
    except FileNotFoundError:
        raise RaporHatasi("Eşleme dosyası bulunamadı: {}".format(yol))
    except ValueError as e:
        raise RaporHatasi("Eşleme dosyası geçerli JSON değil ({}): {}".format(yol, e))
    esleme = {}
    for alan in ZORUNLU + ISTEGE_BAGLI:
        adlar = ham.get(alan, [])
        if not isinstance(adlar, list):
            raise RaporHatasi("Eşleme dosyasında '{}' bir liste olmalı.".format(alan))
        esleme[alan] = {baslik_normallestir(a) for a in adlar}
    for alan in ZORUNLU:
        if not esleme[alan]:
            raise RaporHatasi("Eşleme dosyasında '{}' alanı boş olamaz.".format(alan))
    return esleme


def sutunlari_esle(dosya_adi, basliklar, esleme):
    """Başlıkları alanlara bağlar.

    Döndürür: ({alan: sütun_indeksi}, [tanınmayan başlıklar]).
    Zorunlu bir alan bulunamazsa hangi dosyada neyin eksik olduğunu söyleyen
    RaporHatasi fırlatır.
    """
    bulunan = {}
    for i, baslik in enumerate(basliklar):
        anahtar = baslik_normallestir(baslik)
        for alan, adlar in esleme.items():
            if alan not in bulunan and anahtar in adlar:
                bulunan[alan] = i
                break
    eksik = [a for a in ZORUNLU if a not in bulunan]
    if eksik:
        raise RaporHatasi(
            "{}: '{}' için sütun bulunamadı. Dosyadaki sütunlar: {}. "
            "Bu başlıkları sutun_eslemesi.json dosyasına ekleyin.".format(
                dosya_adi, "', '".join(eksik),
                ", ".join(repr(b) for b in basliklar if b)))
    kullanilan = set(bulunan.values())
    tanınmayan = [b for i, b in enumerate(basliklar) if b and i not in kullanilan]
    return bulunan, tanınmayan
