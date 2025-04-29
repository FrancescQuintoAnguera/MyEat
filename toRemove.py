#Classes
class Recepta:
    def __init__(self, nom, ingredients, passos, tipus):
        self.nom = nom
        self.ingredients = ingredients if ingredients else []
        self.passos = passos if passos else []
        self.tipus = tipus
#Polimorfisme
    def to_dict(self):
        return {
            'nom': self.nom,
            'ingredients': self.ingredients,
            'passos': self.passos,
            'tipus': self.tipus
        }
#Classes (Herencia)
class PrimerPlat(Recepta):
    def __init__(self, nom, ingredients, passos):
        super().__init__(nom, ingredients, passos, "Primer Plat")

class SegonPlat(Recepta):
    def __init__(self, nom, ingredients, passos):
        super().__init__(nom, ingredients, passos, "Segon Plat")

class Postres(Recepta):
    def __init__(self, nom, ingredients, passos):
        super().__init__(nom, ingredients, passos, "Postres")

#JSON
def llegir_receptes():
    try:
        with open('receptes.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []  


def desar_receptes(receptes):
    with open('receptes.json', 'w') as f:
        json.dump(receptes, f, indent=4)


@main.route('/', methods=['GET', 'POST'])
def index():
    receptes = llegir_receptes()  

#Buscar recepta
    tipus_filtre = request.args.get('tipus','')
    nom_buscat = request.args.get('nom','').lower()
    if tipus_filtre:
        receptes = [r for r in receptes if r['tipus'] == tipus_filtre]
    if nom_buscat:
        receptes = [r for r in receptes if nom_buscat in r['nom'].lower()]

#Afegir recepta
    if request.method == 'POST':
        nom_recepta = request.form.get('nom_recepta')
        ingredients = request.form.getlist('ing_recepta') #Llista
        quantitats = request.form.getlist('quant_recepta')  
        passos = request.form.getlist('pas_recepta')  
        tipus = request.form.get('tipus')

        
        ingredients_combinats = [{"ingredient": ing, "quantitat": quant} for ing, quant in zip(ingredients, quantitats)]

        nova_recepta = None  

        if tipus == 'Primer Plat':
            nova_recepta = PrimerPlat(nom_recepta, ingredients_combinats, passos)
        elif tipus == 'Segon Plat':
            nova_recepta = SegonPlat(nom_recepta, ingredients_combinats, passos)
        elif tipus == 'Postres':
            nova_recepta = Postres(nom_recepta, ingredients_combinats, passos)

        if nova_recepta:
            receptes.append(nova_recepta.to_dict())
            desar_receptes(receptes)  

    return render_template('index.html', receptes=receptes, tipus_filtre=tipus_filtre,nom_buscat=nom_buscat)