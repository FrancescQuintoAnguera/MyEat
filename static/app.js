function comment(button) {
    // Verifica si ya existe una caja de comentarios para evitar duplicados
    const existingCommentBox = button.parentElement.querySelector(".comment-box");
    if (existingCommentBox) {
        return; // No hace nada si ya existe una caja de comentarios
    }

    // Crea un formulario para la caja de comentarios
    const form = document.createElement("form");
    form.action = "/index"; // Enviar el comentario a la misma ruta
    form.method = "POST";
    form.classList.add("comment-box");

    // Crea un campo oculto para el ID de la receta
    const recipeIdInput = document.createElement("input");
    recipeIdInput.type = "hidden";
    recipeIdInput.name = "recepta_id";
    recipeIdInput.value = button.getAttribute("value"); // Obtiene el ID de la receta del botón

    // Crea un área de texto para el comentario
    const textarea = document.createElement("textarea");
    textarea.name = "text";
    textarea.placeholder = "Escribe tu comentario aquí...";
    textarea.rows = 4;
    textarea.cols = 50;
    textarea.required = true;

    // Crea un botón para enviar el formulario
    const submitButton = document.createElement("button");
    submitButton.type = "submit";
    submitButton.textContent = "Enviar";

    // Agrega los elementos al formulario
    form.appendChild(recipeIdInput);
    form.appendChild(textarea);
    form.appendChild(submitButton);

    // Inserta el formulario justo debajo del botón seleccionado
    button.insertAdjacentElement("afterend", form);
}