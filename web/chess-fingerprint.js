// Chess Fingerprint - statystyki, radar i odtwarzacz partii z prawdopodobienstwem ruch po ruchu.
// Dane (JSON) eksportuje cotygodniowy pipeline na VPS: chess.olgamironczuk.pl.
(() => {
  const root = document.getElementById('chess-fingerprint');
  if (!root || !window.Chess || !window.Chessboard || !window.Chart) return;

  const API = root.dataset.api;
  const $ = id => document.getElementById(id);

  const TEXT = {
    pl: {
      loadingStats: 'Ładowanie statystyk…',
      loadingGame: 'Ładowanie partii…',
      loadError: 'Nie udało się wczytać danych. Spróbuj ponownie później.',
      pgnError: 'Nie udało się odczytać zapisu tej partii.',
      updated: 'Dane zaktualizowane:',
      games: 'Partie w bazie',
      wins: 'Wygrane',
      draws: 'Remisy',
      avgLength: 'Śr. długość',
      moves: 'ruchów',
      capturesPerMove: 'Bicia / ruch',
      castling: 'Roszada (krótka / długa)',
      timeClasses: 'Bullet / Blitz / Rapid',
      radar: ['Bicia/ruch', 'Wygrane', 'Remisy', 'Krótka roszada', 'Szachy/ruch', 'Blitz'],
      radarLabel: 'Wykres radarowy porównujący styl gry Magnusa Carlsena i Hikaru Nakamury',
      result: 'wynik',
      player: 'Gracz',
      move: 'Ruch',
      play: '▶ Odtwórz',
      pause: '⏸ Pauza',
      prev: 'Poprzedni ruch',
      next: 'Następny ruch',
      speed: 'Prędkość odtwarzania',
      random: '🎲 Losowa partia',
    },
    en: {
      loadingStats: 'Loading statistics…',
      loadingGame: 'Loading game…',
      loadError: 'Could not load the data. Please try again later.',
      pgnError: 'Could not read this game record.',
      updated: 'Data updated:',
      games: 'Games in database',
      wins: 'Wins',
      draws: 'Draws',
      avgLength: 'Avg. length',
      moves: 'moves',
      capturesPerMove: 'Captures / move',
      castling: 'Castling (short / long)',
      timeClasses: 'Bullet / Blitz / Rapid',
      radar: ['Captures/move', 'Wins', 'Draws', 'Short castling', 'Checks/move', 'Blitz'],
      radarLabel: 'Radar chart comparing the playing styles of Magnus Carlsen and Hikaru Nakamura',
      result: 'result',
      player: 'Player',
      move: 'Move',
      play: '▶ Play',
      pause: '⏸ Pause',
      prev: 'Previous move',
      next: 'Next move',
      speed: 'Playback speed',
      random: '🎲 Random game',
    },
  };
  const t = key => (TEXT[document.documentElement.lang] || TEXT.pl)[key];

  const PLAYERS = {
    MagnusCarlsen: {cls: 'magnus', name: 'Magnus Carlsen', icon: '♙', color: '#3a78a0', fill: 'rgba(58,120,160,.15)'},
    hikaru: {cls: 'hikaru', name: 'Hikaru Nakamura', icon: '♟', color: '#b86420', fill: 'rgba(184,100,32,.15)'},
  };

  const chess = new Chess();
  const board = Chessboard('cf-board', {
    position: 'start',
    pieceTheme: '/projekty/chess-fingerprint/pieces/{piece}.png',
  });

  let stats = null;
  let radar = null;
  let game = null;
  let gameCount = 0;
  let gameIndex = -1;
  let moves = [];
  let currentMove = 0;
  let playInterval = null;
  let speed = 1200;
  let lastError = null;

  const pct = v => (v != null ? (v * 100).toFixed(1) + '%' : '—');
  const num = (v, d = 1) => (v != null ? Number(v).toFixed(d) : '—');

  async function fetchJSON(path) {
    const res = await fetch(`${API}/${path}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  function el(tag, props = {}, children = []) {
    const node = Object.assign(document.createElement(tag), props);
    node.append(...children);
    return node;
  }

  function showMessage(container, text, isError = false) {
    container.replaceChildren(el('p', {className: 'cf-msg' + (isError ? ' cf-msg--error' : ''), textContent: text}));
  }

  // ── Karty graczy i radar ──────────────────────
  function renderCards() {
    const cards = Object.entries(PLAYERS).map(([username, p]) => {
      const s = stats.players[username] || {};
      const rows = [
        [t('games'), s.games_count ?? '—'],
        [t('wins'), pct(s.win_rate)],
        [t('draws'), pct(s.draw_rate)],
        [t('avgLength'), `${num(s.avg_fullmoves)} ${t('moves')}`],
        [t('capturesPerMove'), num(s.avg_captures_per_move, 3)],
        [t('castling'), `${pct(s.kingside_castle_rate)} / ${pct(s.queenside_castle_rate)}`],
        [t('timeClasses'), `${pct(s.bullet_share)} / ${pct(s.blitz_share)} / ${pct(s.rapid_share)}`],
      ];
      return el('div', {className: `cf-card cf-card--${p.cls}`}, [
        el('h3', {textContent: `${p.icon} ${p.name}`}),
        el('dl', {}, rows.map(([label, value]) => el('div', {className: 'cf-stat'}, [
          el('dt', {textContent: label}),
          el('dd', {textContent: String(value)}),
        ]))),
      ]);
    });
    $('cf-cards').replaceChildren(...cards);
    $('cf-updated').textContent = `${t('updated')} ${new Date(stats.updated_at).toLocaleDateString(document.documentElement.lang)}`;
  }

  function renderRadar() {
    // Skale dobrane recznie pod zakres wartosci obu graczy (jak w oryginalnym widgecie).
    const mins = [0, 0.3, 0, 0, 0, 0];
    const maxs = [0.15, 0.8, 0.35, 1, 0.08, 1];
    const scaled = s => [s.avg_captures_per_move, s.win_rate, s.draw_rate, s.kingside_castle_rate, s.avg_checks_per_move, s.blitz_share]
      .map((v, i) => (v == null ? 0 : Math.min(1, Math.max(0, (v - mins[i]) / (maxs[i] - mins[i])))));

    const canvas = $('cf-radar');
    canvas.setAttribute('aria-label', t('radarLabel'));
    if (radar) {
      radar.data.labels = t('radar');
      radar.update();
      return;
    }
    const css = getComputedStyle(root);
    radar = new Chart(canvas, {
      type: 'radar',
      data: {
        labels: t('radar'),
        datasets: Object.entries(PLAYERS).map(([username, p]) => ({
          label: p.name.split(' ')[0],
          data: scaled(stats.players[username] || {}),
          borderColor: p.color,
          backgroundColor: p.fill,
          pointBackgroundColor: p.color,
          borderWidth: 2,
        })),
      },
      options: {
        animation: false,
        maintainAspectRatio: false,
        scales: {
          r: {
            min: 0,
            max: 1,
            ticks: {display: false, stepSize: 0.25},
            grid: {color: 'rgba(0,0,0,.07)'},
            angleLines: {color: 'rgba(0,0,0,.07)'},
            pointLabels: {color: css.getPropertyValue('--text-dim').trim() || '#6b6b62', font: {size: 11}},
          },
        },
        plugins: {legend: {labels: {color: css.getPropertyValue('--text').trim() || '#201f1c', boxWidth: 14, font: {size: 12}}}},
      },
    });
  }

  async function loadStats() {
    showMessage($('cf-cards'), t('loadingStats'));
    try {
      stats = await fetchJSON('stats.json');
      renderCards();
      renderRadar();
    } catch (e) {
      showMessage($('cf-cards'), t('loadError'), true);
    }
  }

  // ── Partie ────────────────────────────────────
  function renderGameInfo() {
    const info = $('cf-game-info');
    if (lastError) { info.textContent = t(lastError); return; }
    if (!game) { info.textContent = t('loadingGame'); return; }
    const p = PLAYERS[game.username] || PLAYERS.MagnusCarlsen;
    const meta = [
      game.played_at ? game.played_at.substring(0, 10) : '',
      game.time_class || '',
      game.player_result ? `${t('result')}: ${game.player_result}` : '',
    ].filter(Boolean).join(' · ');
    info.replaceChildren(
      el('strong', {textContent: game.white_username || '?'}), ' vs ', el('strong', {textContent: game.black_username || '?'}),
      el('br'), meta, el('br'),
      `${t('player')}: `, el('strong', {textContent: p.name, style: `color:${p.color}`}),
    );
  }

  async function loadRandomGame() {
    stopPlay();
    lastError = null;
    game = null;
    renderGameInfo();
    try {
      if (!gameCount) gameCount = (await fetchJSON('games/index.json')).count || 0;
      if (!gameCount) throw new Error('empty');
      // Nie losuj drugi raz tej samej partii pod rzad.
      let i = Math.floor(Math.random() * gameCount);
      if (gameCount > 1 && i === gameIndex) i = (i + 1) % gameCount;
      gameIndex = i;
      setupGame(await fetchJSON(`games/${i}.json`));
    } catch (e) {
      lastError = 'loadError';
      renderGameInfo();
    }
  }

  function setupGame(data) {
    chess.reset();
    if (!chess.load_pgn(data.pgn)) {
      lastError = 'pgnError';
      renderGameInfo();
      return;
    }
    moves = chess.history();
    game = data;
    chess.reset();
    board.position('start', false);
    currentMove = 0;
    renderGameInfo();
    updateProbBar();
    updateCounter();
  }

  // ── Pasek prawdopodobienstwa ──────────────────
  // magnus_probs ma jeden wpis na kazdy polruch partii.
  function updateProbBar() {
    const probs = game ? game.magnus_probs : [];
    const mp = currentMove > 0 && probs[currentMove - 1] != null ? probs[currentMove - 1] : 0.5;
    const mPct = Math.round(mp * 100);
    const hPct = 100 - mPct;
    $('cf-magnus-fill').style.width = mPct + '%';
    $('cf-magnus-fill').textContent = mPct > 20 ? mPct + '%' : '';
    $('cf-hikaru-fill').textContent = hPct > 20 ? hPct + '%' : '';
    $('cf-magnus-label').textContent = `Magnus ${mPct}%`;
    $('cf-hikaru-label').textContent = `Hikaru ${hPct}%`;
  }

  function updateCounter() {
    $('cf-counter').textContent = `${t('move')} ${Math.ceil(currentMove / 2)} / ${Math.ceil(moves.length / 2)}`;
  }

  // ── Nawigacja i autoodtwarzanie ───────────────
  function goTo(idx) {
    if (idx < 0 || idx > moves.length) return;
    chess.reset();
    for (let i = 0; i < idx; i++) chess.move(moves[i]);
    board.position(chess.fen(), false);
    currentMove = idx;
    updateProbBar();
    updateCounter();
    if (idx >= moves.length) stopPlay();
  }

  function startPlay() {
    if (!moves.length) return;
    if (currentMove >= moves.length) goTo(0);
    playInterval = setInterval(() => goTo(currentMove + 1), speed);
    $('cf-play').textContent = t('pause');
    $('cf-play').setAttribute('aria-pressed', 'true');
  }

  function stopPlay() {
    clearInterval(playInterval);
    playInterval = null;
    $('cf-play').textContent = t('play');
    $('cf-play').setAttribute('aria-pressed', 'false');
  }

  function setSpeed(button) {
    speed = Number(button.dataset.speed);
    root.querySelectorAll('[data-speed]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    if (playInterval) { stopPlay(); startPlay(); }
  }

  function applyStaticText() {
    $('cf-prev').setAttribute('aria-label', t('prev'));
    $('cf-next').setAttribute('aria-label', t('next'));
    $('cf-speeds').setAttribute('aria-label', t('speed'));
    $('cf-new').textContent = t('random');
    $('cf-play').textContent = playInterval ? t('pause') : t('play');
  }

  $('cf-prev').addEventListener('click', () => { stopPlay(); goTo(currentMove - 1); });
  $('cf-next').addEventListener('click', () => { stopPlay(); goTo(currentMove + 1); });
  $('cf-play').addEventListener('click', () => (playInterval ? stopPlay() : startPlay()));
  $('cf-new').addEventListener('click', loadRandomGame);
  root.querySelectorAll('[data-speed]').forEach(b => b.addEventListener('click', () => setSpeed(b)));
  window.addEventListener('resize', () => board.resize());

  document.addEventListener('languagechange', () => {
    applyStaticText();
    renderGameInfo();
    updateCounter();
    if (stats) { renderCards(); renderRadar(); }
  });

  applyStaticText();
  loadStats();
  loadRandomGame();
})();
