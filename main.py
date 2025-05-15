from flask import Flask, request, render_template, session, redirect
from datetime import datetime
from databases import *
from keys import *
from databases import mclient  # Importa la conexión a MongoDB desde databases.py
from gridfs import GridFS
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = flask_pwd

# Conexión a MongoDB y configuración de GridFS
mongo_db = mclient["MyEat"]
fs = GridFS(mongo_db)

#SQL
@app.route('/')
def root():
    return redirect('/login')

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
                    return redirect('/index')
        
                else:
                    return render_template("login.html", error="Contrasenya o email incorrectes")
        
        except Exception as e:
            return f"Error to login: {str(e)}"

@app.route("/newrecipe", methods=['GET', 'POST'])
def newrecipe():
    if request.method == 'GET':
        try:
            with sclient.cursor() as cursor:
                sql = "SELECT id, nom FROM ingredients"
                cursor.execute(sql)
                ingredients = cursor.fetchall()

            return render_template("newrecipe.html", ingredients=ingredients)
        except Exception as e:
            return f"Error as load: {str(e)}"
    
    elif request.method == 'POST':
        name = request.form['name']
        steps = request.form['steps']
        recipe_type = request.form['type']
        author_id = session.get('id')
        weight = request.form['weight']
        selected_ingredients = request.form.getlist('ingredients')
        image = request.files.get('image')  # Obtén la imagen del formulario

        if not author_id:
            return render_template("login.html", error="Inicia la sessió per afegir una recepta")
        
        try:
            with sclient.cursor() as cursor:
                # Inserta la receta en MySQL
                sql = """
                    INSERT INTO receptes (titol, tipus, pasos, autor_id)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (name, recipe_type, steps, author_id))
                recipe_id = cursor.lastrowid

                # Inserta los ingredientes en la tabla intermedia
                many_to_many = """
                    INSERT INTO recepta_ingredients (recepta_id, ingredient_id, pes)
                    VALUES (%s, %s, %s)
                """
                for ingredient_id in selected_ingredients:
                    cursor.execute(many_to_many, (recipe_id, ingredient_id, weight))

                # Guarda la imagen en GridFS si existe
                if image and image.filename != "":
                    filename = secure_filename(image.filename)
                    file_id = fs.put(image, filename=filename, content_type=image.content_type)

                    # Guarda la referencia de la imagen en MongoDB
                    mongo_db["receptes_images"].insert_one({
                        "recepta_id": recipe_id,
                        "image_id": file_id
                    })

            sclient.commit()
            return redirect("/index")
        except Exception as e:
            sclient.rollback()
            return f"Error al crear la recepta: {str(e)}"

#MongoDB

@app.route("/index", methods=['GET', 'POST'])
def index():
    if 'id' not in session:
        return redirect('/login')

    try:
        with sclient.cursor() as cursor:
            # Consulta para obtener las recetas, incluyendo el autor_id
            sql = """
                SELECT receptes.id, receptes.titol, receptes.tipus, receptes.pasos, usuaris.nom, receptes.autor_id
                FROM receptes 
                INNER JOIN usuaris ON receptes.autor_id = usuaris.id;
            """
            cursor.execute(sql)
            recipes = cursor.fetchall()

            # Consulta para obtener los ingredientes
            sql2 = """
                SELECT ri.recepta_id, i.nom, ri.pes
                FROM recepta_ingredients ri
                INNER JOIN ingredients i ON ri.ingredient_id = i.id;
            """
            cursor.execute(sql2)
            ingredients = cursor.fetchall()

        # Conexión a MongoDB
        mongo_db = mclient["MyEat"]
        mongo_collection = mongo_db["comentaris"]
        ratings_collection = mongo_db["ratings"]
        images_collection = mongo_db["receptes_images"]

        # Obtén los comentarios, puntuaciones e imágenes desde MongoDB
        comments = list(mongo_collection.find())
        ratings = list(ratings_collection.find())
        images = list(images_collection.find())

        # Combina las recetas con sus ingredientes, comentarios, puntuaciones e imágenes
        recipes_with_details = []
        for recipe in recipes:
            recipe_id = recipe[0]
            recipe_ingredients = [ing for ing in ingredients if ing[0] == recipe_id]
            recipe_comments = next(
                (comment["comentaris"] for comment in comments if comment["recepta_id"] == recipe_id), []
            )
            recipe_ratings = next(
                (rating["ratings"] for rating in ratings if rating["recepta_id"] == recipe_id), []
            )
            recipe_image = next(
                (img["image_id"] for img in images if img["recepta_id"] == recipe_id), None
            )
            average_rating = round(sum(recipe_ratings) / len(recipe_ratings), 2) if recipe_ratings else "No hi ha puntuacions"
            recipes_with_details.append({
                "id": recipe_id,
                "title": recipe[1],
                "type": recipe[2],
                "steps": recipe[3],
                "author": recipe[4],
                "author_id": recipe[5],
                "ingredients": recipe_ingredients,
                "comments": recipe_comments,
                "average_rating": average_rating,
                "image_id": recipe_image  # Incluye el ID de la imagen
            })

        return render_template("index.html", recipes=recipes_with_details)

    except Exception as e:
        return f"Error al carregar {str(e)}"

@app.route("/edit_recipe/<int:recipe_id>", methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    if 'id' not in session:
        return redirect('/login')

    try:
        with sclient.cursor() as cursor:
            # Verifica si el usuario es el creador de la receta
            sql = "SELECT autor_id FROM receptes WHERE id = %s"
            cursor.execute(sql, (recipe_id,))
            result = cursor.fetchone()

            if not result or result[0] != session['id']:
                return "No tens permís per editar aquesta recepta", 403

            if request.method == 'GET':
                # Obtén los datos actuales de la receta
                sql = """
                    SELECT titol, tipus, pasos 
                    FROM receptes 
                    WHERE id = %s
                """
                cursor.execute(sql, (recipe_id,))
                recipe = cursor.fetchone()

                # Obtén los ingredientes actuales
                sql2 = """
                    SELECT i.id, i.nom, ri.pes 
                    FROM recepta_ingredients ri
                    INNER JOIN ingredients i ON ri.ingredient_id = i.id
                    WHERE ri.recepta_id = %s
                """
                cursor.execute(sql2, (recipe_id,))
                ingredients = cursor.fetchall()

                return render_template("edit_recipe.html", recipe=recipe, ingredients=ingredients)

            elif request.method == 'POST':
                # Actualiza la receta en MySQL
                title = request.form['title']
                steps = request.form['steps']
                recipe_type = request.form['type']
                changes = request.form['changes']
                image = request.files.get('image')  # Obtén la imagen del formulario

                sql = """
                    UPDATE receptes 
                    SET titol = %s, tipus = %s, pasos = %s 
                    WHERE id = %s
                """
                cursor.execute(sql, (title, recipe_type, steps, recipe_id))

                # Guarda la imagen en GridFS si existe
                if image and image.filename != "":
                    filename = secure_filename(image.filename)
                    file_id = fs.put(image, filename=filename, content_type=image.content_type)

                    # Actualiza la referencia de la imagen en MongoDB
                    mongo_db["receptes_images"].update_one(
                        {"recepta_id": recipe_id},
                        {"$set": {"image_id": file_id}},
                        upsert=True
                    )

                # Guarda el histórico de cambios en MongoDB
                mongo_db["modificacions"].update_one(
                    {"recepta_id": recipe_id},
                    {"$push": {"modificacions": {
                        "data": datetime.now().strftime("%Y-%m-%d"),
                        "usuari": session['name'],
                        "canvis": changes
                    }}},
                    upsert=True
                )

                sclient.commit()
                return redirect("/index")

    except Exception as e:
        sclient.rollback()
        return f"Error al editar la recepta: {str(e)}"

@app.route("/image/<image_id>")
def get_image(image_id):
    try:
        # Convierte el image_id a ObjectId si es necesario
        from bson.objectid import ObjectId
        image = fs.get(ObjectId(image_id))
        return app.response_class(image.read(), content_type=image.content_type)
    except Exception as e:
        return f"Error al carregar la imatge: {str(e)}", 404

if __name__ == '__main__':
    app.run(port=5000, debug="True")
