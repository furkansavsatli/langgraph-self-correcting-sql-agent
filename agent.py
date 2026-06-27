import os
import sqlite3
from typing import TypedDict, Optional, List, Dict, Any
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

# 1. .env dosyasındaki API anahtarlarını yüklüyoruz
load_dotenv()

DB_NAME = "e_ticaret.db"


# 2. LANGGRAPH STATE (Grafiğin Ortak Hafızası)
# Grafikteki her düğüm bu sınıfı okuyacak ve güncelleyecek.
class AgentState(TypedDict):
    question: str  # Kullanıcının sorduğu doğal dildeki soru
    generated_sql: Optional[str]  # LLM tarafından üretilen SQL sorgusu
    error_message: Optional[str]  # Eğer SQL çalışırken hata alırsak veritabanının fırlattığı hata
    query_result: Optional[List]  # SQL başarıyla çalışırsa veritabanından dönen ham veri rows
    retry_count: int  # Hata düzeltme döngüsüne kaçıncı kez girdiğimiz (Maks 3)
    final_response: Optional[str]  # Kullanıcıya döneceğimiz doğal dildeki nihai rapor


# 3. VERİTABANI ŞEMASINI OKUYAN YARDIMCI FONKSİYON
# LLM'e körü körüne SQL yazdırmıyoruz. Ona tabloları ve kolonları bu fonksiyonla besleyeceğiz.
def get_db_schema() -> str:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Veritabanındaki tüm tabloları ve CREATE komutlarını çekiyoruz
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = cursor.fetchall()

    schema_text = ""
    for table_name, create_sql in tables:
        schema_text += f"Table: {table_name}\n"
        schema_text += f"{create_sql}\n"
        schema_text += "-" * 40 + "\n"

    conn.close()
    return schema_text


# 4. LLM MODELİNİ AYAĞA KALDIRMA (Groq - Llama 3)
# Sıcaklığı (temperature) 0 yapıyoruz ki model kafasına göre değil, tamamen deterministik SQL yazsın.
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)

# 5. SQL ÜRETEN İŞÇİ (GENERATE SQL NODE)
def generate_sql_node(state: AgentState) -> Dict[str, Any]:
    print("\n--- [NODE] SQL Üretim Düğümü Çalışıyor ---")

    # State'ten (not defterinden) kullanıcının sorusunu ve varsa önceki hatayı alıyoruz
    question = state["question"]
    error_message = state.get("error_message")
    schema = get_db_schema()

    # Modelin sadece temiz bir SQL dönmesi için katı bir System Prompt yazıyoruz
    system_prompt = (
        "Sen kurumsal bir e-ticaret veritabanında çalışan kıdemli bir SQL uzmanısın.\n"
        "Sana verilen veritabanı şemasına göre kullanıcının sorusunu çözecek bir SQLite sorgusu yazmalısın.\n\n"
        "KURALLAR:\n"
        "1. Sadece ve sadece geçerli bir SQL sorgusu dön. Açıklama yapma, 'İşte sorgunuz' deme.\n"
        "2. Çıktıda markdown (```sql) formatı kullanma, sadece ham metin olarak SQL cümlesini dön.\n"
        "3. Tablo ve kolon isimleri için sana verilen şemaya kesinlikle sadık kal.\n"
        "4. Eğer sana bir önceki adımdan kalan bir hata mesajı verildiyse, o hatayı analiz et ve sorgunu düzelterek tekrar yaz."
    )

    # Kullanıcı içeriği (Burada şemayı, soruyu ve varsa hatayı modele paslıyoruz)
    user_content = f"Veritabanı Şeması:\n{schema}\n\nKullanıcı Sorusu: {question}\n"
    if error_message:
        user_content += f"\n⚠️ ÖNEMLİ: Bir önceki denemede şu SQL hatasını aldın, sorguyu buna göre düzelt:\n{error_message}\n"

    # Prompt şablonunu oluşturup modeli çağırıyoruz
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_content)
    ])

    chain = prompt | llm
    response = chain.invoke({})

    generated_sql = response.content.strip()
    print(f"🤖 Modelin Ürettiği SQL:\n{generated_sql}")

    # Düğüm işini bitirince sadece güncellediği alanları return eder.
    # LangGraph arkada bu dönen veriyi ana State ile otomatik olarak merge (birleştirme) yapar.
    return {"generated_sql": generated_sql}


# 6. SQL ÇALIŞTIRAN İŞÇİ (EXECUTE SQL NODE) - HATA SİMÜLASYONLU
def execute_sql_node(state: AgentState) -> Dict[str, Any]:
    print("\n--- [NODE] SQL Çalıştırma Düğümü Çalışıyor ---")

    generated_sql = state["generated_sql"]
    current_retry = state.get("retry_count", 0)

    # 🔥 SELF-CORRECTION TESTİ İÇİN YAPAY HATA ENJEKSİYONU (Sadece ilk denemede)
    if current_retry == 0:
        print("⚠️ [SİMÜLASYON] İlk denemede yapay bir SQL hatası fırlatılıyor...")
        fake_error = "sqlite3.OperationalError: no such column: urunler.olmayan_kolon"

        return {
            "error_message": fake_error,
            "retry_count": current_retry + 1,
            "query_result": None
        }

    # İkinci denemede burası çalışacak (Gerçek veritabanı süreci)
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(generated_sql)
        rows = cursor.fetchall()
        conn.close()

        print("✅ SQL Başarıyla Çalıştırıldı! Veriler çekildi.")
        return {
            "query_result": rows,
            "error_message": None
        }

    except sqlite3.Error as e:
        error_msg = str(e)
        print(f"❌ Gerçek SQL Hatası Yakalandı: {error_msg}")
        return {
            "error_message": error_msg,
            "retry_count": current_retry + 1,
            "query_result": None
        }

# 7. CEVAP BİÇİMLENDİREN İŞÇİ (FORMAT ANSWER NODE)
# Veritabanından gelen ham veriyi (örn: [(15000.0, 8)]) alıp insan diline çevirir.
def format_answer_node(state: AgentState) -> Dict[str, Any]:
    print("\n--- [NODE] Cevap Biçimlendirme Düğümü Çalışıyor ---")

    question = state["question"]
    query_result = state["query_result"]
    error_message = state.get("error_message")

    # Eğer 3 denemede de hata çözülemediyse ve buraya düştüyse kullanıcıya kibar bir hata dönelim
    if error_message and not query_result:
        return {"final_response": f"Üzgünüm, istediğiniz veriye ulaşırken teknik bir hata oluştu: {error_message}"}

    if not query_result:
        return {"final_response": "Aradığınız kriterlere uygun herhangi bir kayıt bulunamadı."}

    system_prompt = (
        "Sen bir e-ticaret veri analistisin. Veritabanından gelen ham SQL sonuçlarını alıp, "
        "kullanıcının sorusuna samimi, net ve profesyonel bir Türkçe ile cevap vermelisin.\n"
        "Cevabında teknik SQL detaylarından (tablo adı, join vs.) bahsetme, doğrudan bir cümle kur."
    )

    user_content = f"Kullanıcının Sorusu: {question}\nVeritabanından Dönen Ham Veri: {str(query_result)}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_content)
    ])

    chain = prompt | llm
    response = chain.invoke({})

    return {"final_response": response.content.strip()}


# 8. KARAR MEKANİZMASI (ROUTER - CONDITIONAL EDGE)
# Akışın başa mı döneceğine yoksa cevaba mı gideceğine karar veren düz Python fonksiyonu.
def decide_next_step(state: AgentState) -> str:
    print("\n--- [EDGE] Karar Mekanizması Devrede ---")
    error_message = state.get("error_message")
    retry_count = state.get("retry_count", 0)

    # Eğer hata varsa kontrol ediyoruz
    if error_message:
        if retry_count >= 3:
            print(f"⚠️ Maksimum deneme sayısına ({retry_count}) ulaşıldı! Hata düzeltilemedi.")
            return "go_to_format"
        print(f"🔄 Hata tespit edildi! SQL Üretim düğümüne geri fırlatılıyor. (Deneme: {retry_count}/3)")
        return "loop_back"

    print("🚀 Hata yok, akış doğrudan Cevap Biçimlendirme düğümüne ilerliyor.")
    return "go_to_format"


# 9. LABİRENTİ (GRAFİĞİ) İNŞA ETME VE DERLEME
workflow = StateGraph(AgentState)

# İşçileri (Düğümleri) labirente yerleştiriyoruz
workflow.add_node("generate_sql_node", generate_sql_node)
workflow.add_node("execute_sql_node", execute_sql_node)
workflow.add_node("format_answer_node", format_answer_node)

# Çelik duvarları (Okları) çiziyoruz
workflow.set_entry_point("generate_sql_node")  # Başlangıç noktası
workflow.add_edge("generate_sql_node", "execute_sql_node")  # Düz yol

# Meşhur döngüsel/koşullu yol ayrımı
workflow.add_conditional_edges(
    "execute_sql_node",  # Hangi düğümden sonra karar verilecek?
    decide_next_step,  # Kararı hangi fonksiyon verecek?
    {
        "loop_back": "generate_sql_node",  # Eğer fonksiyon 'loop_back' dönerse buraya git
        "go_to_format": "format_answer_node"  # Eğer fonksiyon 'go_to_format' dönerse buraya git
    }
)

# Cevap hazırlandıktan sonra akışı bitiriyoruz
workflow.add_edge("format_answer_node", END)

# Grafiği derleyip çalıştırılabilir bir uygulama haline getiriyoruz
app = workflow.compile()

# 10. ÇALIŞTIRMA VE TEST (MAIN)
if __name__ == "__main__":
    print("\n=== SİSTEM HAZIR. TEST BAŞLIYOR ===")

    # Test Sorusu: Modelin JOIN atmasını gerektiren akıllıca bir soru soruyoruz
    test_inputs = {
        "question": "Stoğu 10'dan az olan kritik ürünlerin isimlerini ve hangi tedarikçiden alındıklarını söyler misin?",
        "retry_count": 0
    }

    # Grafiği tetikliyoruz
    final_state = app.invoke(test_inputs)

    print("\n========================================")
    print("🤖 NİHAİ YAPAY ZEKA CEVABI:")
    print(final_state["final_response"])
    print("========================================")