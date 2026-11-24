"""Komut satırı arayüzü:  python -m rapor KLASÖR --cikti rapor.xlsx"""
import argparse
import sys
from pathlib import Path

from .esleme import esleme_yukle
from .hatalar import RaporHatasi
from .okuma import dosyalari_bul, oku
from .temizle import temizle
from .yaz import rapor_yaz


def tr_para(deger):
    """1234567.5 -> '1.234.567,50 TL'"""
    s = "{:,.2f}".format(deger).replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " TL"


def argumanlar(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m rapor",
        description="Klasördeki CSV/XLSX satış dosyalarını birleştirir, temizler "
                    "ve özet bir Excel raporu üretir.")
    p.add_argument("klasor", help="CSV/XLSX dosyalarının bulunduğu klasör")
    p.add_argument("--cikti", default="rapor.xlsx", help="yazılacak Excel dosyası (varsayılan: rapor.xlsx)")
    p.add_argument("--esleme", help="özel sütun eşleme dosyası (JSON); varsayılan: rapor/sutun_eslemesi.json")
    return p.parse_args(argv)


def calistir(args):
    cikti = Path(args.cikti)
    if cikti.suffix.lower() != ".xlsx":
        raise RaporHatasi("Çıktı dosyası .xlsx ile bitmeli: {}".format(cikti))
    esleme = esleme_yukle(args.esleme)
    dosyalar = dosyalari_bul(args.klasor, haric=cikti if cikti.exists() else None)
    tablolar = [oku(d) for d in dosyalar]
    df, atilan, ist, uyarilar = temizle(tablolar, esleme)
    try:
        rapor_yaz(cikti, df, atilan, ist)
    except PermissionError:
        raise RaporHatasi("'{}' yazılamadı. Dosya Excel'de açık olabilir; kapatıp tekrar deneyin.".format(cikti))
    except OSError as e:
        raise RaporHatasi("'{}' yazılamadı: {}".format(cikti, e))
    for u in uyarilar:
        print("Uyarı: " + u, file=sys.stderr)
    print("Rapor hazır.")
    print("  Okunan dosya     : {}".format(ist["dosya"]))
    print("  Birleşen satır   : {}".format(ist["temiz"]))
    print("  Ayıklanan satır  : {} (yinelenen: {}, bozuk/boş: {})".format(
        ist["yinelenen"] + ist["bozuk"], ist["yinelenen"], ist["bozuk"]))
    print("  Toplam ciro      : {}".format(tr_para(ist["ciro"])))
    print("  Çıktı            : {}".format(cikti))
    print("  (Atılan satırların nedenleri raporda 'Atılan Satırlar' sayfasında.)")


def main(argv=None):
    args = argumanlar(argv)
    try:
        calistir(args)
    except RaporHatasi as e:
        print("Hata: {}".format(e), file=sys.stderr)
        return 1
    return 0
