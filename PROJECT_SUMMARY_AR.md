# 📋 ملخّص مشروع Job Hunter — ملف تسليم وإكمال

> **إزاي تستخدم الملف ده:** في أي وقت تحب تكمّل الشغل، ابعت الملف ده للمساعد
> (Claude في الشات أو Claude Code) وقوله "كمّل من هنا". الملف فيه كل حاجة عن
> المشروع: الفكرة، الملفات، الفلاتر، ميزة الـ CV، اللي خلص، واللي لسه ناقص.
>
> **الريبو:** https://github.com/khaledhussien74/job-hunter
> **آخر تحديث للملخّص:** بعد إضافة ميزة الـ CV المجانية (إجمالي ~٥ ساعات شغل).

---

## 🎯 الفكرة باختصار

بوت بايثون بيدوّر على وظايف **تسويق (Manager / Director / Head)** في الخليج
ومصر (أو ريموت مفتوح)، من مصادر **مجانية وقانونية** بس، بيطبّق فلاتر دقيقة،
وبيبعت **الجديد بس** على تيليجرام — ومع كل وظيفة بيرفق **نسخة CV مخصّصة** للوظيفة.

> ❌ ممنوع تمامًا أي scraping للينكدان / Indeed / Glassdoor / Bayt — كله APIs و RSS رسمية.

---

## 🗂️ ملفات المشروع

| الملف | دوره |
|---|---|
| `job_hunter.py` | البوت الأساسي: المصادر + الفلاتر + الإرسال لتيليجرام |
| `cv_tailor.py` | **(جديد)** تفصيل الـ CV لكل وظيفة + توليد PDF متوافق مع ATS |
| `cv_master.json` | **(جديد)** الـ CV الماستر منظّم — مصدر الحقيقة للتفصيل |
| `README.md` | شرح كامل بالعربي + خطوات الإعداد |
| `.github/workflows/job-hunter.yml` | التشغيل التلقائي كل ٣ ساعات على GitHub Actions |
| `seen_jobs.json` | الوظايف اللي اتبعتت قبل كده (عشان ميكررش) |
| `.gitignore` | بيتجاهل `__pycache__`، `cv_out/`، `out_test/` |
| `Khaled_Hussien_CV_Master.docx` | الـ CV الأصلي اللي اتطلّع منه `cv_master.json` |

---

## 🧠 الفلاتر (٦ فلاتر — موجودة في `job_hunter.py`)

1. **Whitelist (العنوان لازم يحتوي واحدة):** marketing manager, digital marketing
   manager, performance marketing manager, marketing director, head of marketing,
   head of digital, senior marketing manager, senior marketing director,
   senior digital marketing.

2. **Blacklist (يترفض لو العنوان فيه أي منها):** content creator, content writer,
   customer service, supervisor, specialist, coordinator, assistant, intern,
   internship, junior, graduate, trainee, entry.

3. **المرتب:** أي مرتب بأي عملة بيتحوّل لجنيه مصري/شهر (السنوي ÷ ١٢)، ولو أقل من
   **٥٠٬٠٠٠ جنيه/شهر** يترفض. لو مفيش مرتب → يعدّي. أسعار الصرف في `FX_TO_EGP`
   (الدولار = ٥٠ جنيه افتراضيًا).

4. **الجنسية الخليجية:** يترفض لو فيه Saudization / Emiratization / nationals only
   / citizens only … إلخ.

5. **اللغة الأجنبية:** يترفض لو بيطلب إتقان لغة غير الإنجليزي/العربي — إلا لو
   مذكورة كـ "a plus" / "nice to have".

6. **المكان:** يقبل **الخليج** (السعودية/الإمارات/قطر/الكويت/عُمان/البحرين) +
   **مصر** + **MENA/GCC/Gulf**، **وكمان الريموت المفتوح عالميًا** (Remote /
   Worldwide / Anywhere / Global من غير تقييد دولة). بيرفض أي on-site برّه
   الخليج/مصر، وأي ريموت مقيّد بدولة/منطقة برّه (زي Remote-US / Remote-Europe /
   Remote-Nigeria / EMEA). المكان غير الواضح/الفاضي بيتعامل كريموت مفتوح ويعدّي.

---

## 🌐 المصادر (في `SOURCES` داخل `job_hunter.py`)

- **Google Custom Search** (المصدر الأساسي للخليج/مصر) — محتاج `GOOGLE_API_KEY` +
  `GOOGLE_CSE_ID`. بيستخدم بس (العنوان + اللينك + المقتطف) من الـ API.
  حد الخطة المجانية ١٠٠ بحث/يوم → البوت بيعمل ٦ بحثات/تشغيلة، كل ٣ ساعات.
- **شغّالة بدون مفاتيح:** Remotive، RemoteOK، Jobicy، Arbeitnow، Himalayas،
  We Work Remotely (RSS)، The Muse، Findwork.
- **Jooble** (اختياري) — محتاج `JOOBLE_API_KEY`، بيطلب كل دولة خليج/مصر لوحدها.
- **Adzuna اتشال** (مبيغطّيش الخليج/مصر).

---

## 📄 ميزة الـ CV + Cover Letter المخصّصين (جديدة — مجانية ١٠٠٪ بدون أي API/توكن)

مع كل وظيفة جديدة، البوت بيبني CV مخصّص **+ خطاب تقديم (Cover Letter)** ويبعتهم
ملفين PDF مرفقين تحت الوظيفة:

1. **بيختار المسمّى الأنسب** (heuristic بالكلمات المفتاحية) من:
   Marketing Manager / Digital Marketing Manager / Performance Marketing Manager /
   Growth Marketing Manager.
2. **بيحط ملخّص مخصّص للمسمّى** — ٤ نسخ جاهزة في `ROLE_SUMMARIES` داخل `cv_tailor.py`.
3. **بيرتّب الـ Core Competencies** حسب علاقتها بكلمات الوظيفة (`_reorder_competencies`).
4. **بيطلّع PDF متوافق مع ATS** (عمود واحد، نص قابل للقراءة، بدون جداول/صور) عن
   طريق مكتبة `fpdf2`.

> 🔒 **مفيش اختراع بيانات:** الخبرات/الشركات/التواريخ/الأرقام/التعليم بتتاخد
> حرفيًا من `cv_master.json`. البوت بيغيّر بس المسمّى + الملخّص + ترتيب المهارات.

**تفاصيل تقنية مهمة لأي حد هيكمّل:**
- الدالة الأساسية: `cv_tailor.tailor(job, master)` → بترجّع
  `{target_title, summary, competencies}`. الافتراضي هو `smart_local_tailor`
  (مجاني محلي).
- **الكوفر ليتر:** `cv_tailor.build_cover_letter_for_job(job, master, out_dir)` —
  قالب احترافي صفحة واحدة، الترحيب بيتظبط باسم الشركة، والفقرات من `COVER_ROLE_FIT`
  (٤ نسخ حسب المسمّى). كل الأرقام حقيقية من الماستر. مجاني بدون API.
- فيه دالة `_anthropic_tailor` **اختيارية ونائمة** بتشتغل بس لو حد حط
  `ANTHROPIC_API_KEY` (مدفوع) — **المستخدم رفض المدفوع، فهي مش مستخدمة**.
- الإرسال لتيليجرام: `send_telegram_document` (multipart → sendDocument)،
  و`send_job_with_cv` بتبعت الـ CV الأول وبعده الكوفر ليتر تحت كل وظيفة.
- التحكّم: `ATTACH_CV=0` يوقّف الـ CV، `ATTACH_COVER_LETTER=0` يوقّف الكوفر ليتر.
- الـ CVs/الخطابات المؤقتة بتتولّد في `cv_out/` (متجاهَل في git).

---

## 🔐 الأمان والاستضافة

- كل التوكنات بتتقري من **environment variables** (مش في الكود).
- التشغيل التلقائي على **GitHub Actions** كل ٣ ساعات + بيعمل commit لـ
  `seen_jobs.json` بعد كل تشغيلة.
- الـ workflow بيثبّت `fpdf2` تلقائيًا.

### الـ Secrets المطلوبة في GitHub (Settings ← Secrets and variables ← Actions)

| الاسم | إجباري؟ |
|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ |
| `TELEGRAM_CHAT_ID` | ✅ (القيمة: `5936947558`) |
| `GOOGLE_API_KEY` | للمصدر الأساسي |
| `GOOGLE_CSE_ID` | للمصدر الأساسي |
| `JOOBLE_API_KEY` | اختياري |

> ✅ ميزة الـ CV **مش محتاجة أي secret** — بتشتغل مجانًا لوحدها.

---

## ✅ اللي خلص

- البوت كامل بكل الـ ٦ فلاتر + كل المصادر (شغل الـ ٤ ساعات — اتعمله merge على
  main عبر PRs #2 لحد #6 حسب آخر حالة).
- ميزة الـ CV المخصّص اتبنت **واتجرّبت** (٤ أنواع وظايف، المسمّى بيتظبط صح،
  الملخّص بيتغيّر، المهارات بتترتّب، والـ PDF متوافق ATS ونصّه قابل للقراءة).
- اتسلّمت كملفات جاهزة في حزمة `job-hunter-update.zip`.

## ⏳ اللي لسه ناقص (خطوات يدوية من خالد)

1. **رفع ملفات ميزة الـ CV على الريبو** (`job_hunter.py` المعدّل + `cv_tailor.py`
   + `cv_master.json` + `README.md` + `job-hunter.yml` + `.gitignore`). لسه
   **مترفعتش** على الريبو لأن الشغل اتعمل في واجهة الشات.
2. **التأكد إن الـ Secrets متظبّطة** في GitHub (على الأقل `TELEGRAM_BOT_TOKEN` و
   `TELEGRAM_CHAT_ID`).
3. **تشغيل الـ workflow** يدوي مرة (Actions ← Job Hunter ← Run workflow) للتجربة.
4. **(أمان) عمل `/revoke` للتوكن القديم** في @BotFather — لأنه اتكتب في الكود
   قديمًا وفي الشات، فاعتبره مكشوف، وحط التوكن الجديد في الـ Secret.

---

## ⚠️ ملاحظات للجلسة الجاية (مهمة عشان منضيّعش وقت)

- **Claude في واجهة الشات مش بيقدر يعمل push أو يفتح PR** على GitHub — بيسلّم
  الكود كملفات. **Claude Code بيقدر** يعمل commit + PR. فلو عايز push/PR تلقائي،
  كمّل مع Claude Code.
- المسمّيات المسموحة للـ CV (٤): لو عايز تزوّد مسمّى جديد (مثلاً Brand Manager)،
  لازم تتضاف في `allowed_titles` بـ `cv_master.json` + قاعدة في `_TITLE_RULES`
  + ملخّص في `ROLE_SUMMARIES` (كلهم في `cv_tailor.py` ما عدا allowed_titles).
- لتعديل بياناتك في الـ CV: عدّل `cv_master.json` بس، وكل الوظايف الجاية
  هتتفصّل من المحتوى الجديد.
- أسعار الصرف وحد المرتب: `FX_TO_EGP` و `MIN_EGP_PER_MONTH` في أول `job_hunter.py`.

---

## 💡 أفكار ممكنة للتطوير (لو حبينا)

- إضافة مسمّيات/قوالب CV إضافية.
- لو حبّينا تفصيل أذكى ببلاش: نقدر نضيف مزوّد LLM ليه طبقة مجانية (زي Gemini/Groq)
  بدل المدفوع — بس الحالي (المحلي) كويس وكافٍ.
- صفحة لوج/إحصائيات لعدد الوظايف اللي اتبعتت يوميًا.
