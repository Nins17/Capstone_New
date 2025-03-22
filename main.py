from flask import Flask
from flask import *
from flaskext.mysql import MySQL
import os
import vonage  # Import Vonage library

app = Flask(__name__)

app.secret_key = "diarec"
mysql = MySQL()
app.config['MYSQL_DATABASE_USER'] = 'root'  # Database user
app.config['MYSQL_DATABASE_PASSWORD'] = ''  # Database password
app.config['MYSQL_DATABASE_DB'] = 'diarec'  # Name of database
app.config['MYSQL_DATABASE_HOST'] = 'localhost'  # Hosting site
app.config['UPLOAD_FOLDER'] = 'static/files'

mysql.init_app(app)

# Create a Vonage client instance for sending SMS
client = vonage.Client(key="a18a6465", secret="w5p8n9Lc4TNmulMP")
sms = vonage.Sms(client)

def get_db_cursor():
    conn = mysql.connect()
    cursor = conn.cursor()
    return (cursor ,conn)


################################# PAGES ###############################
@app.route('/')
def land():
    return render_template("land.html")

#about land page
@app.route('/about', methods=["POST", "GET"])
def about():
    return render_template("about.html") 

#contact land page
@app.route('/contact', methods=["POST", "GET"])
def contact():
    return render_template("contact.html")

#add patient form page
@app.route('/addpatient', methods=["POST", "GET"])
def addpatient():
    if session.get('log_admin') == True:
        cursor, conn = get_db_cursor()
        
        cursor.execute("SELECT * FROM patient")
        patient_list = cursor.fetchall()
        return render_template("addpatient.html", patients=patient_list)
    else:
        flash('Admin Not Authorized', 'error')
        return redirect(url_for('land'))

#patient homepage
@app.route('/patient_home', methods=["POST", "GET"])
def patient_home():
    if session.get('log_patient') == True:
        cursor, conn = get_db_cursor()
        cursor.execute('SELECT * FROM records WHERE patient_id=%s ', (session.get('patient_id'))) 
        patient_records = cursor.fetchall()
        return render_template("records.html", first_name=session["account"][2], patient_records=patient_records)
    else:
        flash('Patient not authorize!', 'error')
        return redirect(url_for('land'))

#admin/doctor homepage    
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

#lab result land page
@app.route('/lab_results', methods=["POST","GET"])
def lab_results():
    if session.get('log_admin') == True:
        cursor, conn = get_db_cursor()
        
        cursor.execute('SELECT * FROM records') 
        patient_records = cursor.fetchall()
        print(patient_records)
        
        cursor.execute("SELECT * FROM patient")
        patient_list = cursor.fetchall()
        return render_template("patientrecords.html",patient_records=patient_records, patients=patient_list)
    else:
        flash('Admin Not Authorized', 'error')
        return redirect(url_for('land'))
    
#add result form page   
@app.route('/add-result/<int:patient_id>')
def add_result(patient_id):
    cursor, conn = get_db_cursor()

    cursor.execute("SELECT * FROM patient WHERE pat_id=%s",(patient_id))
    patient_list = cursor.fetchall()
    return render_template("addrecord.html", selected_patient=patient_list)

@app.route('/open_record/<int:patient_id>')
def open_record(patient_id):
    cursor, conn = get_db_cursor()

    cursor.execute("SELECT * FROM records WHERE patient_id=%s",(patient_id))
    patient_list = cursor.fetchall()
    return render_template("recordsviewerspecific.html", patient_records=patient_list)

@app.route('/open_profile/<int:patient_id>')
def open_profile(patient_id):
    cursor, conn = get_db_cursor()
    
    cursor.execute("SELECT * FROM patient WHERE pat_id=%s", (patient_id,))
    patient = cursor.fetchone()
    
    if patient:
        cursor.execute("SELECT * FROM records WHERE patient_id=%s", (patient_id,))
        patient_records = cursor.fetchall()
        return render_template("view_profile.html", patient=patient, patient_records=patient_records)
    else:
        flash("Patient not found!", "error")
        return redirect(url_for('admin_home'))


############# END PAGES ####################




##############LOG INS########################
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
                
                cursor.execute('SELECT * FROM records WHERE patient_id=%s ', (session['patient_id'])) 
                patient_records = cursor.fetchall()
                print(patient_records)
                return render_template("records.html", first_name=session["account"][2], patient_records=patient_records)
        else:
            session['log_patient'] = False
            flash('No Patient Found!', 'error')
            return redirect(url_for('land'))

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
            cursor.close()
            conn.close()
            return redirect(url_for('admin_home'))
        else:
            flash('Admin Not Authorized', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('land'))

    return render_template('land.html')

############# END LOGINS ####################


##################### QUERIES ####################     
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
        pcontact = str("+63"+request.form["patientContact"])
        email = request.form["patientEmail"]
        bloodtype = str(request.form["patientBloodType"])

        cursor, conn = get_db_cursor()

        cursor.execute("SELECT * FROM patient WHERE contact_num=%s AND email=%s", (pcontact, email))
        p_acc = cursor.fetchone()
        print(p_acc)

        if p_acc:
            alert_message = "Patient already exists!"
            redirect_url = "/add_patient"
        else:
            if len(pcontact)==13 and pcontact.startswith("+63"):
                query = """
                INSERT INTO patient 
                (pat_id, pat_pass, first_name, last_name, middle_intl, gender, age, birthday, address, contact_num, email, blood_type) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (0000, f"{last_name}123", first_name, last_name, middle_name, gender, age, bday, address, f"63{pcontact}", email, bloodtype)
                cursor.execute(query, values)
                conn.commit()

                # Get the patient ID of the newly added patient (auto-incremented)
                patient_id = cursor.lastrowid

                # Send SMS to the newly added patient with their ID and password
                message = f"Hello {first_name}, your Patient ID is {patient_id} and your password is {last_name}123. Please use these details to log in to your account."
                responseData = sms.send_message({
                    "from": "Diarec",  # Sender name
                    "to": pcontact,  # Recipient's phone number
                    "text": message,  # Message content
                })

                if responseData["messages"][0]["status"] == "0":
                    print(f"Message sent successfully to {pcontact}")
                else:
                    print(f"Message failed to send: {responseData['messages'][0]['error-text']}")

                alert_message = "Patient successfully added and message sent!"
                redirect_url = "/admin_home"
            else:
                alert_message = "invalid contact! follow contact format"
                redirect_url = "/add_patient"
                

        cursor.close()
        conn.close()

    return render_template('addpatient.html', alert_message=alert_message, redirect_url=redirect_url)

@app.route('/update_patient_pass', methods=["POST", "GET"])
def update_patient_pass(): 
    if request.method == "POST":
        session['patid'] = session.get('patient_id')
        new_pass = str(request.form["newpass"])
        confirm_pass = str(request.form["confirm_pass"])
        cursor, conn = get_db_cursor()        
        if len(new_pass) >= 8:
            if new_pass == confirm_pass:
                cursor.execute("UPDATE `patient` SET `pat_pass`=%s WHERE `pat_id`=%s ", (new_pass, session['patid']))
                conn.commit()
                flash('Password Updated Successfully! Please Log in again.')
                return redirect(url_for('land'))
            else:
                flash('Password does not match!', 'error')
                return render_template('update_pass.html', patient_id=session['patid'])
        else:
            flash('Password length must be 8 or longer', 'error')
            return render_template('update_pass.html', patient_id=session['patid'])

@app.route('/addresults', methods=["POST", "GET"])
def addresults():
    if request.method == 'POST':
    
        patient_id = int(request.form.get('patientid'))
        patient_name = str(request.form.get('patientname'))
        bloodtype = request.form.get('bloodtype')
        date_tested = str(request.form.get('date_tested'))
        result_release_date = str(request.form.get('result_release_date'))
        doctor_in_charge = request.form.get('doctor_in_charge')
        test_type = request.form.get('test_type')
        file = request.files.get('attachment')

        
        if 'attachment' not in request.files:
            status = "Processing"
        elif 'attachment' in request.files:
            status = "Available/Uploaded"
        else:
            status ="Postponed"

    
        file_path = None 
        if file and file.filename != '':
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)
            file_path = "files/" + file.filename

        
        cursor, conn = get_db_cursor()
        query = """
            INSERT INTO `records` 
            (`id`,`patient_id`, `patient_name`, `bloodtype`, `date`, `dateresult`, `file`, `status`, `incharge`, `test_type`) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
        """
        values = (0,patient_id, patient_name, bloodtype, date_tested, result_release_date, file_path, status, doctor_in_charge, test_type)
                
        cursor, conn = get_db_cursor()   
         
        
        cursor.execute(query, values)
        conn.commit()
        
        cursor.close()
        conn.close()
        return redirect(url_for('admin_home'))

    
# Sign Out
@app.route('/sign_out')
def sign_out():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('land'))

if __name__ =='__main__':
    app.run(debug=True)
