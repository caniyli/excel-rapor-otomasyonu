"""CSV ve XLSX dosyalarını ham tablo olarak okur (kodlama ve ayraç algılamalı)."""
import codecs
import csv
import io
from pathlib import Path

from openpyxl import load_workbook

from .ayristir import metin_temizle
from .hatalar import RaporHatasi

UZANTILAR = (".csv", ".xlsx")
AYRAC_ADAYLARI = (";", ",", "\t", "|")


class Tablo(object):
    """Bir dosyanın başlıkları ve satırları. satirlar: [(dosyadaki satır no, [hücreler])]."""

    def __init__(self, dosya, basliklar, satirlar):
        self.dosya = dosya
        self.basliklar = basliklar
        self.satirlar = satirlar


def dosyalari_bul(klasor, haric=None):
    """Klasördeki CSV/XLSX dosyalarını ada göre sıralı döndürür.

    Excel'in geçici '~$' dosyaları, gizli dosyalar ve `haric` (çıktı dosyası) atlanır.
    """
    klasor = Path(klasor)
    if not klasor.exists():
        raise RaporHatasi("Klasör bulunamadı: {}".format(klasor))
    if not klasor.is_dir():
        raise RaporHatasi("Bir klasör bekleniyordu, dosya verildi: {}".format(klasor))
    haric = haric.resolve() if haric else None
    bulunanlar = [
        p for p in sorted(klasor.iterdir(), key=lambda p: p.name.lower())
        if p.is_file() and p.suffix.lower() in UZANTILAR
        and not p.name.startswith(("~$", ".")) and p.resolve() != haric
    ]
    if not bulunanlar:
        raise RaporHatasi("{} içinde .csv veya .xlsx dosyası yok.".format(klasor))
    return bulunanlar


def kodlama_algila(ham):
    """UTF-8 (BOM'lu/BOM'suz) ya da Windows-1254 (Türkçe) döndürür."""
    if ham.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    try:
        ham.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1254"


def ayrac_algila(metin):
    """İlk dolu satırdaki en sık geçen ayracı seçer (; , sekme |)."""
    for satir in metin.splitlines():
        if satir.strip():
            sayilar = {a: satir.count(a) for a in AYRAC_ADAYLARI}
            en_iyi = max(AYRAC_ADAYLARI, key=lambda a: sayilar[a])
            return en_iyi if sayilar[en_iyi] else ";"
    return ";"


def _tablo_kur(yol, satirlar):
    """(satır_no, hücreler) listesinden başlığı ayırıp Tablo kurar."""
    for k, (_, hucreler) in enumerate(satirlar):
        if any(metin_temizle(h) for h in hucreler):
            basliklar = [metin_temizle(h) for h in hucreler]
            kalan = []
            for no, h in satirlar[k + 1:]:
                h = list(h)[:len(basliklar)]
                kalan.append((no, h + [""] * (len(basliklar) - len(h))))
            return Tablo(yol, basliklar, kalan)
    raise RaporHatasi("{}: dosya boş.".format(yol.name))


def csv_oku(yol):
    ham = yol.read_bytes()
    kodlama = kodlama_algila(ham)
    try:
        metin = ham.decode(kodlama)
    except UnicodeDecodeError:
        raise RaporHatasi("{}: karakter kodlaması okunamadı.".format(yol.name))
    okuyucu = csv.reader(io.StringIO(metin, newline=""), delimiter=ayrac_algila(metin))
    satirlar = []
    for hucreler in okuyucu:
        if hucreler:  # tamamen boş satırları atla (satır numaraları korunur)
            satirlar.append((okuyucu.line_num, hucreler))
    return _tablo_kur(yol, satirlar)


def xlsx_oku(yol):
    try:
        wb = load_workbook(str(yol), read_only=True, data_only=True)
    except Exception as e:  # bozuk/şifreli dosya
        raise RaporHatasi("{}: Excel dosyası açılamadı ({}).".format(yol.name, e))
    try:
        ws = wb.worksheets[0]
        satirlar = [(no, list(r)) for no, r in
                    enumerate(ws.iter_rows(values_only=True), start=1)]
    finally:
        wb.close()
    return _tablo_kur(yol, satirlar)


def oku(yol):
    yol = Path(yol)
    return csv_oku(yol) if yol.suffix.lower() == ".csv" else xlsx_oku(yol)
