from flask import Flask, request, render_template, session
from databases import *
from keys import *

app = Flask(__name__)

app.secret_key = flask_pwd

@app.route('/singin', methods=['GET','POST'])
def singIn():
    if request.method == 'GET':
        return render_template("singin.html")
    
    elif request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        try:
        
            with sclient.cursor() as cursor:
                sql = """
                    INSERT INTO usuaris (nom, email, pass) VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (name, email, password))
        
            sclient.commit()
            return render_template("index.html")
        
        except Exception as e:
            sclient.rollback()
            return f"Error to sig-in: {str(e)}"

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    
    elif request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            with sclient.cursor() as cursor:
        
                sql = """
                    SELECT * FROM usuaris WHERE email = %s AND pass = %s
                """
                cursor.execute(sql, (email, password))
                result = cursor.fetchone()
        
                if result:
                    session['id'] = result[0]
                    session['name'] = result[1]
                    return render_template("index.html")
        
                else:
                    return render_template("login.html", error="Contrasenya o email incorrectes")
        
        except Exception as e:
            return f"Error to login: {str(e)}"

@app.route("/")
def form():
    return render_template("login.html")

@app.route("/index", methods=['GET','POST'])
def index():
    return render_template("index.html")

@app.route("/newrecipe", methods=['GET','POST'])
def newrecipe():
    if request.method == 'GET':
        return render_template("newrecipe.html")
    
    elif request.method == 'POST':
        name = request.form['name']
        steps = request.form['steps']
        type = request.form['type']
        author_id = session.get('id')
        
        if not author_id:
            return render_template("login.html", error="Inicia la sessió per afegir una recepta")
        
        try:
            with sclient.cursor() as cursor:
                print("entran al cusor")
                sql = """
                    INSERT INTO receptes (titol, tipus, pasos, autor_id)
                    VALUES (%s, %s, %s, %s)
            """
                cursor.execute(sql,(name, type ,steps, author_id))
                
            sclient.commit()
            
        except Exception as e:
            return f"Error to login: {str(e)}"


if __name__ == '__main__':
    app.run(port=5000, debug="True")
