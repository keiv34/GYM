import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_key")
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:@localhost:3306/gymdb"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuración de Flask-Mail
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('EMAIL_USER', 'kevinwtf71@gmail.com') 
    MAIL_PASSWORD = os.getenv('EMAIL_PASS', 'lvqkhrooavlvlxwo')
    UPLOAD_FOLDER = 'static/uploads/productos'
