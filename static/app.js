document.getElementById('addIngredients').addEventListener('click', function() {
    var ingredients = document.getElementById('ingredients');
    var ingredientsDiv = document.createElement('div');
    ingredientsDiv.className = 'ingredientsDiv';

    var newIngredient = document.createElement('input');
    newIngredient.type = 'text';
    newIngredient.name = 'ing_recepta';
    newIngredient.placeholder = 'Ingredients';
    newIngredient.className = 'ingredients';

    var newQuantity = document.createElement('input');
    newQuantity.type = 'text';
    newQuantity.name = 'quant_recepta';
    newQuantity.placeholder = '20G';
    newQuantity.className = 'quantitats';

    ingredientsDiv.appendChild(newIngredient);
    ingredientsDiv.appendChild(newQuantity);
    ingredients.appendChild(ingredientsDiv);
});

document.getElementById('addPassos').addEventListener('click', function() {
    var passos = document.getElementById('passos');
    var newPasso = document.createElement('input');
    newPasso.type = 'text';
    newPasso.name = 'pas_recepta';
    newPasso.placeholder = 'Pas a seguir';
    newPasso.className = 'passos';
    newPasso.style.fontSize = '16px';

    passos.appendChild(newPasso);
});
