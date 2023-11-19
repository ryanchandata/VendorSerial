from flask import Flask, render_template, request, redirect, url_for, make_response
import csv
import os
import datetime
import barcode
from barcode.writer import ImageWriter
from barcode import get_barcode_class
from io import BytesIO
import base64
from flask import jsonify

app = Flask(__name__)

def generate_barcode(serial_no):
    print(f"Generating barcode for serial number: {serial_no}")  # Log the serial number
    try:
        CODE128 = barcode.get_barcode_class('code128')
        barcode_instance = CODE128(serial_no, writer=ImageWriter())

        # Adjusting options
        options = {
            'write_text': False,  # Ensure the text is not written
            'text_distance': 3,   # Distance between barcode and text
            'quiet_zone': 1,      # Margins around the barcode
        }

        buffered = BytesIO()
        barcode_instance.write(buffered, options=options)
        barcode_data = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{barcode_data}"

    except Exception as e:
        print(f"Error generating barcode for {serial_no}: {e}")  # Log any errors
        return None



def read_today_records():
    with open('db.csv', mode='r') as file:
        reader = csv.DictReader(file)
        date_today = datetime.datetime.now().strftime('%Y-%m-%d')
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        return [row for row in reader if row['date'] == today_str]

@app.route('/all_records')
def all_records():
    records = read_all_records()  # Function to read all records from the database
    return render_template('all_records.html', records=records)

def read_all_records():
    # Implement the logic to read all records from your database
    # For example, reading from a CSV file
    with open('db.csv', mode='r') as file:
        reader = csv.DictReader(file)
        return list(reader)


# Function to read data from vendor.csv
def read_vendor_csv():
    with open('vendor.csv', mode='r') as file:
        reader = csv.DictReader(file)
        vendor_list = list(reader)
    return vendor_list

@app.route('/print_vendor_labels')
def print_vendor_labels():
    vendor_code = request.args.get('vendorCode')
    date_today = datetime.datetime.now().strftime('%Y-%m-%d')
    records = read_records_for_vendor(vendor_code, date_today)

    # Add this loop to assign barcode images to each record
    for record in records:
        record['barcode_image'] = generate_barcode(record['serialNo'])

    return render_template('print_labels.html', records=records)


# Function to get the largest SN from db.csv
def get_largest_sn():
    try:
        with open('db.csv', mode='r') as file:
            reader = csv.DictReader(file)
            sn_list = [int(row['SN']) for row in reader if 'SN' in row and row['SN'].isdigit()]
            return max(sn_list, default=0)
    except FileNotFoundError:
        return 0  # Return 0 if file not found, meaning no records yet

# Function to write to db.csv
def write_to_db(data):
    with open('db.csv', mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        writer.writerow(data)

# Function to read records for today from db.csv
def read_today_records():
    with open('db.csv', mode='r') as file:
        reader = csv.DictReader(file)
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        return [row for row in reader if row['date'] == today_str]

def read_records_for_vendor(vendor_code, date):
    with open('db.csv', 'r') as file:
        reader = csv.DictReader(file)
        return [row for row in reader if row['vendorCode'] == vendor_code and row['date'] == date]

def handle_serial_number(serial_number):
    records = []
    updated = False

    with open('db.csv', mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['serialNo'] == serial_number:
                row['status'] = 'Y'  # Update status to 'Y'
                updated = True
            records.append(row)

    if updated:
        with open('db.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)

    return redirect(url_for('index'))

# Function to get the next unique ID
def get_next_unique_id():
    try:
        with open('serial_counter.txt', 'r') as file:
            current_id = int(file.read().strip())
    except FileNotFoundError:
        current_id = 0
    
    with open('serial_counter.txt', 'w') as file:
        file.write(str(current_id + 1))
    return current_id + 1

# Luhn Algorithm for checksum digit
def calculate_luhn(number):
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d*2))
    return checksum % 10

# Function to generate the serial number
def generate_serial(operation_type, unique_id):
    prefix = "04"
    year = datetime.datetime.now().year
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    serial = f"{prefix}{operation_type}{year:04}{day_of_year:03}{unique_id:08}"
    checksum = calculate_luhn(serial)
    return f"{serial}{checksum}"

@app.route('/get_today_records')
def get_today_records():
    records = read_today_records()
    return jsonify(records)

@app.route('/get_non_finished_skids')
def get_non_finished_skids():
    records = read_today_records()
    non_finished_records = [record for record in records if record.get('status') != 'Y']
    return jsonify(non_finished_records)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        vendor_code = request.form['vendorCode']
        vendors = read_vendor_csv()
        vendor = next((item for item in vendors if item["vendorCode"] == vendor_code), None)
        if vendor:
            return redirect(url_for('additional_input', vendor_code=vendor_code))

    records = read_today_records()
    unique_companies = {record['vendorName'] for record in records}
    total_skids_today = len(records)
    # Calculate total non-finished skids
    total_non_finished_skids = sum(1 for record in records if record.get('status') != 'Y')
    return render_template('index.html', records=records, unique_companies_count=len(unique_companies), 
                           total_skids_today=total_skids_today, total_non_finished_skids=total_non_finished_skids)

@app.route('/print_labels')
def print_labels():
    records = read_today_records()
    for record in records:
        record['barcode_image'] = generate_barcode(record['serialNo'])
    return render_template('print_labels.html', records=records)

@app.route('/scan_input', methods=['POST'])
def scan_input():
    scanned_code = request.form.get('scannedCode')

    if scanned_code.startswith('04') and len(scanned_code) == 20:
        return handle_serial_number(scanned_code)
    else:
        return redirect(url_for('additional_input', vendor_code=scanned_code))


@app.route('/input/<vendor_code>', methods=['GET', 'POST'])
def additional_input(vendor_code):
    vendors = read_vendor_csv()
    vendor = next((item for item in vendors if item["vendorCode"] == vendor_code), None)
    if not vendor:
        return redirect(url_for('index'))

    if request.method == 'POST':
        total_skids = int(request.form['totalSkids'])
        invoice_no = request.form['invoiceNo']
        largest_sn = get_largest_sn()

        for current_skid in range(1, total_skids + 1):
            sn = largest_sn + current_skid
            unique_id = get_next_unique_id()
            serial_no = generate_serial("01", unique_id)
            record = {
                'SN': sn,
                'vendorCode': vendor_code,
                'vendorName': vendor['vendorName'],
                'date': datetime.datetime.now().strftime("%Y-%m-%d"),
                'total_skids': total_skids,
                'current_skid': current_skid,
                'invoiceNo': invoice_no,
                'serialNo': serial_no,
                'status' : 'N'
            }
            write_to_db(record)

        return redirect(url_for('index'))
    print(vendor)  # Add this line to debug
    return render_template('additional_input.html', vendor=vendor)

if __name__ == "__main__":
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        port = int(os.environ.get('PORT', 80))  # Use PORT environment variable in production, default to 80
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        app.run(host='0.0.0.0', port=5888, debug=True)  # Use 5000 for local development with debug mode enabled