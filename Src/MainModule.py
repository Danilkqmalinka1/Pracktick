from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List
import sqlite3
from PIL import Image
import io
import os

app = FastAPI()

DATABASE = "images.db"  # Имя файла базы данных

# Модель данных для изображения
class ImageModel(BaseModel):
    name: str
    size: int
    width: int
    height: int
    type: str
    date_added: str
    file_path: str

# Функция для подключения к базе данных
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Возвращать результаты в виде словарей
    return conn

# Функция для создания таблицы, если ее нет
def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            size INTEGER NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            type TEXT NOT NULL,
            date_added TEXT NOT NULL,
            file_path TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

create_table()  # Создаем таблицу при запуске

# API для добавления изображения
@app.post("/api/image/add", response_model=ImageModel)
async def add_image(file: UploadFile = File(...)):
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))

        # Получаем метаданные изображения
        name = file.filename
        size = len(image_data)
        width, height = image.size
        type = file.content_type
        date_added = str(datetime.datetime.now())

        # Генерируем уникальный путь для сохранения файла
        file_path = f"images/{name}" #Определяем путь к файлу
        os.makedirs("images", exist_ok=True)  # Создаем директорию images, если ее нет
        with open(file_path, "wb") as f: #Открываем файл на запись
            f.write(image_data) #Записываем image_data в file_path

        #Сохраняем в БД
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO images (name, size, width, height, type, date_added, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, size, width, height, type, date_added, file_path))
        image_id = cursor.lastrowid
        conn.commit()
        conn.close()

        #Возвращаем данные
        return ImageModel(
            name=name, size=size, width=width, height=height,
            type=type, date_added=date_added, file_path=file_path
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API для изменения размера изображения
@app.put("/api/image/change/size")
async def resize_image(file_path: str, width: int, height: int):
        try:
            image = Image.open(file_path)
            resized_image = image.resize((width, height)) # Изменяем размер изображения
            resized_image.save(file_path) #Сохраняем изображение

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE images SET width = ?, height = ? WHERE file_path = ?
            """, (width, height, file_path)) # Обновляем высоту и ширину в БД
            conn.commit()
            conn.close()

            return {"message": "Image resized successfully"}

        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Image not found")
        except Exception as e:
             raise HTTPException(status_code=500, detail=str(e))



# API для поворота изображения
@app.put("/api/image/change/rotate")
async def rotate_image(file_path: str, angle: int):
    try:
        image = Image.open(file_path) #Открываем файл
        rotated_image = image.rotate(angle) #Поворачиваем на угол angle
        rotated_image.save(file_path) #Сохраняем

        return {"message": "Image rotated successfully"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# API для получения всех изображений
@app.get("/api/image", response_model=List[ImageModel])
async def get_all_images():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM images")
    rows = cursor.fetchall()
    conn.close()

    images = []
    for row in rows:
        images.append(ImageModel(
            name=row["name"], size=row["size"], width=row["width"], height=row["height"],
            type=row["type"], date_added=row["date_added"], file_path=row["file_path"]
        ))
    return images