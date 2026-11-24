"""Türkçe biçimli sayı ve tarihleri ayrıştıran küçük yardımcılar."""
import datetime as dt
import math
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_PARA_EKI = re.compile(r"(?i)(₺|\btl\b|\btry\b)")
_TARIH_ISO = re.compile(r"^(\d{4})[-./](\d{1,2})[-./](\d{1,2})(?:[ T].*)?$")
_TARIH_GUN_ONCE = re.compile(r"^(\d{1,2})[-./](\d{1,2})[-./](\d{4})(?:[ T].*)?$")
_BINLIK_NOKTA = re.compile(r"^[-+]?\d{1,3}(\.\d{3})+$")


def metin_temizle(deger):
    """Hücre değerini düz metne çevirir; baştaki/sondaki ve çift boşlukları atar."""
    if deger is None:
        return ""
    if isinstance(deger, float) and math.isnan(deger):
        return ""
    return re.sub(r"\s+", " ", str(deger).replace("\xa0", " ")).strip()


def sayi_ayristir(deger):
    """'1.234,50', '1234,5', '1.250 TL', 12.5 gibi değerleri Decimal yapar.

    Kurallar (Türkiye biçimi öncelikli):
      * hem nokta hem virgül varsa sonuncusu ondalık ayraçtır,
      * yalnız virgül varsa ondalıktır ('1,5' -> 1.5),
      * yalnız nokta varsa ve '1.234' / '12.345.678' biçimindeyse binliktir,
        aksi halde ('12.5') ondalıktır.
    Okunamıyorsa ValueError fırlatır.
    """
    if isinstance(deger, bool):
        raise ValueError("sayı değil")
    if isinstance(deger, (int, float, Decimal)):
        if isinstance(deger, float) and (math.isnan(deger) or math.isinf(deger)):
            raise ValueError("sayı değil")
        return Decimal(str(deger))
    s = _PARA_EKI.sub("", metin_temizle(deger)).replace(" ", "")
    if not s or not re.fullmatch(r"[-+]?[\d.,]+", s) or not re.search(r"\d", s):
        raise ValueError("sayı okunamadı: {!r}".format(metin_temizle(deger)))
    if "," in s and "." in s:
        ondalik = "," if s.rfind(",") > s.rfind(".") else "."
        binlik = "." if ondalik == "," else ","
    elif "," in s:
        ondalik, binlik = (",", ".") if s.count(",") == 1 else (None, ",")
    elif "." in s:
        if _BINLIK_NOKTA.match(s):
            ondalik, binlik = None, "."
        elif s.count(".") == 1:
            ondalik, binlik = ".", None
        else:
            raise ValueError("sayı okunamadı: {!r}".format(s))
    else:
        ondalik, binlik = None, None
    if binlik:
        s = s.replace(binlik, "")
    if ondalik and ondalik != ".":
        s = s.replace(ondalik, ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError("sayı okunamadı: {!r}".format(s))


def tutar_ayristir(deger):
    """Para tutarını 2 ondalığa yuvarlanmış float olarak döndürür."""
    return float(sayi_ayristir(deger).quantize(Decimal("0.01"), ROUND_HALF_UP))


def adet_ayristir(deger):
    """Pozitif tam sayı adet; aksi halde ValueError."""
    sayi = sayi_ayristir(deger)
    if sayi != sayi.to_integral_value() or sayi < 1:
        raise ValueError("adet geçersiz: {!r}".format(metin_temizle(deger)))
    return int(sayi)


def tarih_ayristir(deger):
    """'24.11.2026', '24/11/2026', '2026-11-24' ve Excel tarih hücrelerini date yapar.

    Noktalı/eğik çizgili biçimler gün-ay-yıl sırasıyla okunur (Türkiye düzeni).
    """
    if isinstance(deger, dt.datetime):
        return deger.date()
    if isinstance(deger, dt.date):
        return deger
    s = metin_temizle(deger)
    if not s:
        raise ValueError("tarih boş")
    m = _TARIH_ISO.match(s)
    if m:
        y, a, g = (int(x) for x in m.groups())
    else:
        m = _TARIH_GUN_ONCE.match(s)
        if not m:
            raise ValueError("tarih okunamadı: {!r}".format(s))
        g, a, y = (int(x) for x in m.groups())
    try:
        return dt.date(y, a, g)
    except ValueError:
        raise ValueError("geçersiz tarih: {!r}".format(s))
