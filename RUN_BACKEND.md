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
