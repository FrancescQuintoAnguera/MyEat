function addIngredient() {
    const ingredientsDiv = document.getElementById("ingredients");
    const newIngredientDiv = document.createElement("div");
    newIngredientDiv.classList.add("ingredientsDiv");
    newIngredientDiv.innerHTML = `
        <input type="text" class="ingredients" name="ing_recepta" placeholder="Ingredients" required>
        <input type="text" class="quantitats" name="quant_recepta" placeholder="20G" required>
    `;
    ingredientsDiv.appendChild(newIngredientDiv);
}

