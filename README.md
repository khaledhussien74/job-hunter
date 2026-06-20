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

6. **فلتر المكان (Location):** الوظيفة تعدّي بس لو مكانها:
   - **الخليج:** السعودية/الرياض/جدة، الإمارات/دبي/أبوظبي، قطر/الدوحة، الكويت،
     عُمان/مسقط، البحرين.
   - **مصر:** Egypt / Cairo.
   - **ريموت مفتوح عالميًا:** Remote / Worldwide / Anywhere / Global (من غير
     تقييد دولة).

   وبتترفض لو مكانها في **أوروبا أو أمريكا أو مقيّدة بيهم** (زي `Remote - US`،
   `Remote – Netherlands`، `Amsterdam`، `New York`، `Germany`، `UK`، `EU`،
   `EMEA` … أو أي مدينة أوروبية/أمريكية).
   لو المكان مش واضح أو فاضي، البوت بيعتبرها **ريموت عالمي** وبيخليها تعدّي.

> 💱 أسعار الصرف موجودة في قاموس `FX_TO_EGP` جوّه `job_hunter.py` — عدّلها لما
> السعر يتغير. (الدولار مثلًا متحط افتراضيًا بـ 50 جنيه.)

---

## 🌐 المصادر (كلها مجانية وقانونية)

شغّالة بدون أي مفاتيح:
**Remotive، RemoteOK، Jobicy، Arbeitnow، Himalayas، We Work Remotely (RSS)،
The Muse، Findwork.**

مصادر تجميعية (aggregators) محتاجة مفتاح مجاني (اختيارية — البوت بيشتغل من غيرها
بس تغطيتها بتكبر معاها جدًا):
**Adzuna** و **Jooble**.

---

## 🔐 الإعداد (Environment Variables)

البوت بيقرا القيم الحساسة من environment variables (مش متخزنة جوّه الكود):

| المتغير | إجباري؟ | إيه هو |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | توكن بوت التيليجرام |
| `TELEGRAM_CHAT_ID` | ✅ | رقم الـ chat اللي هيوصله الرسايل |
| `ADZUNA_APP_ID` | اختياري | لتفعيل Adzuna |
| `ADZUNA_APP_KEY` | اختياري | لتفعيل Adzuna |
| `JOOBLE_API_KEY` | اختياري | لتفعيل Jooble |

### تشغيل محلي (للتجربة)

```bash
export TELEGRAM_BOT_TOKEN="ضع_التوكن_هنا"
export TELEGRAM_CHAT_ID="ضع_الـchat_id_هنا"
# اختياري:
export ADZUNA_APP_ID="..."
export ADZUNA_APP_KEY="..."
export JOOBLE_API_KEY="..."

python job_hunter.py --once     # تشغيل مرة واحدة
python job_hunter.py            # تشغيل مستمر كل ٢٠ دقيقة
```

---

## 🤖 التشغيل التلقائي ٢٤ ساعة (GitHub Actions)

في ملف `.github/workflows/job-hunter.yml` بيشغّل البوت **كل ٢٠ دقيقة** تلقائيًا،
بياخد القيم من **GitHub Secrets**، وبيحفظ `seen_jobs.json` بين التشغيلات (بيعمله
commit ورا كل مرة) عشان الوظايف ماتتكررش.

> ملاحظة: مواعيد الـ cron في GitHub أحيانًا بتتأخر شوية وقت الزحمة، ده طبيعي.

---

## 📌 خطوات لازم تعملها بنفسك

### ١) تجيب توكن بوت التيليجرام و الـ chat id
1. على تيليجرام كلّم **@BotFather** → ابعت `/newbot` → اختار اسم ويوزرنيم →
   هيديك **التوكن** (ده `TELEGRAM_BOT_TOKEN`).
2. ابعت أي رسالة لبوتك الجديد.
3. افتح في المتصفح: `https://api.telegram.org/bot<التوكن>/getUpdates`
   وهتلاقي `"chat":{"id": ...}` — الرقم ده هو `TELEGRAM_CHAT_ID`.

### ٢) تسجّل في Adzuna وتجيب الـ keys (مجاني)
1. ادخل **https://developer.adzuna.com/** واعمل **Register / Sign up**.
2. فعّل الإيميل وادخل على **Dashboard / My Apps**.
3. هتلاقي **Application ID** = `ADZUNA_APP_ID` و **Application Key** = `ADZUNA_APP_KEY`.

### ٣) تسجّل في Jooble وتجيب الـ key (مجاني)
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
   - `ADZUNA_APP_ID`       (لو سجّلت في Adzuna)
   - `ADZUNA_APP_KEY`      (لو سجّلت في Adzuna)
   - `JOOBLE_API_KEY`      (لو سجّلت في Jooble)

### ٥) تتأكد إن الـ Actions شغّالة
1. روح تاب **Actions** في الريبو، ولو ظهرلك زرار تفعيل اضغط عليه.
2. اختار workflow اسمه **Job Hunter** واضغط **Run workflow** عشان تجرّبه يدوي.
3. تابع الـ logs، ولو كله تمام هتبدأ توصلك الوظايف على تيليجرام، وبعد كده
   هيشتغل لوحده كل ٢٠ دقيقة.

> 💡 لو عايز تظبط الحد الأدنى للمرتب أو أسعار الصرف، عدّل `MIN_EGP_PER_MONTH`
> و `FX_TO_EGP` في أول ملف `job_hunter.py`.
