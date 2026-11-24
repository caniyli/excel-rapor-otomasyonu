"""Satırları normalleştirir, bozukları ve yinelenenleri ayıklar (silmez, gerekçesiyle tutar)."""
import pandas as pd

from .ayristir import (adet_ayristir, metin_temizle, tarih_ayristir,
                       tutar_ayristir)
from .esleme import sutunlari_esle
from .hatalar import RaporHatasi

KAYIT_SUTUNLARI = ["tarih", "sube", "siparis_no", "urun", "adet", "tutar", "kaynak"]
ATILAN_SUTUNLARI = ["kaynak", "satir_no", "neden", "icerik"]


def sube_dosya_adindan(yol):
    """'Kadıköy_2026-08.csv' -> 'Kadıköy' (ilk '_' öncesi)."""
    return yol.stem.split("_")[0].strip()


def _satiri_coz(hucreler, idx):
    """Ham hücrelerden kayıt çıkarır. (kayıt, [sorunlar]) döndürür."""
    sorunlar = []
    kayit = {}

    def al(alan):
        return hucreler[idx[alan]] if alan in idx else None

    for alan, ayristir in (("tarih", tarih_ayristir), ("tutar", tutar_ayristir)):
        try:
            kayit[alan] = ayristir(al(alan))
        except ValueError as e:
            mesaj = str(e)
            sorunlar.append(mesaj if alan in mesaj else "{}: {}".format(alan, mesaj))
    kayit["urun"] = metin_temizle(al("urun"))
    if not kayit["urun"]:
        sorunlar.append("ürün adı boş")
    if "adet" in idx:
        try:
            kayit["adet"] = adet_ayristir(al("adet"))
        except ValueError as e:
            sorunlar.append(str(e) if metin_temizle(al("adet")) else "adet boş")
    else:
        kayit["adet"] = 1
    if "tutar" in kayit and kayit["tutar"] <= 0:
        sorunlar.append("tutar sıfır veya negatif: {}".format(kayit["tutar"]))
    kayit["siparis_no"] = metin_temizle(al("siparis_no"))
    kayit["sube"] = metin_temizle(al("sube"))
    return kayit, sorunlar


def temizle(tablolar, esleme):
    """Tabloları birleştirir.

    Döndürür: (temiz DataFrame, atılan DataFrame, istatistik sözlüğü, uyarılar).
    Tanınmayan zorunlu sütun varsa tüm dosyalar taranır ve tek bir RaporHatasi
    içinde hepsi listelenir.
    """
    hatalar, uyarilar, eslesmeler = [], [], []
    for t in tablolar:
        try:
            idx, tanimayan = sutunlari_esle(t.dosya.name, t.basliklar, esleme)
        except RaporHatasi as e:
            hatalar.append(str(e))
            continue
        eslesmeler.append((t, idx))
        if tanimayan:
            uyarilar.append("{}: kullanılmayan sütunlar yok sayıldı: {}".format(
                t.dosya.name, ", ".join(tanimayan)))
    if hatalar:
        raise RaporHatasi("\n".join(hatalar))

    temiz, atilan, gorulen = [], [], {}
    okunan = 0
    for t, idx in eslesmeler:
        varsayilan_sube = sube_dosya_adindan(t.dosya)
        for satir_no, hucreler in t.satirlar:
            okunan += 1
            icerik = " | ".join(metin_temizle(h) for h in hucreler)
            if not any(metin_temizle(h) for h in hucreler):
                sorunlar, kayit = ["boş satır"], {}
            else:
                kayit, sorunlar = _satiri_coz(hucreler, idx)
            if sorunlar:
                atilan.append({"kaynak": t.dosya.name, "satir_no": satir_no,
                               "neden": "Bozuk satır: " + "; ".join(sorunlar),
                               "icerik": icerik, "tur": "bozuk"})
                continue
            kayit["sube"] = kayit["sube"] or varsayilan_sube
            kayit["kaynak"] = t.dosya.name
            anahtar = (kayit["sube"], kayit["tarih"], kayit["siparis_no"],
                       kayit["urun"], kayit["adet"], kayit["tutar"])
            if anahtar in gorulen:
                ilk = gorulen[anahtar]
                atilan.append({"kaynak": t.dosya.name, "satir_no": satir_no,
                               "neden": "Yinelenen satır: {} dosyasının {}. satırıyla aynı".format(*ilk),
                               "icerik": icerik, "tur": "yinelenen"})
                continue
            gorulen[anahtar] = (t.dosya.name, satir_no)
            temiz.append(kayit)

    if not temiz:
        raise RaporHatasi("Hiç geçerli satır bulunamadı; tüm satırlar atıldı.")
    df = pd.DataFrame(temiz, columns=KAYIT_SUTUNLARI)
    df = df.sort_values(["tarih", "sube", "siparis_no"], kind="mergesort").reset_index(drop=True)
    # Sipariş sayısı: sipariş numarası varsa şube+numara, yoksa her satır bir sipariş.
    df["siparis_anahtar"] = [
        "{}|{}".format(s, n) if n else "satir{}".format(i)
        for i, (s, n) in enumerate(zip(df["sube"], df["siparis_no"]))]
    at = pd.DataFrame(atilan, columns=ATILAN_SUTUNLARI + ["tur"])
    istatistik = {
        "dosya": len(tablolar),
        "okunan_satir": okunan,
        "temiz": len(df),
        "yinelenen": int((at["tur"] == "yinelenen").sum()),
        "bozuk": int((at["tur"] == "bozuk").sum()),
        "ciro": round(float(df["tutar"].sum()), 2),
    }
    return df, at[ATILAN_SUTUNLARI], istatistik, uyarilar
