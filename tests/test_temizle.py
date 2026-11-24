import datetime as dt
from pathlib import Path

import pytest

from rapor.esleme import esleme_yukle
from rapor.hatalar import RaporHatasi
from rapor.okuma import Tablo
from rapor.temizle import temizle

B = ["Tarih", "Sipariş No", "Ürün", "Adet", "Tutar"]


def tablo(ad, satirlar, basliklar=B):
    return Tablo(Path(ad), basliklar, [(i + 2, s) for i, s in enumerate(satirlar)])


@pytest.fixture(scope="module")
def esleme():
    return esleme_yukle()


def test_yinelenen_satir_ayiklanir_ve_nedeni_yazilir(esleme):
    t = tablo("Konak_2026-08.csv", [
        ["01.08.2026", "K-1", "Termos", "1", "530,00"],
        ["2026-08-01", "K-1", " Termos ", "1", "530,00 TL"],  # aynı kayıt, farklı yazım
        ["01.08.2026", "K-2", "Termos", "1", "530,00"],       # farklı sipariş: yinelenen değil
    ])
    df, atilan, ist, _ = temizle([t], esleme)
    assert len(df) == 2 and ist["yinelenen"] == 1 and ist["bozuk"] == 0
    assert "Yinelenen" in atilan.iloc[0]["neden"] and "2. satır" in atilan.iloc[0]["neden"]
    assert atilan.iloc[0]["satir_no"] == 3


def test_yinelenen_dosyalar_arasinda_da_yakalanir(esleme):
    s = ["01.08.2026", "K-1", "Termos", "1", "530,00"]
    df, _, ist, _ = temizle([tablo("Konak_a.csv", [s]), tablo("Konak_b.csv", [s])], esleme)
    assert len(df) == 1 and ist["yinelenen"] == 1


def test_ayni_siparisin_farkli_urunleri_yinelenen_sayilmaz(esleme):
    t = tablo("Konak_x.csv", [["01.08.2026", "K-1", "Termos", "1", "530"],
                               ["01.08.2026", "K-1", "Defter A5", "2", "190"]])
    df, _, ist, _ = temizle([t], esleme)
    assert len(df) == 2 and df["siparis_anahtar"].nunique() == 1


@pytest.mark.parametrize("satir, parca", [
    (["", "", "", "", ""], "boş satır"),
    (["31.02.2026", "K-1", "Termos", "1", "530"], "geçersiz tarih"),
    (["01.08.2026", "K-1", "Termos", "1", "belirsiz"], "tutar"),
    (["01.08.2026", "K-1", "   ", "1", "530"], "ürün adı boş"),
    (["01.08.2026", "K-1", "Termos", "0", "530"], "adet"),
    (["01.08.2026", "K-1", "Termos", "1", "-5"], "negatif"),
])
def test_bozuk_satirlar_nedenle_atilir(esleme, satir, parca):
    iyi = ["02.08.2026", "K-9", "Defter A5", "1", "95"]
    df, atilan, ist, _ = temizle([tablo("Konak_x.csv", [iyi, satir])], esleme)
    assert len(df) == 1 and ist["bozuk"] == 1
    assert parca in atilan.iloc[0]["neden"]


def test_temizlenen_degerler(esleme):
    t = tablo("Kadıköy_2026-08.csv", [["03.08.2026", "K-1", "  Çay   Demlik Seti ", "2", "1.280,50 TL"]])
    df, _, _, _ = temizle([t], esleme)
    r = df.iloc[0]
    assert (r["tarih"], r["sube"], r["urun"], r["adet"], r["tutar"]) == (
        dt.date(2026, 8, 3), "Kadıköy", "Çay Demlik Seti", 2, 1280.5)


def test_tanimayan_sutun_tum_dosyalar_icin_raporlanir(esleme):
    kotu1 = tablo("a.csv", [["x"]], ["Tarih", "Ürün", "Kazanç"])
    kotu2 = tablo("b.csv", [["x"]], ["Gün", "Ürün", "Tutar"])
    with pytest.raises(RaporHatasi) as e:
        temizle([kotu1, kotu2], esleme)
    assert "a.csv" in str(e.value) and "b.csv" in str(e.value)


def test_hic_gecerli_satir_yoksa_hata(esleme):
    with pytest.raises(RaporHatasi):
        temizle([tablo("a.csv", [["", "", "", "", ""]])], esleme)
