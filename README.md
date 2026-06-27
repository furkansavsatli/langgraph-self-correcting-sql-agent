# 🤖 Self-Correcting SQL Analyst Agent (AI Veri Analisti)

Bu proje, doğal dilde sorulan soruları akıllıca SQL sorgularına dönüştüren, ilişkisel bir veritabanında çalıştıran ve hata alması durumunda **kendi hatasını otomatik olarak düzelten (Self-Correction)** döngüsel bir yapay zeka ajanı (AI Agent) uygulamasıdır.

Geleneksel LLM zincirlerinin (Chains) aksine, bu proje **LangGraph** kullanılarak bir durum makinesi (State Machine) olarak tasarlanmıştır. Bu sayede sistem, veritabanından bir hata aldığında çökmek yerine, hatayı analiz eder, şemayı tekrar inceler ve sorguyu revize ederek yeniden dener.

---

## 🏗️ Mimari ve Akış Diyagramı

Sistem, LangGraph düğümleri (Nodes) ve koşullu kenarlar (Conditional Edges) üzerinde doğrusal olmayan bir akış izler:

```text
               +-----------------------+
               |   Kullanıcı Sorusu    |
               +-----------+-----------+
                           |
                           v
             +-------------+-------------+
             |    generate_sql_node      | <------+
             | (SQL Sorgusu Üretim)      |        |
             +-------------+-------------+        |
                           |                      |
                           v                      | (Hata Var & Deneme < 3)
             +-------------+-------------+        | [loop_back]
             |     execute_sql_node      |        |
             |  (Veritabanı Çalıştırma)  |        |
             +-------------+-------------+        |
                           |                      |
                           v                      |
             +-------------+-------------+        |
             |     decide_next_step      |--------+
             |    (Router / Karar)       |
             +-------------+-------------+
                           |
                           | (Hata Yok VEYA Deneme >= 3)
                           | [go_to_format]
                           v
             +-------------+-------------+
             |    format_answer_node     |
             |   (Türkçe Cevap Üretim)   |
             +-------------+-------------+
                           |
                           v
                 +---------+---------+
                 |    Nihai Cevap    |
                 +-------------------+
```

### 🧠 Ajan Nasıl Kendi Kendini Düzeltiyor?
1. **Hafıza Yönetimi (State):** Tüm düğümler `AgentState` adı verilen ortak bir veri sözlüğünü (not defterini) okur ve günceller.
2. **Hata Yakalama (Try-Catch):** SQL çalıştırma düğümünde oluşan herhangi bir veritabanı istisnası (`sqlite3.Error`), çiğ metin olarak yakalanır ve `error_message` alanına yazılır.
3. **Akıllı Revizyon:** Karar mekanizması akışı tekrar başa fırlattığında, SQL Üretim Düğümü sistem promptuna eklenen hata mesajını görür. Model, *"Önceki adımda şu kolonu bulamadım demiştin, şemaya baktım doğrusu şuymuş"* diyerek kodu revize eder.

---

## 🛠️ Kullanılan Teknolojiler ve Kütüphaneler

Proje, modern ve yüksek performanslı yapay zeka ajanı kütüphaneleri ve kurumsal standartlar dikkate alınarak geliştirilmiştir:

* **Python 3.11+**: Projenin ana programlama dili.
* **LangGraph (`langgraph`)**: Ajanın döngüsel durum makinesini (Graph) yönetmek, düğümleri ve koşullu geçişleri kurmak için kullanılan ana iskelet.
* **LangChain (`langchain` & `langchain-community`)**: Prompt şablonları (Prompt Templates) oluşturmak, zincirleri (`|` operatörü) yönetmek ve LLM entegrasyonu için kurumsal altyapı.
* **LangChain Groq (`langchain-groq`)**: Groq Cloud üzerindeki LLM modelleri ile entegrasyonu sağlayan resmi sürücü.
* **Groq Cloud (Llama-3.3-70b-versatile)**: Piyasadaki en hızlı LLM çıkarım (inference) motoru. `temperature=0` ayarlanarak tamamen deterministik ve tutarlı SQL üretimi sağlanmıştır.
* **SQLite3 (`sqlite3`)**: Yerel ilişkisel veritabanı motoru. (E-ticaret senaryosuna ait tabloları, ilişkileri ve mock verileri barındırır).
* **python-dotenv (`python-dotenv`)**: API anahtarlarının ve hassas konfigürasyonların kodun içine gömülmesini engelleyen kurumsal çevre değişkenleri yönetim kütüphanesi.

---

## 📂 Proje Yapısı

```text
├── .env                  # API Anahtarları ve Çevre Değişkenleri (Git'e yüklenmez!)
├── .gitignore            # Git tarafında takip edilmeyecek dosyalar (.env, .venv vb.)
├── agent.py              # LangGraph Ajan Tanımları, Düğümler ve Çalıştırma Kodu
├── e_ticaret.db          # Mock verilerle beslenmiş SQLite Veritabanı dosyası
└── README.md             # Proje dokümantasyonu
```

---

## ⚙️ Çevre Değişkenleri (Environment Variables)

Projenin çalışması için kök dizinde bir `.env` dosyası oluşturulmalı ve aşağıdaki değişkenler tanımlanmalıdır. **Güvenlik nedeniyle bu dosya kesinlikle GitHub'a pushlanmamalıdır!**

```text
# Groq Cloud API Anahtarı (Zorunlu)
GROQ_API_KEY=gsk_your_real_groq_api_key_here

# LangSmith İzlenebilirlik ve Analiz Ayarları (Opsiyonel)
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=lsv2_your_langsmith_key_here
# LANGCHAIN_PROJECT=Self-Correcting-SQL-Analyst
```

---

## 🚀 Kurulum ve Çalıştırma

### 1. Projeyi Klonlayın
```bash
git clone [https://github.com/kullanici_adiniz/langgraph-self-correcting-sql-agent.git](https://github.com/kullanici_adiniz/langgraph-self-correcting-sql-agent.git)
cd langgraph-self-correcting-sql-agent
```

### 2. Sanal Ortam (Virtual Environment) Oluşturun ve Aktif Edin
```bash
# Windows (PyCharm / VS Code terminali için)
python -m venv .venv
.\\.venv\\Scripts\\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Gerekli Kütüphaneleri Yükleyin
```bash
pip install langgraph langchain langchain-community langchain-groq python-dotenv
```

### 4. Uygulamayı Tetikleyin
```bash
python agent.py
```

---

## 📊 Örnek Konsol Çıktısı (Self-Correction Canlı Testi)

Aşağıda, sisteme ilk denemede yapay bir hata enjekte edildiğinde ajanın nasıl davrandığını gösteren log çıktısı yer almaktadır:

```text
=== SİSTEM HAZIR. TEST BAŞLIYOR ===

--- [NODE] SQL Üretim Düğümü Çalışıyor ---
🤖 Modelin Ürettiği SQL:
SELECT u.isim, t.isim FROM urunler u LEFT JOIN tedarikciler t ON u.tedarikci_id = t.id WHERE u.stok < 10

--- [NODE] SQL Çalıştırma Düğümü Çalışıyor ---
⚠️ [SİMÜLASYON] İlk denemede yapay bir SQL hatası fırlatılıyor...

--- [EDGE] Karar Mekanizması Devrede ---
🔄 Hata tespit edildi! SQL Üretim düğümüne geri fırlatılıyor. (Deneme: 1/3)

--- [NODE] SQL Üretim Düğümü Çalışıyor ---
🤖 Modelin Ürettiği SQL:
SELECT urunler.isim, tedarikciler.isim 
FROM urunler 
INNER JOIN tedarikciler 
ON urunler.tedarikci_id = tedarikciler.id 
WHERE urunler.stok < 10

--- [NODE] SQL Çalıştırma Düğümü Çalışıyor ---
✅ SQL Başarıyla Çalıştırıldı! Veriler çekildi.

--- [EDGE] Karar Mekanizması Devrede ---
🚀 Hata yok, akış doğrudan Cevap Biçimlendirme düğümüne ilerliyor.

--- [NODE] Cevap Biçimlendirme Düğümü Çalışıyor ---

========================================
🤖 NİHAİ YAPAY ZEKA CEVABI:
Stoğu 10'dan az olan kritik ürünler Akıllı Telefon ve Kışlık Mont olup, sırasıyla TeknoToptan ve ModaTekstil tedarikçilerinden alınmaktadır.
========================================
```

---

## 🔒 Kurumsal Entegrasyon Önerileri (Production Notes)

Eğer bu sistemi canlı bir mikroservis mimarisine taşımak isterseniz şu adımların atılması önerilir:
1. **Veritabanı Güvenliği (Guardrails):** Uygulamanın bağlandığı DB kullanıcısı sadece `Read-Only` yetkilere sahip olmalıdır. `DROP`, `DELETE` gibi zararlı komutları engellemek için SQL interceptor yazılmalıdır.
2. **Kalıcı Hafıza (Persistence):** RAM tabanlı hafıza yerine LangGraph'in `SqliteSaver` veya `RedisSaver` checkpointer mekanizmaları kullanılarak multi-user desteği eklenmelidir.
3. **API Katmanı:** Grafik akışı `FastAPI` ile sarmalanarak dış dünyaya bir REST API olarak sunulabilir.
```
