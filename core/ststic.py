# ========================== الإعدادات ==========================
# معرف المجلد في Google Drive (استخرجه من الرابط)
FOLDER_UPLOAD_ID = "1oTAlGsmPSqt_lmTnHAnLq0X8pzNKfI1l"   # غيّره حسب مجلدك
TXT_FOLDER_ID = "1d_ZR8PsfRcdZteZIh4yU7LZN0yBKJFsy"  # مجلد رفع ملفات .txt
TMP_DIR='/tmp/scd_update'
# قائمة بالمسارات النسبية المحتملة للملف الأصلي (نسبة إلى موقع هذا الملف)
POSSIBLE_PATHS = [
    "../colab/orginal.ipynb",
    "../../colab/orginal.ipynb",
    "colab/orginal.ipynb",
    "orginal.ipynb",
]

# نطاقات الصلاحية المطلوبة لـ Drive
SCOPES = ['https://www.googleapis.com/auth/drive']

# قائمة عمليات الخلفية التي يجب إيقافها عند الخروج
BACKGROUND_PROCS = []

DATABASE_PORT =3000
MONGO_URI = "mongodb+srv://scdgroup01_db_user:gd9QOtgXcpSlUEC4@cluster01.wlwx8z6.mongodb.net/?appName=Cluster01"
DB_NAME = 'test'
