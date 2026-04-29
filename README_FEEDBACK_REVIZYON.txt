# Analiz Kırpıntı Feedback ve Aktif Öğrenme Revizyonu

Bu paket önceki confidence/kırpıntı revizyonunun üstüne şu özellikleri ekler:

1. Kırpıntı ekranında her tespit için eğitim feedback seçenekleri:
   - Doğru - Aynı Sınıfla Eğitime Ekle
   - Doğru - Seçilen Sınıfla Eğitime Ekle
   - Tam Kareyi Seçilen Sınıfla Kaydet
   - Yanlış Alarm - Kırpıntıyı Background'a Ekle
   - Hedef Var Ama Bu Kırpıntı Yanlış
   - Kutu Yanlış - Manuel Label'a At
   - Emin Değilim - İncelemeye At
   - Bulanık/Kullanılmaz - Reddet
   - Tekrar/Gereksiz Benzer - Ayır
   - Sadece Referans Olarak Sakla

2. Dışa aktarma:
   - Tek kırpıntıyı işaretli veya ham haliyle farklı kaydet.
   - Tüm kırpıntıları seçilen klasöre ham + işaretli PNG olarak kaydet.

3. Kalite:
   - Kaynak fotoğraf/video dosyasına dokunulmaz.
   - Eğitim feedback görselleri PNG olarak kaydedilir.
   - Ekranda küçültme sadece önizleme içindir.

4. Eğitim klasörlerine kayıt mantığı:
   - Yanlış alarm kırpıntısı:
     training_data/background/images/train/*.png
     training_data/background/labels/train/*.txt  (boş label)

   - Doğru pozitif parça:
     training_data/<kategori>/images/train/*.png
     training_data/<kategori>/labels/train/*.txt

5. Kritik güvenlik:
   - Karede gerçek silah varsa "Tam Karede Silah Yok" seçeneğini kullanma.
   - Bu durumda sadece yanlış kırpıntıyı background'a ekle.

Kopyalanacak dosyalar:
- config.py
- main.py
- gui/analysis_tab.py
- gui/workers.py
- src/detector.py
