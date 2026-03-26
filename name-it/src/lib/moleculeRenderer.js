(function () {
  function create({ canvas, statusElement }) {
    const drawer = new SmilesDrawer.Drawer({
      width: canvas.width,
      height: canvas.height,
    });
    const context = canvas.getContext("2d");

    function clear() {
      context.clearRect(0, 0, canvas.width, canvas.height);
    }

    function render(smiles, themeName) {
      clear();

      if (!smiles) {
        statusElement.textContent = "This round has no drawable molecule.";
        return;
      }

      statusElement.textContent = "";

      SmilesDrawer.parse(
        smiles,
        (tree) => {
          clear();
          drawer.draw(tree, canvas, themeName === "dark" ? "dark" : "light");
        },
        (error) => {
          clear();
          statusElement.textContent = "Could not render this SMILES string.";
          console.error("SMILES render error:", error);
        }
      );
    }

    return { render };
  }

  window.NameItMoleculeRenderer = { create };
})();
