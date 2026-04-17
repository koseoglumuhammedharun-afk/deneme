import pandas as pd
import os

# Senin verdiğin verilere göre dosya yolu
csv_path = r'C:\Users\CASPER\Desktop\drone_detection\training_data\models\custom_howitzer7\results.csv'

if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    
    # Sütun isimlerindeki boşlukları temizleyelim
    df.columns = df.columns.str.strip()
    
    # mAP50 değerini alalım
    max_map50 = df['metrics/mAP50(B)'].max()
    last_epoch = df['epoch'].max()
    
    print("-" * 30)
    print(f"7. EĞİTİM ANALİZİ")
    print("-" * 30)
    print(f"Tamamlanan Epoch: {last_epoch}")
    print(f"En Yüksek Başarı (mAP50): %{max_map50 * 100:.2f}")
    print("-" * 30)
    
    if max_map50 > 0.8:
        print("Yorum: Modelin canavar gibi olmuş, drone'ları kaçırmaz!")
    else:
        print("Yorum: Biraz daha veriye veya eğitime ihtiyacı olabilir.")
else:
    print("Hata: results.csv dosyası belirtilen yolda bulunamadı!")