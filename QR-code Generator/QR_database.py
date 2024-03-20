import uuid
from tkinter import *
from PIL import ImageTk, Image
import pyqrcode
from pymongo import MongoClient

root = Tk()
canvas = Canvas(root, width=800, height=800)
canvas.pack()

# Definiera MongoClient och collection globalt
connection_string = 'mongodb+srv://george02:xxgeorgexx02@cluster0.0erqfzf.mongodb.net/'
client = MongoClient(connection_string)
db = client['QR-inventory']
collection = db['Product-catalog']

def fetch_data_from_mongodb():
    try:
        all_documents = collection.find()
        return list(all_documents)
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return []

def generate_and_display_qr_codes():
    x_position = 100
    y_position = 200
    row_limit = 3
    qr_count = 0

    documents = fetch_data_from_mongodb()

    for doc in documents:
        produkt_data = doc.get('Produkt-data', [])
        if not produkt_data:
            continue

        sku = produkt_data[0]
        link = produkt_data[5] if len(produkt_data) > 5 else None
        additional_info = produkt_data[1:5]

        if not sku or not link:
            continue

        # Generera ett nytt GUID
        new_guid = str(uuid.uuid4())

        # Lägg till "&UID=" precis innan GUID
        if len(produkt_data) > 5 and len(new_guid) == 36:
            produkt_data[5] = link.split('&UID=')[0] + '&UID=' + new_guid


        # Uppdatera dokumentet i databasen med det nya värdet i index 5
        update_result = collection.update_one({'_id': doc['_id']}, {'$set': {'Produkt-data': produkt_data}})
        
        if update_result.modified_count == 1:
            print(f"GUID {new_guid} har ersatt de sista 32 tecknen i index 5 i databasen för SKU: {sku}")

        qr_code = pyqrcode.create(link)
        file_name = f"qr_{sku}.png"
        qr_code.png(file_name, scale=5)

        group_names = ["Marabou liten", "Marabou mellan", "Marabou stor"]
        for i, group_name in enumerate(group_names):
            group_label = Label(root, text=group_names[qr_count % len(group_names)])
            group_label.place(x=x_position + 415, y=y_position + 150)

        custom_texts = ["Vikt: ", "Kostnad: ", "Material: ", "Storlek: "]
        info_text = "\n".join([f"{custom_texts[i]}: {info}" for i, info in enumerate(additional_info)])
        info_label = Label(root, text=f"SKU: {sku}\n{info_text}")
        info_label.place(x=x_position + 410, y=y_position + 170)

        with Image.open(file_name) as img:
            image = ImageTk.PhotoImage(img)
            image_label = Label(image=image)
            image_label.image = image
            canvas.create_window(x_position, y_position, window=image_label)

        qr_count += 1
        if qr_count % row_limit == 0:
            x_position = 50
            y_position += 200
        else:
            x_position += 350

root.after(100, generate_and_display_qr_codes)
root.mainloop()