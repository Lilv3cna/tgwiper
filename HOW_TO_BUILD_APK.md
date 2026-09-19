# طريقة بناء ملف APK حقيقي من المشروع ده (عبر Google Colab)

بيئتي الحالية مالهاش اتصال إنترنت ومفيهاش Android SDK/NDK، فمقدرش أعمل compile
للـ APK بنفسي. الطريقة الأسهل والمجانية إنك تستخدم **Google Colab** (عنده
إنترنت وبيئة Linux كاملة) عشان يبني الـ APK بالنيابة عنك. العملية بتاخد من
30 لحد 60 دقيقة في أول مرة (لأنه بينزّل Android NDK/SDK)، والمرات اللي بعد
كده أسرع بكتير.

## الخطوات

1. افتح https://colab.research.google.com واعمل **New notebook**.

2. ارفع الملفين دول لمجلد المشروع في Colab (من قايمة الملفات على الشمال،
   Upload):
   - `main.py`
   - `buildozer.spec`

   أو حطهم كلهم في مجلد اسمه `tgwiper` جوه Colab.

3. في أول خلية (cell) في Colab شغّل الأوامر دي عشان تثبّت الأدوات المطلوبة:

```
!sudo apt update
!sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf \
    libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
    libtinfo5 cmake libffi-dev libssl-dev
!pip install --upgrade buildozer cython==0.29.33
```

4. في خلية جديدة، ادخل مجلد المشروع وابدأ البناء:

```
%cd tgwiper
!buildozer -v android debug
```

   (لو ظهر سؤال عن قبول تراخيص Android SDK، اكتب `y` واضغط Enter لكل سؤال،
   أو خلي `android.accept_sdk_license = True` في buildozer.spec زي ما هي
   موجودة بالفعل عشان توافق أوتوماتيك).

5. لما البناء يخلص، الـ APK هيبقى موجود في مجلد `bin/` باسم شبيه بـ:
   `tgwiper-1.0-arm64-v8a_armeabi-v7a-debug.apk`

6. نزّل الملف على جهازك بالأمر ده في خلية جديدة:

```
from google.colab import files
import glob
apk_path = glob.glob("bin/*.apk")[0]
files.download(apk_path)
```

7. انقل ملف الـ APK لموبايلك (عن طريق تليجرام لنفسك مثلاً، أو USB)، وفعّل
   "السماح بالتثبيت من مصادر غير معروفة" في إعدادات أندرويد، وثبّته عادي.

## ملاحظات مهمة

- ده build **debug** (للتجربة الشخصية)، مش موقّع (signed) لرفعه على متجر
  Google Play — ده كافي تمامًا للاستخدام الشخصي على موبايلك.
- أول مرة تبني فيها المشروع، Buildozer بينزّل NDK كامل (حجمه كبير) فخد بالك
  من الوقت والمساحة في Colab.
- لو حصل خطأ في البناء، شغّل نفس أمر `buildozer -v android debug` تاني بعد
  قراءة رسالة الخطأ في الـ log — غالبًا بتكون مكتبة ناقصة أو نسخة مش متوافقة.
- التطبيق بيستخدم نفس منطق أداة التيرمينال اللي عملناها: بتدخل API ID/HASH +
  رقم التليفون + لينك القناة، بعدين كود الدخول (والباسورد لو عندك 2FA مفعّل)،
  وبعدين تختار نطاق الحذف من القائمة وتأكد قبل التنفيذ.
