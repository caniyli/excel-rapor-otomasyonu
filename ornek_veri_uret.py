"""Tamamen uydurma, tohumlu (tekrarlanabilir) örnek satış verisi üretir.

Kullanım:  python ornek_veri_uret.py [klasör]      (varsayılan: ornek_veri/)

3 şube x 3 ay = 9 dosya üretir. Dosyalar bilerek dağınıktır: CSV (noktalı virgül,
Türkçe ondalık virgül, utf-8 ve cp1254 karışık) ve XLSX; sütun adları ve tarih
biçimleri dosyadan dosyaya değişir; yinelenen, boş ve bozuk satırlar vardır.
Üretici, temizlendiğinde çıkması gereken doğru toplamları `beklenen.json`
dosyasına yazar (uçtan uca test bunu kullanır).
"""
import csv
import datetime as dt
import json
import random
import sys
from pathlib import Path

from openpyxl import Workbook

SUBELER = {"Kadıköy": "KDK", "Çankaya": "CNK", "Konak": "KNK"}
AYLAR = [(2026, 8), (2026, 9), (2026, 10)]
URUNLER = [
    ("Filtre Kahve 250 g", 185.0), ("Çay Demlik Seti", 640.0),
    ("Bardak Takımı", 420.0), ("Termos", 530.0), ("Defter A5", 95.0),
    ("Kalem Seti", 120.0), ("Hediye Kutusu", 275.0), ("Kokulu Mum", 160.0),
    ("Ahşap Kaşık", 85.0), ("Seramik Kupa", 210.0), ("El Yapımı Sabun", 70.0),
    ("Bez Çanta", 110.0), ("Masa Lambası", 980.0), ("Çalışma Örtüsü", 345.0),
]
BASLIKLAR = {
    "A": {"tarih": "Tarih", "siparis": "Sipariş No", "urun": "Ürün",
          "adet": "Adet", "tutar": "Tutar"},
    "B": {"tarih": "tarih", "siparis": "Sipariş No", "urun": "Ürün Adı",
          "adet": "Miktar", "tutar": "Toplam (TL)"},
    "C": {"tarih": "Sipariş Tarihi", "siparis": "Fiş No", "urun": "Ürün",
          "adet": "Adet", "tutar": "Tutar (TL)"},
}
ALANLAR = ["tarih", "siparis", "urun", "adet", "tutar"]
# (şube, ay) -> (dosya biçimi, başlık takımı, tarih biçimi, tutar biçimi)
PLAN = {
    ("Kadıköy", 8): ("csv-utf8", "A", "nokta", "tr"),
    ("Kadıköy", 9): ("csv-cp1254", "A", "iso", "tr_tl"),
    ("Kadıköy", 10): ("xlsx", "B", "hucre", "sayi"),
    ("Çankaya", 8): ("csv-cp1254", "B", "karisik", "tr"),
    ("Çankaya", 9): ("xlsx", "C", "metin", "tr_tl"),
    ("Çankaya", 10): ("csv-utf8", "C", "iso", "tr"),
    ("Konak", 8): ("xlsx", "A", "hucre", "sayi"),
    ("Konak", 9): ("csv-utf8", "B", "nokta", "tr_tl"),
    ("Konak", 10): ("csv-cp1254", "C", "karisik", "tr"),
}


def tr_sayi(deger, binlik=True):
    s = "{:,.2f}".format(deger) if binlik else "{:.2f}".format(deger)
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def tarih_yaz(gun, bicim, rng):
    if bicim == "karisik":
        bicim = rng.choice(["nokta", "iso", "egik"])
    if bicim in ("nokta", "metin"):
        return gun.strftime("%d.%m.%Y")
    if bicim == "iso":
        return gun.isoformat()
    if bicim == "egik":
        return gun.strftime("%d/%m/%Y")
    return dt.datetime(gun.year, gun.month, gun.day)  # "hucre": gerçek Excel tarihi


def tutar_yaz(tutar, bicim, rng):
    if bicim == "sayi":
        return tutar if rng.random() < 0.9 else tr_sayi(tutar) + " TL"
    s = tr_sayi(tutar, binlik=rng.random() < 0.7)
    return s + " TL" if bicim == "tr_tl" else s


def dosya_satirlari(sube, yil, ay, plan, rng, siparis_baslangic):
    """Bir dosyanın ham satırlarını ve doğru (temiz) kayıtlarını üretir."""
    _, _, tarih_bicimi, tutar_bicimi = plan
    kod = SUBELER[sube]
    temiz, ham = [], []
    for i in range(rng.randint(38, 55)):
        ad, fiyat = rng.choice(URUNLER)
        adet = rng.randint(1, 5)
        tutar = round(adet * fiyat * rng.choice([1, 1, 1, 0.9, 0.95]), 2)
        gun = dt.date(yil, ay, rng.randint(1, 28))
        no = "{}-{:02d}{:03d}".format(kod, ay, siparis_baslangic + i)
        temiz.append({"sube": sube, "tarih": gun, "no": no, "urun": ad,
                      "adet": adet, "tutar": tutar})
        urun_ham = ad
        if rng.random() < 0.12:  # başta/sonda fazladan boşluk
            urun_ham = rng.choice(["  ", " ", ""]) + ad + rng.choice(["  ", " "])
        ham.append({"tarih": tarih_yaz(gun, tarih_bicimi, rng), "siparis": no,
                    "urun": urun_ham, "adet": adet,
                    "tutar": tutar_yaz(tutar, tutar_bicimi, rng)})

    yinelenen = rng.choice([0, 1, 2, 2])
    for _ in range(yinelenen):  # aynı satırı bir kez daha yaz
        k = rng.randrange(len(ham))
        ham.insert(k + 1, dict(ham[k]))

    bozuk_turleri = []
    for _ in range(rng.choice([1, 1, 2])):
        tur = rng.choice(["bos", "tarih_gecersiz", "tutar_bozuk", "urun_bos"])
        bozuk_turleri.append(tur)
        satir = dict(ham[rng.randrange(len(ham))])
        if tur == "bos":
            satir = {a: "" for a in ALANLAR}
        elif tur == "tarih_gecersiz":
            satir["tarih"] = rng.choice(["31.02.2026", "", "yarın"])
            satir["siparis"] = satir["siparis"] + "-X"
        elif tur == "tutar_bozuk":
            satir["tutar"] = rng.choice(["belirsiz", "#DEĞER!", "-"])
            satir["siparis"] = satir["siparis"] + "-X"
        else:
            satir["urun"] = "   "
            satir["siparis"] = satir["siparis"] + "-X"
        ham.insert(rng.randrange(len(ham) + 1), satir)
    return temiz, ham, yinelenen, len(bozuk_turleri)


def dosya_yaz(yol, bicim, baslik_takimi, ham):
    basliklar = [BASLIKLAR[baslik_takimi][a] for a in ALANLAR]
    satirlar = [[r[a] for a in ALANLAR] for r in ham]
    if bicim == "xlsx":
        wb = Workbook()
        ws = wb.active
        ws.title = "Satışlar"
        ws.append(basliklar)
        for s in satirlar:
            ws.append([None if v == "" else v for v in s])
        wb.save(str(yol))
        return
    kodlama = "utf-8" if bicim == "csv-utf8" else "cp1254"
    with open(str(yol), "w", encoding=kodlama, newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(basliklar)
        w.writerows(satirlar)


def uret(klasor, tohum=2026):
    """Dosyaları yazar, doğru toplamları (kuruş hassasiyetinde) döndürür."""
    klasor = Path(klasor)
    klasor.mkdir(parents=True, exist_ok=True)
    for eski in list(klasor.glob("*.csv")) + list(klasor.glob("*.xlsx")):
        eski.unlink()
    rng = random.Random(tohum)
    tum_temiz, yinelenen, bozuk = [], 0, 0
    for (sube, ay), plan in PLAN.items():
        yil = 2026
        temiz, ham, d, b = dosya_satirlari(sube, yil, ay, plan, rng, 1)
        uzanti = "xlsx" if plan[0] == "xlsx" else "csv"
        dosya_yaz(klasor / "{}_{}-{:02d}.{}".format(sube, yil, ay, uzanti),
                  plan[0], plan[1], ham)
        tum_temiz += temiz
        yinelenen += d
        bozuk += b

    def kurus(kayitlar):
        return sum(int(round(k["tutar"] * 100)) for k in kayitlar)

    beklenen = {
        "dosya_sayisi": len(PLAN),
        "satir_sayisi": len(tum_temiz),
        "siparis_sayisi": len({k["no"] for k in tum_temiz}),
        "yinelenen": yinelenen,
        "bozuk": bozuk,
        "toplam_ciro": kurus(tum_temiz) / 100,
        "sube_ciro": {s: kurus([k for k in tum_temiz if k["sube"] == s]) / 100
                      for s in SUBELER},
        "ay_ciro": {"{}-{:02d}".format(y, a): kurus(
            [k for k in tum_temiz if k["tarih"].month == a]) / 100
            for y, a in AYLAR},
    }
    with open(str(klasor / "beklenen.json"), "w", encoding="utf-8") as f:
        json.dump(beklenen, f, ensure_ascii=False, indent=2)
    return beklenen


if __name__ == "__main__":
    hedef = sys.argv[1] if len(sys.argv) > 1 else "ornek_veri"
    sonuc = uret(hedef)
    print("{} dosya yazıldı: {} (doğru toplam ciro: {:.2f} TL)".format(
        sonuc["dosya_sayisi"], hedef, sonuc["toplam_ciro"]))
