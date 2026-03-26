(function () {
  function randomIndex(length) {
    return Math.floor(Math.random() * length);
  }

  function pickNextRoundIndex(rounds, currentIndex) {
    if (!rounds.length) {
      return -1;
    }

    if (rounds.length === 1) {
      return 0;
    }

    let nextIndex = randomIndex(rounds.length);
    while (nextIndex === currentIndex) {
      nextIndex = randomIndex(rounds.length);
    }
    return nextIndex;
  }

  window.NameItGame = {
    pickNextRoundIndex,
  };
})();
