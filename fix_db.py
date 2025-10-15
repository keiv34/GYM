# fix_db.py

import os
from GYM_App import create_app
from GYM_App.extensions import db
from GYM_App.models import Producto

app = create_app()

with app.app_context():
    print("Iniciando la corrección de rutas de imágenes en la base de datos...")
    
    productos = Producto.query.all()
    corregidos = 0
    
    for producto in productos:
        if producto.imagen_url:
            # Extraer solo el nombre del archivo de la ruta actual
            # Esto maneja rutas con dobles carpetas, barras invertidas, y codificación
            filename = os.path.basename(producto.imagen_url.replace('\\', '/').replace('%5C', '/').replace('%255C', '/'))
            
            # Reconstruir la ruta correcta, que debe ser relativa a 'static'
            nueva_ruta = f"uploads/productos/{filename}"
            
            # Si la ruta es diferente, la actualizamos
            if producto.imagen_url != nueva_ruta:
                producto.imagen_url = nueva_ruta
                print(f"Ruta corregida para '{producto.nombre}': {nueva_ruta}")
                corregidos += 1
    
    if corregidos > 0:
        db.session.commit()
        print(f"¡Corrección completada! Se han actualizado {corregidos} rutas en la base de datos.")
    else:
        print("No se encontraron productos con rutas que necesiten corrección.")