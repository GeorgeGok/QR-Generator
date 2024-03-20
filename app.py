# Importera nödvändiga bibliotek
from flask import Flask, render_template, request, jsonify, send_file
import os
import uuid
import pyqrcode
import zipfile
from datetime import datetime
from pymongo import MongoClient

# Ange projektmappen och den statiska mappen för Flask-appen
project_folder = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(project_folder, 'static')

# Skapa en Flask-app
app = Flask(__name__, static_folder=static_folder)

# Ange anslutningssträngen för MongoDB och skapa en klient och en databasanslutning
connection_string = 'mongodb+srv://george02:xxgeorgexx02@cluster0.0erqfzf.mongodb.net/'
client = MongoClient(connection_string)
db = client['QR-inventory']
collection = db['Product-catalog']

# Funktion för att hämta data från MongoDB
def fetch_data_from_mongodb():
    try:
        all_documents = collection.find()
        return list(all_documents)
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return []

# Funktion för att generera QR-koder baserat på kvantitet och SKU
def generate_qr_codes(quantity, sku, folder_date):
    qr_folder = os.path.join(static_folder, folder_date)

    if not os.path.exists(qr_folder):
        os.makedirs(qr_folder)

    documents = fetch_data_from_mongodb()

    qr_count = 1
    sku_list = []
    timestamps = []
    links = []
    uuid_list = []

    for doc in documents:
        produkt_data = doc.get('Produkt-data', [])
        if not produkt_data:
            continue

        current_sku = produkt_data[0]

        if sku and current_sku != sku:
            continue

        link = produkt_data[5] if len(produkt_data) > 5 else None  

        if not link:
            continue

        for _ in range(int(quantity) if quantity else 1):
            new_guid = str(uuid.uuid4())
            uuid_list.append(new_guid)

            qr_code = pyqrcode.create(link + '&UID=' + new_guid)
            file_name = os.path.join(qr_folder, f"{str(qr_count).zfill(2)}_qr_{current_sku}.png")
            qr_code.png(file_name, scale=5)
            qr_count += 1
            sku_list.append(current_sku)
            timestamps.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            links.append(link + '&UID=' + new_guid)  

    return qr_count, sku_list, timestamps, links, uuid_list  

# Hemrutt för att rendera indexsidan
@app.route('/')
def index():
    return render_template('index.html')

# Rutten för att generera QR-koder baserat på formulärdata
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    generator_option = request.form.get('generatorOption')
    quantity_input_all = request.form.get('quantityInput')
    quantity_input_specific = request.form.get('quantityInputSpecific')
    sku = request.form.get('skuInput')

    qr_count = 1
    sku_list = []
    timestamps = []
    links = []  
    uuid = None  

    folder_date = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    if generator_option == 'all':
        if quantity_input_all:
            qr_count, sku_list, timestamps, links, uuid = generate_qr_codes(quantity_input_all, None, folder_date)
    elif generator_option == 'quantity':
        if quantity_input_all:
            qr_count, sku_list, timestamps, links, uuid = generate_qr_codes(quantity_input_all, None, folder_date)
    elif generator_option == 'specific':
        if sku:
            if quantity_input_specific:
                qr_count, sku_list, timestamps, links, uuid = generate_qr_codes(quantity_input_specific, sku, folder_date)

    return render_template('result.html', qr_count=qr_count, sku_list=sku_list, timestamps=timestamps, links=links, folder_date=folder_date, uuid=uuid)

# Funktion för att hämta SKUs från databasen
def fetch_skus_from_database():
    try:
        all_documents = collection.find()
        skus = set()
        for doc in all_documents:
            produkt_data = doc.get('Produkt-data', [])
            if produkt_data:
                skus.add(produkt_data[0])
        return list(skus)
    except Exception as e:
        print(f"Error fetching SKUs from MongoDB: {e}")
        return []

# Rutten för att hämta SKUs från databasen och returnera dem som JSON
@app.route('/get_skus')
def get_skus():
    skus = fetch_skus_from_database()
    return jsonify({'skus': skus})

# Funktion för att skapa en ZIP-fil för QR-koder
def create_zip(folder_date):
    zip_file_path = os.path.join(static_folder, folder_date + '.zip')
    qr_folder = os.path.join(static_folder, folder_date)

    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for root, _, files in os.walk(qr_folder):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), qr_folder))

    return zip_file_path

# Rutten för att ladda ner ZIP-filen
@app.route('/download_qr_codes/<folder_date>')
def download_qr_codes(folder_date):
    zip_file_path = create_zip(folder_date)
    return send_file(zip_file_path, as_attachment=True)

# Starta Flask-appen
if __name__ == '__main__':
    app.run(debug=True)