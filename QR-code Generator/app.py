# Importera nödvändiga bibliotek
from flask import Flask, render_template, request, jsonify, send_file
import os
import uuid  # Importera uuid
import pyqrcode
import zipfile
from io import BytesIO
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

    qr_count = 0
    sku_list = []
    timestamps = []
    links = []  # Lägg till en tom lista för att lagra länkar med UUID
    uuid_list = []  # Lägg till en tom lista för att lagra UUIDs

    global_qr_counter = 0  # Global räknare för alla QR-koder

    for doc in documents:
        produkt_data = doc.get('Produkt-data', [])
        if not produkt_data:
            continue

        current_sku = produkt_data[0]

        if sku and current_sku != sku:
            continue

        link = produkt_data[5] if len(produkt_data) > 5 else None  # Antag att länken finns på index 5 i produkt_data-listan

        if not link:
            continue

        if not quantity:
            quantity = 1

        quantity = int(quantity)

        for _ in range(quantity):
            qr_count += 1
            global_qr_counter += 1
            new_guid = str(uuid.uuid4())
            uuid_list.append(new_guid)

            qr_code = pyqrcode.create(link + '&UID=' + new_guid)
            file_name = os.path.join(qr_folder, f"{str(global_qr_counter).zfill(2)}_qr_{current_sku}.png")
            qr_code.png(file_name, scale=5)

            sku_list.append(current_sku)
            timestamps.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            links.append(link + '&UID=' + new_guid)  # Lägg till länken med UUID i listan

    return qr_count, sku_list, timestamps, links, uuid_list  # Returnera också UUIDs

# Ny ruttfunktion för att ladda ner QR-koderna som en zip-fil
from flask import make_response

@app.route('/download_qr_codes')
def download_qr_codes():
    folder_date = request.args.get('folder_date')  # Hämta mappen med QR-koder baserat på datumet
    qr_folder = os.path.join(static_folder, folder_date)

    # Skapa en temporär minnesbuffert för att skapa zip-filen
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
        # Lägg till varje QR-kod i zip-filen
        for root, _, files in os.walk(qr_folder):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.relpath(file_path, qr_folder))

    # Återställ bufferns pekare till början
    zip_buffer.seek(0)

    # Skapa namnet på zip-filen baserat på datumet och tiden för QR-kodernas generering
    zip_file_name = f"qr_codes_{folder_date}.zip"

    # Skapa en Flask-respons och lägg till zip-filen som en bifogad fil
    response = make_response(zip_buffer.getvalue())
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = f'attachment; filename={zip_file_name}'
    
    return response

# Hemrutt för att rendera indexsidan
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/form')
def form():
    return render_template('form.html')

@app.route('/button')
def button():
    return render_template('button.html')

@app.route('/chart')
def chart():
    return render_template('chart.html')

@app.route('/element')
def element():
    return render_template('element.html')

@app.route('/signin')
def signin():
    return render_template('signin.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/table')
def table():
    return render_template('table.html')

@app.route('/typography')
def typography():
    return render_template('typography.html')

@app.route('/widget')
def widget():
    return render_template('widget.html')

@app.route('/blank')
def blank():
    return render_template('blank.html')

@app.route('/fyranollfyra')
def fyranollfyra():
    return render_template('404.html')

# Rutten för att generera QR-koder baserat på formulärdata
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    generator_option = request.form.get('generatorOption')

    qr_count = 0
    sku_list = []
    timestamps = []
    links = []  # Lägg till en tom lista för att lagra länkar med UUID
    uuid = None  # Definiera uuid variabeln

    folder_date = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    if generator_option == 'all':
        qr_count, sku_list, timestamps, links, uuid = generate_qr_codes(None, None, folder_date)
    elif generator_option == 'quantity':
        quantity_input_all = request.form.get('quantityInput')
        qr_count, sku_list, timestamps, links, uuid = generate_qr_codes(quantity_input_all, None, folder_date)
    elif generator_option == 'specific':
        sku = request.form.get('skuInput')
        quantity_input_specific = request.form.get('quantityInputSpecific')
        qr_count, sku_list, timestamps, links, uuid = generate_qr_codes(quantity_input_specific, sku, folder_date)

    return render_template('result.html', qr_count=qr_count, sku_list=sku_list, timestamps=timestamps, links=links, folder_date=folder_date, uuid=uuid)  # Skicka med uuid till mallen

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

# Starta Flask-appen
if __name__ == '__main__':
    app.run(debug=True)
