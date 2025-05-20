from flask import Flask, request, render_template, session, redirect
from bson.objectid import ObjectId
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

@app.route('/logout')
def logout():
    session.clear()
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
    if 'id' not in session:
        return redirect('/login')
    
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

        # Si es una solicitud POST, guarda el comentario en MongoDB
        if request.method == 'POST':
            recepta_id = request.form.get("recepta_id")
            text = request.form.get("text")
            usuari = session.get("name")  # Nombre del usuario desde la sesión
            data_actual = datetime.now().strftime("%Y-%m-%d")  # Fecha actual

            if recepta_id and text:
                recepta = mongo_collection.find_one({"recepta_id": int(recepta_id)})
                if recepta:
                    mongo_collection.update_one(
                        {"recepta_id": int(recepta_id)},
                        {"$push": {"comentaris": {"usuari": usuari, "text": text, "data": data_actual}}}
                    )
                else:
                    mongo_collection.insert_one({
                        "recepta_id": int(recepta_id),
                        "comentaris": [{"usuari": usuari, "text": text, "data": data_actual}]
                    })

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

            user_id = session['id']
            user_has_rated = any(r["user_id"] == user_id for r in recipe_ratings)
            # Calcula la puntuació mitjana
            if recipe_ratings:
                # Extreu només els valors de "rating" dels diccionaris
                ratings_values = [r["rating"] for r in recipe_ratings]
                average_rating = round(sum(ratings_values) / len(ratings_values), 2)
            else:
                average_rating = "No hi ha puntuacions"

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
                "image_id": recipe_image,
                "user_has_rated": user_has_rated
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
        image = fs.get(ObjectId(image_id))
        return app.response_class(image.read(), content_type=image.content_type)
    except Exception as e:
        return f"Error al carregar la imatge: {str(e)}", 404

@app.route("/delete_recipe/<int:recipe_id>", methods=['POST'])
def delete_recipe(recipe_id):
    if 'id' not in session:
        return redirect('/login')

    try:
        with sclient.cursor() as cursor:
            # Verifica si el usuario es el creador de la receta
            sql = "SELECT autor_id FROM receptes WHERE id = %s"
            cursor.execute(sql, (recipe_id,))
            result = cursor.fetchone()

            if not result or result[0] != session['id']:
                return "No tens permís per eliminar aquesta recepta", 403

            # Elimina los ingredientes relacionados de la tabla intermedia
            sql_delete_ingredients = "DELETE FROM recepta_ingredients WHERE recepta_id = %s"
            cursor.execute(sql_delete_ingredients, (recipe_id,))

            # Elimina la receta de MySQL
            sql_delete_recipe = "DELETE FROM receptes WHERE id = %s"
            cursor.execute(sql_delete_recipe, (recipe_id,))

            # Elimina los comentarios relacionados de MongoDB
            mongo_db["comentaris"].delete_one({"recepta_id": recipe_id})

            # Elimina la imagen relacionada de MongoDB (GridFS)
            image_doc = mongo_db["receptes_images"].find_one({"recepta_id": recipe_id})
            if image_doc:
                fs.delete(image_doc["image_id"])  # Elimina la imagen de GridFS
                mongo_db["receptes_images"].delete_one({"recepta_id": recipe_id})

            # Elimina el histórico de cambios de MongoDB
            mongo_db["modificacions"].delete_one({"recepta_id": recipe_id})

            sclient.commit()
            return redirect("/index")

    except Exception as e:
        sclient.rollback()
        return f"Error al eliminar la recepta: {str(e)}"

@app.route("/rate_recipe/<int:recipe_id>", methods=['POST'])
def rate_recipe(recipe_id):
    if 'id' not in session:
        return redirect('/login')

    user_id = session['id']
    rating = int(request.form.get("rating"))  # Obté la puntuació del formulari

    try:
        # Conexió a la col·lecció de puntuacions
        ratings_collection = mongo_db["ratings"]

        # Verifica si l'usuari ja ha puntuat aquesta recepta
        existing_rating = ratings_collection.find_one({
            "recepta_id": recipe_id,
            "ratings.user_id": user_id
        })

        if existing_rating:
            return redirect("/index")
        # Si no ha puntuat, afegeix la puntuació
        ratings_collection.update_one(
            {"recepta_id": recipe_id},
            {"$push": {"ratings": {"user_id": user_id, "rating": rating}}},
            upsert=True
        )

        return redirect("/index")

    except Exception as e:
        return f"Error al puntuar la recepta: {str(e)}"

if __name__ == '__main__':
    app.run(port=5000, debug="True")