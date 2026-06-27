import sqlite3
import os

DB_NAME = "e_ticaret.db"

def init_db():
    # Eğer eski bir DB varsa temizle ki her seferinde sıfırdan temiz başlasın
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print("Tablolar oluşturuluyor...")

    # 1. Kategoriler Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kategoriler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isim TEXT NOT NULL UNIQUE
        )
    ''')

    # 2. Tedarikçiler Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tedarikciler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isim TEXT NOT NULL,
            telefon TEXT
        )
    ''')

    # 3. Ürünler Tablosu (Kategori ve Tedarikçi ile ilişkili)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS urunler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isim TEXT NOT NULL,
            kategori_id INTEGER,
            tedarikci_id INTEGER,
            fiyat REAL,
            stok INTEGER,
            FOREIGN KEY (kategori_id) REFERENCES kategoriler(id),
            FOREIGN KEY (tedarikci_id) REFERENCES tedarikciler(id)
        )
    ''')

    # 4. Müşteriler Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS musteriler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isim TEXT NOT NULL,
            email TEXT UNIQUE
        )
    ''')

    # 5. Siparişler Tablosu (Müşteri ile ilişkili)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS siparisler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            musteri_id INTEGER,
            siparis_tarihi DATE,
            FOREIGN KEY (musteri_id) REFERENCES musteriler(id)
        )
    ''')

    # 6. Sipariş Detayları Tablosu (Sipariş ve Ürün ile ilişkili)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS siparis_detaylari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            siparis_id INTEGER,
            urun_id INTEGER,
            adet INTEGER,
            birim_fiyat REAL,
            FOREIGN KEY (siparis_id) REFERENCES siparisler(id),
            FOREIGN KEY (urun_id) REFERENCES urunler(id)
        )
    ''')

    print("Sahte veriler yükleniyor...")

    # Veri Ekleme (Seed Data)
    kategoriler = [('Elektronik',), ('Kitap',), ('Giyim',), ('Ev & Yaşam',)]
    cursor.executemany("INSERT INTO kategoriler (isim) VALUES (?)", kategoriler)

    tedarikciler = [
        ('TeknoToptan', '05551112233'),
        ('Alfa Yayıncılık', '05552223344'),
        ('ModaTekstil', '05553334455'),
        ('YorganSepeti', '05554445566')
    ]
    cursor.executemany("INSERT INTO tedarikciler (isim, telefon) VALUES (?, ?)", tedarikciler)

    # urunler: (isim, kategori_id, tedarikci_id, fiyat, stok)
    urunler = [
        ('Laptop', 1, 1, 25000.0, 15),
        ('Akıllı Telefon', 1, 1, 15000.0, 8),
        ('Kablosuz Kulaklık', 1, 1, 2000.0, 50),
        ('Python 101 Kitabı', 2, 2, 250.0, 120),
        ('Dizayn Pattern Kitabı', 2, 2, 450.0, 40),
        ('Pamuklu Tişört', 3, 3, 350.0, 200),
        ('Kışlık Mont', 3, 3, 1800.0, 5),
        ('Kahve Makinesi', 4, 4, 3500.0, 25),
        ('Çalışma Masası', 4, 4, 1200.0, 12)
    ]
    cursor.executemany("INSERT INTO urunler (isim, kategori_id, tedarikci_id, fiyat, stok) VALUES (?, ?, ?, ?, ?)", urunler)

    musteriler = [
        ('Ahmet Yılmaz', 'ahmet@gmail.com'),
        ('Mehmet Demir', 'mehmet@yahoo.com'),
        ('Ayşe Kaya', 'ayse@hotmail.com'),
        ('Fatma Çelik', 'fatma@outlook.com'),
        ('Can Üstün', 'can@gmail.com')
    ]
    cursor.executemany("INSERT INTO musteriler (isim, email) VALUES (?, ?)", musteriler)

    # siparisler: (musteri_id, siparis_tarihi)
    siparisler = [
        (1, '2026-05-10'),
        (2, '2026-05-12'),
        (3, '2026-06-01'),
        (4, '2026-06-15'),
        (1, '2026-06-18'),
        (5, '2026-06-19')
    ]
    cursor.executemany("INSERT INTO siparisler (musteri_id, siparis_tarihi) VALUES (?, ?)", siparisler)

    # siparis_detaylari: (siparis_id, urun_id, adet, birim_fiyat)
    detaylar = [
        (1, 1, 1, 25000.0),
        (1, 3, 2, 2000.0),
        (2, 4, 1, 250.0),
        (3, 8, 1, 3500.0),
        (3, 6, 3, 350.0),
        (4, 7, 1, 1800.0),
        (5, 2, 1, 15000.0),
        (6, 5, 2, 450.0)
    ]
    cursor.executemany("INSERT INTO siparis_detaylari (siparis_id, urun_id, adet, birim_fiyat) VALUES (?, ?, ?, ?)", detaylar)

    conn.commit()
    conn.close()
    print("Veritabanı başarıyla oluşturuldu ve sahte verilerle dolduruldu!")

if __name__ == "__main__":
    init_db()