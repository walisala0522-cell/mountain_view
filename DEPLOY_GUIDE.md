# 🚀 Deploy ไปที่ Render - Mountain View Bungalow

## ขั้นตอน Deploy

### 1. Push โปรเจกต์ไปที่ GitHub
```bash
git add .
git commit -m "Deploy configuration"
git push origin main
```

---

## 2. ตั้งค่า Google OAuth

### ขั้นตอน A: สร้าง Credentials ใน Google Cloud Console

1. ไปที่ https://console.cloud.google.com
2. สร้าง Project หรือเลือก Project ที่มีอยู่
3. ไปที่ **APIs & Services** → **Credentials**
4. คลิก **Create Credentials** → **OAuth Client ID**
5. เลือก **Web application**
6. ใน **Authorized redirect URIs** เพิ่ม:
   ```
   https://mountain-view-1.onrender.com/callback
   ```
   (แทน `mountain-view-1` ด้วยชื่อจริงของแอปใน Render)

7. ดาวน์โหลด JSON credentials
8. คัดลอกเนื้อหาทั้งหมดของไฟล์ JSON นั้น

### ขั้นตอน B: ตั้งค่า Environment Variable บน Render

1. ไปที่ Dashboard ของแอปใน Render
2. คลิก **Environment**
3. เพิ่ม Environment Variable:

| Key | Value |
|-----|-------|
| `GOOGLE_CLIENT_SECRET_JSON` | (วาง JSON content ที่คัดลอกจาก Google Cloud) |
| `FLASK_ENV` | `production` |
| `DATABASE_URL` | (MySQL connection string) |
| `RENDER_EXTERNAL_HOSTNAME` | (ชื่อ domain ของ Render - เช่น mountain-view-1.onrender.com) |

:warning: **สำคัญ:** Environment Variable จะเก็บ credentials อย่างปลอดภัย

---

## 3. ตั้งค่า MySQL Database

ตั้งค่า environment variable สำหรับ database:

```
DB_HOST=your-database-host
DB_USER=your-username
DB_PASSWORD=your-password
DB_NAME=mountain_view
```

(หรือใช้ `DATABASE_URL` เต็มตามรูปแบบ MySQL connection string)

---

## 4. Deploy บน Render

### วิธี A: Automatic Deploy (แนะนำ)
- Render จะ deploy อัตโนมัติเมื่อ push ไปที่ GitHub

### วิธี B: Manual Deploy
- ไปที่ Dashboard → คลิก **Deploy** 

---

## 5. ทดสอบ Google Login

1. ไปที่ https://mountain-view-1.onrender.com/login
2. คลิก **Login with Google**
3. ถ้าสำเร็จ ก็จะ login เข้าระบบได้

---

## 🔧 Troubleshooting

### ❌ "Google Auth not configured"
- ตรวจสอบว่ามี environment variable `GOOGLE_CLIENT_SECRET_JSON` หรือ `client_secret.json` ไม่ว่าแบบไหน
- ดู Render logs: **Logs** tab ในแดชบอร์ด

### ❌ "Redirect URI mismatch"
- ใน Google Cloud Console → ตัวอักษรแรก redirect URI ต้องเป็น https:// บน production
- ตรวจสอบชื่อ domain ใน `RENDER_EXTERNAL_HOSTNAME`

### ❌ Database Connection Error
- ตรวจสอบข้อมูล `DB_HOST`, `DB_USER`, `DB_PASSWORD`
- ทำให้ MySQL server สามารถแชร์ได้จากภายนอก (whitelist Render IP)

### ❌ Port Error
- Render ใช้ port 5000 โดยอัตโนมัติ
- ดูใน Render logs เพื่อหาปัญหา

---

## 📝 Local Development

สำหรับการพัฒนาในเครื่องของคุณ:

```bash
# ใส่ client_secret.json ในไฟล์รูทของโปรเจกต์
# app.py จะอ่านจากไฟล์นี้โดยอัตโนมัติ

python app.py
```

---

## 📦 Files ที่ใช้สำหรับ Deploy

- **Procfile** - บอก Render วิธีรันแอป
- **render.yaml** - ตั้งค่า Render (เพิ่มเติม)
- **requirements.txt** - Dependencies
- **runtime.txt** - Python version

---

## 💡 Tips

- ใช้ `.gitignore` เพื่อไม่ upload `client_secret.json` ไปยัง GitHub
- Environment variables อยู่เฉพาะใน Render ไม่ผ่าน Git
- ตรวจสอบ logs ใน Render Dashboard สำหรับ debugging

---

**สร้างเมื่อ:** March 2026  
**สำหรับ:** Mountain View Bungalow
