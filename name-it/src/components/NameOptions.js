(function () {
  function getOptionState(option, isSelected, hasChecked) {
    if (!hasChecked) {
      return isSelected ? "is-selected" : "";
    }

    if (option.isCorrect && isSelected) {
      return "is-correct-selected";
    }
    if (option.isCorrect) {
      return "is-correct-missed";
    }
    if (isSelected) {
      return "is-incorrect-selected";
    }
    return "";
  }

  function NameOptions({ options, selectedIds, hasChecked, onToggle }) {
    const selectedSet = new Set(selectedIds);

    return (
      <div className="options-grid">
        {options.map((option) => {
          const isSelected = selectedSet.has(option.id);
          const stateClassName = getOptionState(option, isSelected, hasChecked);

          return (
            <label key={option.id} className={`option-card ${stateClassName}`.trim()}>
              <span className="option-input">
                <input
                  type="checkbox"
                  checked={isSelected}
                  disabled={hasChecked}
                  onChange={() => onToggle(option.id)}
                />
              </span>
              <span className="option-label">{option.label}</span>
              {hasChecked && option.isCorrect && (
                <span className="option-note option-note-correct">✓</span>
              )}
              {hasChecked && !option.isCorrect && isSelected && (
                <span className="option-note option-note-wrong">✕</span>
              )}
            </label>
          );
        })}
      </div>
    );
  }

  window.NameOptions = NameOptions;
})();
