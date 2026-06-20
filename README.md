# Job Hunter 🎯

بوت بيجمع وظايف **التسويق (Senior/Manager/Director)** الريموت من مصادر مجانية
وقانونية، بيطبّق عليها فلاتر دقيقة، وبيبعت **الجديد بس** على تيليجرام.

> ❌ مفيش أي scraping للينكدان أو Indeed أو Glassdoor أو Bayt — كله APIs و RSS رسمية.

---

## 🧠 إزاي البوت بيفلتر الوظايف

1. **Whitelist (العنوان لازم يحتوي واحدة من دي):**
   `marketing manager`, `digital marketing manager`, `performance marketing manager`,
   `marketing director`, `head of marketing`, `head of digital`,
   `senior marketing manager`, `senior marketing director`, `senior digital marketing`.

2. **Blacklist (يترفض لو العنوان فيه أي من دي):**
   `content creator`, `content writer`, `customer service`, `supervisor`,
   `specialist`, `coordinator`, `assistant`, `intern`, `internship`,
   `junior`, `graduate`, `trainee`, `entry`.

3. **فلتر المرتب:** لو الوظيفة كاتبة مرتب بأي عملة، البوت بيحوّله للجنيه المصري
   في الشهر (لو سنوي بيقسمه على ١٢) ولو طلع **أقل من ٥٠٬٠٠٠ جنيه شهريًا** بيستبعدها.
   لو مفيش مرتب مكتوب، الوظيفة بتعدّي عادي.

4. **استبعاد شرط الجنسية الخليجية:** بيترفض لو العنوان/الوصف فيه حاجة زي
   `Saudization`, `Saudi nationals only`, `Emiratization`, `nationals only`,
   `citizens only` … إلخ.

5. **استبعاد اللغة الأجنبية:** لو الوظيفة بتطلب إتقان لغة غير الإنجليزي والعربي
   (ألماني، فرنسي، إسباني، إيطالي … إلخ) بتترفض. بس لو اللغة مذكورة كـ
   "a plus" أو "nice to have" بس، البوت **مابيرفضهاش**.

6. **فلتر المكان (Location) — صارم (allow-list):** الوظيفة تعدّي **بس** لو
   مكانها أو **وصفها** بيحدد بوضوح إنها في:
   - **الخليج:** السعودية/الرياض/جدة، الإمارات/دبي/أبوظبي، قطر/الدوحة، الكويت،
     عُمان/مسقط، البحرين/المنامة.
   - **مصر:** Egypt / Cairo.
   - **منطقة بتشملهم:** MENA, Middle East, GCC, Gulf, Arab region.

   وأي حاجة غير كده **بتترفض** — أوروبا، أمريكا، كندا، كل دول آسيا غير الخليج،
   وكمان أي وظيفة مكانها **مش واضح أو فاضي** أو مكتوب
   `Remote / Worldwide / Anywhere` **من غير ذكر صريح** للخليج/مصر/MENA.

> 💱 أسعار الصرف موجودة في قاموس `FX_TO_EGP` جوّه `job_hunter.py` — عدّلها لما
> السعر يتغير. (الدولار مثلًا متحط افتراضيًا بـ 50 جنيه.)

---

## 🌐 المصادر (كلها مجانية وقانونية)

**المصدر الأساسي للخليج/مصر — Google Custom Search** (محتاج مفتاحين مجانيين):
محرك بحث مخصص (CSE) مربوط على Bayt و Wuzzuf و LinkedIn و NaukriGulf و
Glassdoor. البوت بيستخدم الـ **Google Custom Search JSON API** ويبحث عن
المسميات (marketing manager / digital marketing manager / performance
marketing manager / marketing director / head of marketing / head of digital)
مدموجة بكلمات أماكن الخليج/مصر. **بيستخدم بس (العنوان + اللينك + المقتطف)
اللي بترجّعه الـAPI — مبيسحبش صفحة الوظيفة نفسها** التزامًا بشروط المواقع دي.

> ⚠️ **حدود الخطة المجانية:** Google CSE مجاني لحد **١٠٠ بحث في اليوم**.
> عشان كده البوت بيعمل **٦ بحثات بس في كل تشغيلة** (بحد أقصى ٧)، والـ workflow
> بيشتغل **كل ٣ ساعات** (≈٨ مرات/يوم) → ٦×٨ = ٤٨ بحث/يوم، تحت الحد بأمان.

شغّالة بدون أي مفاتيح:
**Remotive، RemoteOK، Jobicy، Arbeitnow، Himalayas، We Work Remotely (RSS)،
The Muse، Findwork.**

مصدر تجميعي إضافي محتاج مفتاح مجاني (اختياري):
**Jooble** — والبوت بيطلب منه كل دولة لوحدها (مصر، الإمارات، السعودية، قطر،
الكويت، عُمان، البحرين) عشان يرجّع المناطق دي بس من المصدر نفسه.

> ℹ️ **Adzuna اتشال** لأنه مبيغطّيش الخليج/مصر (بيرجّع أمريكا/أوروبا) فكان
> بيضيف نويز من غير فايدة.

---

## 🔐 الإعداد (Environment Variables)

البوت بيقرا القيم الحساسة من environment variables (مش متخزنة جوّه الكود):

| المتغير | إجباري؟ | إيه هو |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | توكن بوت التيليجرام |
| `TELEGRAM_CHAT_ID` | ✅ | رقم الـ chat اللي هيوصله الرسايل |
| `GOOGLE_API_KEY` | للمصدر الأساسي | مفتاح Google Custom Search JSON API |
| `GOOGLE_CSE_ID` | للمصدر الأساسي | معرّف محرك البحث المخصص (cx) |
| `JOOBLE_API_KEY` | اختياري | لتفعيل Jooble |

### تشغيل محلي (للتجربة)

```bash
export TELEGRAM_BOT_TOKEN="ضع_التوكن_هنا"
export TELEGRAM_CHAT_ID="ضع_الـchat_id_هنا"
# للمصدر الأساسي (Google):
export GOOGLE_API_KEY="..."
export GOOGLE_CSE_ID="..."
# اختياري:
export JOOBLE_API_KEY="..."

python job_hunter.py --once     # تشغيل مرة واحدة
python job_hunter.py            # تشغيل مستمر
```

---

## 🤖 التشغيل التلقائي ٢٤ ساعة (GitHub Actions)

ملف `.github/workflows/job-hunter.yml` بيشغّل البوت **كل ٣ ساعات** تلقائيًا
(عشان نفضل تحت حد Google CSE المجاني ١٠٠ بحث/يوم)، بياخد القيم من
**GitHub Secrets**، وبيحفظ `seen_jobs.json` بين التشغيلات (بيعمله commit ورا كل
مرة) عشان الوظايف ماتتكررش.

> ملاحظة: مواعيد الـ cron في GitHub أحيانًا بتتأخر شوية وقت الزحمة، ده طبيعي.

---

## 📌 خطوات لازم تعملها بنفسك

### ١) تجيب توكن بوت التيليجرام و الـ chat id
1. على تيليجرام كلّم **@BotFather** → ابعت `/newbot` → اختار اسم ويوزرنيم →
   هيديك **التوكن** (ده `TELEGRAM_BOT_TOKEN`).
2. ابعت أي رسالة لبوتك الجديد.
3. افتح في المتصفح: `https://api.telegram.org/bot<التوكن>/getUpdates`
   وهتلاقي `"chat":{"id": ...}` — الرقم ده هو `TELEGRAM_CHAT_ID`.

### ٢) تجهّز Google Custom Search (المصدر الأساسي)
**أ) اعمل محرك بحث مخصص (CSE) وتجيب الـ `GOOGLE_CSE_ID`:**
1. ادخل **https://programmablesearchengine.google.com/** واعمل **Add / Create**.
2. في **Sites to search** ضيف المواقع اللي عايز تبحث جوّاها، مثلًا:
   `bayt.com`، `wuzzuf.net`، `linkedin.com/jobs`، `naukrigulf.com`،
   `glassdoor.com`.
3. بعد الإنشاء افتح **Control Panel** وهتلاقي **Search engine ID** — ده
   `GOOGLE_CSE_ID` (الـ cx).

**ب) تفعّل الـ API وتجيب الـ `GOOGLE_API_KEY`:**
1. ادخل **https://console.cloud.google.com/** واعمل مشروع جديد (أو اختار واحد).
2. من **APIs & Services → Library** دوّر على **Custom Search API** واضغط
   **Enable**.
3. من **APIs & Services → Credentials** اضغط **Create credentials → API key**
   — ده `GOOGLE_API_KEY`.

> 💡 الخطة المجانية ١٠٠ بحث/يوم. البوت متظبّط يفضل تحتها (٦ بحثات/تشغيلة، كل ٣ ساعات).

### ٣) تسجّل في Jooble وتجيب الـ key (اختياري)
1. ادخل **https://jooble.org/api/about**.
2. اضغط **Get API key** / **Get a free key** واملأ بياناتك.
3. هيوصلك مفتاح (سلسلة حروف وأرقام) = `JOOBLE_API_KEY`.

### ٤) تضيف القيم في GitHub Secrets (خطوة بخطوة)
1. افتح صفحة الريبو على GitHub.
2. **Settings** (من فوق) ← من القايمة الشمال: **Secrets and variables** ← **Actions**.
3. اضغط زرار **New repository secret**.
4. في خانة **Name** اكتب اسم المتغير بالظبط، وفي **Secret** اكتب القيمة، وبعدين **Add secret**.
5. كرّر الخطوة لكل واحد من دول:
   - `TELEGRAM_BOT_TOKEN`  (إجباري)
   - `TELEGRAM_CHAT_ID`    (إجباري)
   - `GOOGLE_API_KEY`      (للمصدر الأساسي)
   - `GOOGLE_CSE_ID`       (للمصدر الأساسي)
   - `JOOBLE_API_KEY`      (لو سجّلت في Jooble)

### ٥) تتأكد إن الـ Actions شغّالة
1. روح تاب **Actions** في الريبو، ولو ظهرلك زرار تفعيل اضغط عليه.
2. اختار workflow اسمه **Job Hunter** واضغط **Run workflow** عشان تجرّبه يدوي.
3. تابع الـ logs، ولو كله تمام هتبدأ توصلك الوظايف على تيليجرام، وبعد كده
   هيشتغل لوحده كل ٣ ساعات.

> 💡 لو عايز تظبط الحد الأدنى للمرتب أو أسعار الصرف، عدّل `MIN_EGP_PER_MONTH`
> و `FX_TO_EGP` في أول ملف `job_hunter.py`.
