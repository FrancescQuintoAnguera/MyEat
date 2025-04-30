from flask import Flask, request, render_template
from databases import *

app = Flask(__name__)

@app.route('/singin', methods=['POST'])
def singIn():
    print("Entrant a la funcio")
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    
    try:
        with sclient.cursor() as cursor:
            print("Avans de insert")
            sql = "INSERT INTO usuaris (nom, email, pass) VALUES (%s, %s, %s)"
            cursor.execute(sql, (name, email, password))
        sclient.commit()
        print("Despres de insert")
        return render_template("index.html")
    except Exception as e:
        sclient.rollback()
        return f"Error to sig-in: {str(e)}"

@app.route("/")
def form():
    return render_template("singin.html")

if __name__ == '__main__':
    app.run(port=5000, debug="True")
