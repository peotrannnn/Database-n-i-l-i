(function () {
  let audioCtx = null;
  let unlocked = false;
  let hasGesture = false;
  let lastHover = 0;
  let master = null;
  let queuedType = null;

  const presets = {
    hover:       { wave: 'sine',     freqs: [520, 650], dur: .045, vol: .016, delay: .016, second: 1.16 },
    toastHover:  { wave: 'triangle', freqs: [410, 540], dur: .055, vol: .016, delay: .018, second: 1.14 },
    focus:       { wave: 'triangle', freqs: [330, 420, 560], dur: .075, vol: .018, delay: .026, second: 1.12 },
    click:       { wave: 'square',   freqs: [300, 205], dur: .060, vol: .022, delay: .010, second: .58 },
    submit:      { wave: 'triangle', freqs: [370, 520, 690, 840], dur: .170, vol: .026, delay: .038, second: 1.40 },
    open:        { wave: 'triangle', freqs: [340, 470, 620, 780], dur: .160, vol: .025, delay: .032, second: 1.36 },
    close:       { wave: 'sine',     freqs: [520, 350, 220], dur: .100, vol: .021, delay: .024, second: .68 },
    closeTiny:   { wave: 'sine',     freqs: [560, 360], dur: .055, vol: .014, delay: .014, second: .72 },
    dropdown:    { wave: 'square',   freqs: [560, 470, 610], dur: .100, vol: .020, delay: .022, second: 1.16 },
    check:       { wave: 'triangle', freqs: [460, 680, 860], dur: .105, vol: .024, delay: .030, second: 1.36 },
    uncheck:     { wave: 'sine',     freqs: [390, 260], dur: .075, vol: .019, delay: .020, second: .72 },
    enter:       { wave: 'triangle', freqs: [470, 660, 800], dur: .105, vol: .024, delay: .024, second: 1.28 },
    success:     { wave: 'triangle', freqs: [392, 523, 659, 784], dur: .210, vol: .026, delay: .045, second: 1.42 },
    error:       { wave: 'sawtooth', freqs: [235, 160, 112, 92], dur: .175, vol: .022, delay: .033, second: .60 },
    login:       { wave: 'triangle', freqs: [350, 440, 660, 820], dur: .205, vol: .025, delay: .040, second: 1.38 },
    logout:      { wave: 'sine',     freqs: [720, 540, 380, 250], dur: .175, vol: .023, delay: .033, second: .72 },
    approve:     { wave: 'triangle', freqs: [410, 615, 820, 980], dur: .220, vol: .026, delay: .042, second: 1.45 },
    reject:      { wave: 'square',   freqs: [270, 190, 135], dur: .150, vol: .021, delay: .030, second: .62 }
  };

  function getCtx() {
    if (!hasGesture) return null;
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return null;
      audioCtx = new AudioContext({ latencyHint: 'interactive' });
      master = audioCtx.createGain();
      master.gain.value = 0.66;
      master.connect(audioCtx.destination);
    }
    return audioCtx;
  }

  function unlock() {
    hasGesture = true;
    const ctx = getCtx();
    if (!ctx) return Promise.resolve(false);
    const resume = ctx.state === 'suspended' ? ctx.resume() : Promise.resolve();
    return resume.then(() => {
      unlocked = true;
      if (queuedType) {
        const type = queuedType;
        queuedType = null;
        window.setTimeout(() => playRaw(type), 20);
      }
      return true;
    }).catch(() => false);
  }

  function envGain(ctx, now, duration, volume) {
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.linearRampToValueAtTime(volume, now + 0.004);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
    return gain;
  }

  function makeVoice(ctx, preset, start, volumeScale, octaveScale) {
    const osc = ctx.createOscillator();
    const gain = envGain(ctx, start, preset.dur, preset.vol * volumeScale);
    const filter = ctx.createBiquadFilter();
    const lfo = ctx.createOscillator();
    const lfoGain = ctx.createGain();
    const freqs = preset.freqs;
    const step = preset.dur / Math.max(1, freqs.length - 1);

    osc.type = preset.wave;
    osc.frequency.setValueAtTime(Math.max(40, freqs[0] * octaveScale), start);
    freqs.slice(1).forEach((freq, index) => {
      osc.frequency.exponentialRampToValueAtTime(Math.max(40, freq * octaveScale), start + step * (index + 1));
    });

    lfo.type = 'sine';
    lfo.frequency.setValueAtTime(10 + Math.abs(Math.cos(start * 7)) * 7, start);
    lfoGain.gain.setValueAtTime(1.8 + Math.abs(Math.sin(start * 9)) * 4.5, start);
    lfo.connect(lfoGain);
    lfoGain.connect(osc.frequency);

    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(1450 + Math.cos(start * 5) * 160, start);
    filter.Q.setValueAtTime(0.45, start);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(master || ctx.destination);
    osc.start(start);
    lfo.start(start);
    osc.stop(start + preset.dur + .04);
    lfo.stop(start + preset.dur + .04);
  }

  function playRaw(type) {
    const ctx = getCtx();
    if (!ctx || ctx.state === 'suspended') return false;
    const preset = presets[type] || presets.click;
    const now = ctx.currentTime + 0.001;
    makeVoice(ctx, preset, now, 1, 1);
    if (preset.second) makeVoice(ctx, preset, now + (preset.delay || .025), .36, preset.second);
    return true;
  }

  function play(type) {
    if (type === 'hover') {
      const nowMs = performance.now();
      if (nowMs - lastHover < 75) return;
      lastHover = nowMs;
    }

    if (!hasGesture) {
      if (type !== 'hover' && type !== 'focus' && type !== 'toastHover') queuedType = type;
      return;
    }

    const ctx = getCtx();
    if (!ctx) return;
    if (ctx.state === 'suspended' || !unlocked) {
      unlock().then((ok) => { if (ok && type !== 'hover') playRaw(type); });
      return;
    }
    playRaw(type);
  }

  ['pointerdown', 'keydown', 'touchstart'].forEach((name) => {
    window.addEventListener(name, () => unlock(), { once: true, capture: true, passive: true });
  });

  document.addEventListener('pointerover', function (event) {
    if (event.target.closest('button, .primary-btn, .ghost-btn, .danger-btn, .success-btn, .link-btn, .nav a, .logo, .dropdown-menu a, .check-row, .check-chip')) play('hover');
  });

  document.addEventListener('pointerdown', function (event) {
    if (event.target.closest('button, .primary-btn, .ghost-btn, .danger-btn, .success-btn, .link-btn, .nav a, .logo, .dropdown-menu a, .toast')) play('click');
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Enter') play('enter');
  });

  window.LaiSound = { play, unlock };
})();
