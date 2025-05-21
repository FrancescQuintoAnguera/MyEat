from flask import Flask, request, render_template, session, redirect
from bson.objectid import ObjectId
from datetime import datetime
from databases import *
from keys import *
from gridfs import GridFS
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = flask_pwd

mongo_db = mclient["MyEat"]
fs = GridFS(mongo_db)


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
            return redirect("/login")
        
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
        image = request.files.get('image')

        if not author_id:
            return render_template("login.html", error="Inicia la sessió per afegir una recepta")
        
        try:
            with sclient.cursor() as cursor:
        
                sql = """
                    INSERT INTO receptes (titol, tipus, pasos, autor_id)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (name, recipe_type, steps, author_id))
                recipe_id = cursor.lastrowid

                many_to_many = """
                    INSERT INTO recepta_ingredients (recepta_id, ingredient_id, pes)
                    VALUES (%s, %s, %s)
                """
                for ingredient_id in selected_ingredients:
                    cursor.execute(many_to_many, (recipe_id, ingredient_id, weight))

                if image and image.filename != "":
                    filename = secure_filename(image.filename)
                    file_id = fs.put(image, filename=filename, content_type=image.content_type)

                    mongo_db["receptes_images"].insert_one({
                        "recepta_id": recipe_id,
                        "image_id": file_id
                    })

            sclient.commit()
            return redirect("/index")
        except Exception as e:
            sclient.rollback()
            return f"Error al crear la recepta: {str(e)}"

@app.route("/index", methods=['GET', 'POST'])
def index():
    if 'id' not in session:
        return redirect('/login')

    try:

        user_name = session.get('name')

        with sclient.cursor() as cursor:

            sql = """
                SELECT receptes.id, receptes.titol, receptes.tipus, receptes.pasos, usuaris.nom, receptes.autor_id
                FROM receptes 
                INNER JOIN usuaris ON receptes.autor_id = usuaris.id;
            """
            cursor.execute(sql)
            recipes = cursor.fetchall()

            sql2 = """
                SELECT ri.recepta_id, i.nom, ri.pes
                FROM recepta_ingredients ri
                INNER JOIN ingredients i ON ri.ingredient_id = i.id;
            """
            cursor.execute(sql2)
            ingredients = cursor.fetchall()

        if request.method == 'POST':
            recepta_id = request.form.get("recepta_id")
            text = request.form.get("text")
            usuari = session.get("name")  
            data_actual = datetime.now().strftime("%Y-%m-%d")  

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

        comments = list(mongo_collection.find())
        ratings = list(ratings_collection.find())
        images = list(images_collection.find())

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

            if recipe_ratings:

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

        return render_template("index.html", recipes=recipes_with_details, user_name=user_name)

    except Exception as e:
        return f"Error al carregar {str(e)}"

@app.route("/edit_recipe/<int:recipe_id>", methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    if 'id' not in session:
        return redirect('/login')

    try:
        with sclient.cursor() as cursor:

            sql = "SELECT autor_id FROM receptes WHERE id = %s"
            cursor.execute(sql, (recipe_id,))
            result = cursor.fetchone()

            if not result or result[0] != session['id']:
                return "No tens permís per editar aquesta recepta", 403

            if request.method == 'GET':

                sql = """
                    SELECT titol, tipus, pasos 
                    FROM receptes 
                    WHERE id = %s
                """
                cursor.execute(sql, (recipe_id,))
                recipe = cursor.fetchone()

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
                title = request.form['title']
                steps = request.form['steps']
                recipe_type = request.form['type']
                changes = request.form['changes']
                image = request.files.get('image')

                sql = """
                    UPDATE receptes 
                    SET titol = %s, tipus = %s, pasos = %s 
                    WHERE id = %s
                """
                cursor.execute(sql, (title, recipe_type, steps, recipe_id))

                if image and image.filename != "":
                    filename = secure_filename(image.filename)
                    file_id = fs.put(image, filename=filename, content_type=image.content_type)
                    
                    mongo_db["receptes_images"].update_one(
                        {"recepta_id": recipe_id},
                        {"$set": {"image_id": file_id}},
                        upsert=True
                    )
                
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

            sql = """
                SELECT autor_id FROM receptes WHERE id = %s
                """
            
            cursor.execute(sql, (recipe_id,))
            result = cursor.fetchone()

            if not result or result[0] != session['id']:
                return "No tens permís per eliminar aquesta recepta", 403
            
            sql_delete_ingredients = """
            DELETE FROM recepta_ingredients WHERE recepta_id = %s
            """
            cursor.execute(sql_delete_ingredients, (recipe_id,))

            sql_delete_recipe = """
                DELETE FROM receptes WHERE id = %s
                """
            cursor.execute(sql_delete_recipe, (recipe_id,))

            mongo_db["comentaris"].delete_one({"recepta_id": recipe_id})

            image_doc = mongo_db["receptes_images"].find_one({"recepta_id": recipe_id})
            if image_doc:
                fs.delete(image_doc["image_id"]) 
                mongo_db["receptes_images"].delete_one({"recepta_id": recipe_id})

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
    rating = int(request.form.get("rating"))  

    try:
        
        ratings_collection = mongo_db["ratings"]

        
        existing_rating = ratings_collection.find_one({
            "recepta_id": recipe_id,
            "ratings.user_id": user_id
        })

        if existing_rating:
            return redirect("/index")
        
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