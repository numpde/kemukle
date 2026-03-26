(function () {
  function MoleculeViewer({ smiles, cid }) {
    const canvasRef = React.useRef(null);
    const statusRef = React.useRef(null);
    const rendererRef = React.useRef(null);
    const [themeName, setThemeName] = React.useState(
      window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
    );

    React.useEffect(() => {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handleChange = (event) => {
        setThemeName(event.matches ? "dark" : "light");
      };

      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }, []);

    React.useEffect(() => {
      if (!canvasRef.current || !statusRef.current) {
        return;
      }

      if (!rendererRef.current) {
        rendererRef.current = window.NameItMoleculeRenderer.create({
          canvas: canvasRef.current,
          statusElement: statusRef.current,
        });
      }

      rendererRef.current.render(smiles, themeName);
    }, [smiles, themeName]);

    return (
      <section className="panel molecule-panel">
        <div className="molecule-stage">
          <canvas
            ref={canvasRef}
            className="molecule-canvas"
            width="720"
            height="720"
          />
          <p ref={statusRef} className="molecule-status" data-cid={cid} />
          <a
            className="molecule-link"
            href={`https://pubchem.ncbi.nlm.nih.gov/compound/${cid}`}
            target="_blank"
            rel="noreferrer"
          >
            View on PubChem
          </a>
        </div>
      </section>
    );
  }

  window.MoleculeViewer = MoleculeViewer;
})();
