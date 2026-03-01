# تشغيل Backend Server

## الخطوات المطلوبة:

### 1. تفعيل البيئة الافتراضية (Virtual Environment)
```powershell
cd D:\Shop
.\venv\Scripts\Activate.ps1
```

### 2. الانتقال إلى مجلد backend
```powershell
cd backend
```

### 3. تشغيل السيرفر
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## أو يمكنك تشغيل كل الأوامر دفعة واحدة:
```powershell
cd D:\Shop
.\venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## التحقق من تشغيل السيرفر:
بعد التشغيل، افتح المتصفح على:
- http://localhost:8000/health
- http://localhost:8000/api/v1/docs (Swagger Documentation)

## ملاحظات:
- تأكد من تشغيل PostgreSQL على المنفذ 5432
- تأكد من وجود قاعدة البيانات `shop_db`
- المنفذ 8000 يجب أن يكون متاحاً

---

# النشر على Railway (Docker)

## الملفات المستخدمة للنشر
- `Dockerfile`
- `start.sh`
- `.dockerignore`
- `railway.toml`

## فكرة التشغيل
عند كل Deploy:
1. السكربت `start.sh` يتأكد أن `DATABASE_URL` موجود.
2. ينفذ `alembic upgrade head`.
3. يشغل التطبيق على `PORT` القادم من Railway (أو 8000 كقيمة افتراضية).

## خطوات النشر على Railway
1. افتح Railway وأنشئ مشروع/Service جديدة من نفس الـ repo.
2. اختر النشر عبر Dockerfile (سيقرأ `railway.toml` تلقائيًا).
3. أضف متغيرات البيئة المطلوبة.
4. نفّذ Deploy.
5. راقب الـ logs وتأكد من:
   - نجاح migration.
   - بدء `uvicorn` بدون أخطاء.
6. اختبر `GET /health`.

## متغيرات البيئة المطلوبة على Railway

### إلزامي
- `DATABASE_URL`: رابط PostgreSQL خارجي.
- `SECRET_KEY`: مفتاح قوي للإنتاج.
- `ALLOWED_ORIGINS`: دومين الواجهة (أو عدة دومينات مفصولة بفواصل).

### حسب الاستخدام
- البريد:
  - `EMAIL_HOST`
  - `EMAIL_PORT`
  - `EMAIL_USER`
  - `EMAIL_PASSWORD`
  - `EMAIL_FROM`
- الدفع:
  - `STRIPE_API_KEY`
  - `STRIPE_WEBHOOK_SECRET`
  - `PAYPAL_CLIENT_ID`
  - `PAYPAL_CLIENT_SECRET`
  - `PAYPAL_WEBHOOK_ID`

## مثال `ALLOWED_ORIGINS`
```env
ALLOWED_ORIGINS=https://your-frontend-domain.com,https://staging-frontend-domain.com
```

## ملاحظة مهمة عن uploads
المجلد `uploads/` داخل السيرفر المحلي (ephemeral filesystem) على Railway، لذلك الملفات قد تضيع بعد restart/redeploy.
للاستخدام الإنتاجي الكامل يفضّل لاحقًا نقل التخزين إلى Object Storage مثل S3 أو Cloudinary.
