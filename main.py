from flask import Flask
from flask import *
from flaskext.mysql import MySQL
import os
import vonage

app = Flask(__name__)

# Vonage Client Setup
client = vonage.Client(key="4278da57", secret="MFVKEoZOh8R8AMXt")
sms = vonage.Sms(client)

app.secret_key = "diarec"
mysql = MySQL()
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'diarec'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
app.config['UPLOAD_FOLDER'] = 'static/files'

mysql.init_app(app)

def get_db_cursor():
    conn = mysql.connect()
    cursor = conn.cursor()
    return (cursor, conn)

def send_sms_to_patient(contact_number, pat_id, password):
    # Format the message to send to the patient
    message = f"Hello! Your account has been created. Your Patient ID is {pat_id} and your password is {password}. Please keep it safe."

    # Send the message
    response = sms.send_message({
        "from": "Your Clinic Name",  # Sender name or your clinic name
        "to": contact_number,  # Recipient phone number (ensure it's in international format)
        "text": message,  # The message to send
    })

    # Check if the message was successfully sent
    if response["messages"][0]["status"] == "0":
        print("Message sent successfully.")
    else:
        print(f"Message failed with error: {response['messages'][0]['error-text']}")

# Route to add a patient
@app.route('/add_patient', methods=["POST", "GET"])
def add_patient():
    alert_message = None
    redirect_url = "/add_patient"

    if request.method == "POST":
        first_name = str(request.form["patientfName"])
        middle_name = str(request.form["patientmName"])
        last_name = str(request.form["patientlName"])
        gender = str(request.form["patientGender"])
        age = int(request.form["patientAge"])
        bday = str(request.form["patientBD"])
        address = str(request.form["patientAddress"])
        pcontact = request.form["patientContact"]
        email = request.form["patientEmail"]
        bloodtype = str(request.form["patientBloodType"])

        cursor, conn = get_db_cursor()

        # Check if the patient already exists
        cursor.execute("SELECT * FROM patient WHERE contact_num=%s AND email=%s", (pcontact, email))
        p_acc = cursor.fetchone()

        if p_acc:
            alert_message = "Patient already exists!"
            redirect_url = "/add_patient"
        else:
            # Insert the new patient data
            new_pat_id = 1000  # You might want to generate this dynamically
            new_pass = f"{last_name}123"  # Generate a simple password or securely generate it

            query = """
            INSERT INTO patient 
            (pat_id, pat_pass, first_name, last_name, middle_intl, gender, age, birthday, address, contact_num, email, blood_type) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (new_pat_id, new_pass, first_name, last_name, middle_name, gender, age, bday, address, pcontact, email, bloodtype)
            cursor.execute(query, values)
            conn.commit()

            # Send the SMS to the new patient with their `pat_id` and password
            send_sms_to_patient(pcontact, new_pat_id, new_pass)

            alert_message = "Patient successfully added!"
            redirect_url = "/admin_home"

        cursor.close()
        conn.close()

    return render_template('addpatient.html', alert_message=alert_message, redirect_url=redirect_url)

# Route to update patient password
@app.route('/update_patient_pass', methods=["POST", "GET"])
def update_patient_pass():
    if request.method == "POST":
        session['patid'] = session.get('patient_id')
        new_pass = str(request.form["newpass"])
        confirm_pass = str(request.form["confirm_pass"])

        cursor, conn = get_db_cursor()

        if len(new_pass) >= 8:
            if new_pass == confirm_pass:
                # Update the password in the database
                cursor.execute("UPDATE patient SET pat_pass=%s WHERE pat_id=%s", (new_pass, session['patid']))
                conn.commit()

                # Send the SMS to the patient notifying them of the password change
                send_sms_to_patient(session['patid'], new_pass, new_pass)

                flash('Password Updated Successfully! Please Log in again.')
                return redirect(url_for('land'))
            else:
                flash('Password does not match!', 'error')
                return render_template('update_pass.html', patient_id=session['patid'])
        else:
            flash('Password length must be 8 characters or longer', 'error')
            return render_template('update_pass.html', patient_id=session['patid'])

# Route to sign out
@app.route('/sign_out')
def sign_out():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('land'))

# Route for the landing page
@app.route('/')
def land():
    return render_template("land.html")

# Route for the about page
@app.route('/about', methods=["POST", "GET"])
def about():
    return render_template("about.html")

# Route for the contact page
@app.route('/contact', methods=["POST", "GET"])
def contact():
    return render_template("contact.html")

# Route to add a patient page (only accessible to admins)
@app.route('/addpatient', methods=["POST", "GET"])
def addpatient():
    if session.get('log_admin') == True:
        return render_template("addpatient.html")
    else:
        flash('Admin Not Authorized', 'error')
        return redirect(url_for('land'))

# Route for patient home page (only accessible to logged-in patients)
@app.route('/patient_home', methods=["POST", "GET"])
def patient_home():
    login_patient = session.get('login_patient')
    if login_patient == True:
        return render_template("records.html", first_name=session["account"][2])
    else:
        flash('Patient not authorized!', 'error')
        return redirect(url_for('land'))

# Route for admin home page (only accessible to logged-in admins)
@app.route('/admin_home')
def admin_home():
    if session.get('log_admin') == True:
        cursor, conn = get_db_cursor()
        
        cursor.execute("SELECT * FROM patient")
        patient_list = cursor.fetchall()
        
        return render_template("results.html", patients=patient_list)
    else:
        flash('Admin Not Authorized', 'error')
        return redirect(url_for('land'))

# Route to log in a patient
@app.route('/login_patient', methods=["POST", "GET"])
def login_patient():
    if request.method == "POST":
        session['patient_id'] = int(request.form["patient_id"])
        patient_password = str(request.form["patient_password"])
        
        cursor, conn = get_db_cursor()
        cursor.execute('SELECT * FROM patient WHERE pat_id=%s AND pat_pass=%s', (session['patient_id'], patient_password))
        patient_acc = cursor.fetchall()
        
        if patient_acc:
            for info in patient_acc:
                acc_info = list(info)
            
            if acc_info[1] == (acc_info[3] + "123"):
                return render_template('update_pass.html', patient_id=session['patient_id'])
            else:
                session["patient_password"] = patient_password
                session["account"] = acc_info
                session['log_patient'] = True
                return render_template("records.html", first_name=session["account"][2])
        else:
            session['log_patient'] = False
            flash('No Patient Found!', 'error')
            return redirect(url_for('land'))

# Route to log in an admin
@app.route('/login_admin', methods=["POST", "GET"])
def login_admin():
    if request.method == "POST":
        admin_id = int(request.form["admin_id"])
        admin_password = str(request.form["admin_pass"])

        cursor, conn = get_db_cursor()
        cursor.execute('SELECT * FROM admin WHERE admin_id=%s AND admin_pass=%s', (admin_id, admin_password))
        ad_account = cursor.fetchone()

        if ad_account:    
            session["admin_id"] = admin_id
            session["admin_password"] = admin_password
            session["admin_account"] = ad_account  
            session["log_admin"] = True  
            return redirect(url_for('admin_home'))
        else:
            flash('Admin Not Authorized', 'error')
            return redirect(url_for('land'))

    return render_template('land.html')

if __name__ == '__main__':
    app.run(debug=True)
