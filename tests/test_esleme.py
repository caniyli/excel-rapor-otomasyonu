import json

import pytest

from rapor.esleme import baslik_normallestir, esleme_yukle, sutunlari_esle
from rapor.hatalar import RaporHatasi


@pytest.fixture(scope="module")
def esleme():
    return esleme_yukle()


def test_normallestir():
    assert baslik_normallestir("  Sipariş   Tarihi ") == "siparis tarihi"
    assert baslik_normallestir("TOPLAM (TL)") == "toplam tl"
    assert baslik_normallestir("İşlem Tarihi") == baslik_normallestir("islem tarihi")


@pytest.mark.parametrize("basliklar, beklenen", [
    (["Tarih", "Sipariş No", "Ürün", "Adet", "Tutar"],
     {"tarih": 0, "siparis_no": 1, "urun": 2, "adet": 3, "tutar": 4}),
    (["tarih", "Sipariş No", "Ürün Adı", "Miktar", "Toplam (TL)"],
     {"tarih": 0, "siparis_no": 1, "urun": 2, "adet": 3, "tutar": 4}),
    (["Sipariş Tarihi", "Fiş No", "Ürün", "Adet", "Tutar (TL)"],
     {"tarih": 0, "siparis_no": 1, "urun": 2, "adet": 3, "tutar": 4}),
    (["TUTAR", "urun", "siparis tarihi"], {"tutar": 0, "urun": 1, "tarih": 2}),
])
def test_sutun_esleme(esleme, basliklar, beklenen):
    bulunan, tanimayan = sutunlari_esle("x.csv", basliklar, esleme)
    assert bulunan == beklenen
    assert tanimayan == []


def test_tanimayan_sutun_uyari_olarak_doner(esleme):
    _, tanimayan = sutunlari_esle("x.csv", ["Tarih", "Ürün", "Tutar", "Not"], esleme)
    assert tanimayan == ["Not"]


def test_zorunlu_sutun_yoksa_dosya_ve_sutun_adi_hatada(esleme):
    with pytest.raises(RaporHatasi) as e:
        sutunlari_esle("kadikoy.csv", ["Tarih", "Ürün", "Kazanç"], esleme)
    mesaj = str(e.value)
    assert "kadikoy.csv" in mesaj and "tutar" in mesaj and "Kazanç" in mesaj


def test_ozel_esleme_dosyasi(tmp_path):
    yol = tmp_path / "e.json"
    yol.write_text(json.dumps({"tarih": ["Gün"], "urun": ["Mal"], "tutar": ["Kazanç"]}),
                   encoding="utf-8")
    es = esleme_yukle(yol)
    bulunan, _ = sutunlari_esle("x.csv", ["Gün", "Mal", "Kazanç"], es)
    assert bulunan == {"tarih": 0, "urun": 1, "tutar": 2}


def test_bozuk_esleme_dosyasi(tmp_path):
    yol = tmp_path / "e.json"
    yol.write_text("{bozuk", encoding="utf-8")
    with pytest.raises(RaporHatasi):
        esleme_yukle(yol)
