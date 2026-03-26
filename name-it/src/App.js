(function () {
  const { MoleculeViewer, NameOptions, NameItConfig, NameItGame } = window;

  function App() {
    const rounds = window.NameItData?.rounds || [];
    const [roundIndex, setRoundIndex] = React.useState(() =>
      NameItGame.pickNextRoundIndex(rounds, -1)
    );
    const [selectedIds, setSelectedIds] = React.useState([]);
    const [hasChecked, setHasChecked] = React.useState(false);

    const currentRound = roundIndex >= 0 ? rounds[roundIndex] : null;
    const correctCount = currentRound
      ? currentRound.options.filter((option) => option.isCorrect).length
      : 0;

    React.useEffect(() => {
      if (!currentRound || hasChecked) {
        return;
      }
      if (selectedIds.length === correctCount) {
        setHasChecked(true);
      }
    }, [correctCount, currentRound, hasChecked, selectedIds]);

    const handleToggle = (optionId) => {
      if (hasChecked) {
        return;
      }

      setSelectedIds((currentSelected) =>
        currentSelected.includes(optionId)
          ? currentSelected.filter((id) => id !== optionId)
          : [...currentSelected, optionId]
      );
    };

    const handleNext = () => {
      if (!rounds.length) {
        return;
      }

      setRoundIndex((currentIndex) => NameItGame.pickNextRoundIndex(rounds, currentIndex));
      setSelectedIds([]);
      setHasChecked(false);
    };

    if (!currentRound) {
      return (
        <main className="page-shell">
          <section className="empty-state">{NameItConfig.emptyState}</section>
        </main>
      );
    }

    return (
      <main className="page-shell">
        <header className="topbar">
          <h1 className="app-title">{NameItConfig.title}</h1>
        </header>

        <section className="workspace">
          <MoleculeViewer cid={currentRound.cid} smiles={currentRound.smiles} />

          <section className="panel quiz-panel">
            <p className="quiz-instruction">
              Choose {correctCount} correct {correctCount === 1 ? "name" : "names"}:
            </p>
            <NameOptions
              options={currentRound.options}
              selectedIds={selectedIds}
              hasChecked={hasChecked}
              onToggle={handleToggle}
            />

            <div className="action-row">
              <button
                type="button"
                className="button button-secondary"
                onClick={handleNext}
              >
                Next
              </button>
            </div>
          </section>
        </section>
      </main>
    );
  }

  window.App = App;
})();
