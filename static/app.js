
function hideLoadingScreen() {
  const loading = document.getElementById('loading-screen');
  if (!loading) return;
  const startedAt = Number(loading.dataset.startedAt || performance.now());
  const elapsed = performance.now() - startedAt;
  const wait = Math.max(0, 520 - elapsed);
  window.setTimeout(() => {
    loading.classList.add('is-hidden');
    window.setTimeout(() => loading.remove(), 520);
  }, wait);
}

document.addEventListener('DOMContentLoaded', () => {
  const loading = document.getElementById('loading-screen');
  if (loading) loading.dataset.startedAt = String(performance.now());
});

window.addEventListener('load', hideLoadingScreen);
window.setTimeout(hideLoadingScreen, 1500);

function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal || modal.classList.contains('open')) return;
  modal.classList.remove('closing');
  modal.classList.add('open');
  document.body.classList.add('modal-is-open');
  modal.setAttribute('aria-hidden', 'false');
  if (window.LaiSound) window.LaiSound.play('open');
  const firstInput = modal.querySelector('input:not([type="hidden"]), button, a');
  if (firstInput) setTimeout(() => firstInput.focus({ preventScroll: true }), 120);
}

function closeModal(modal) {
  if (!modal || !modal.classList.contains('open') || modal.classList.contains('closing')) return;
  modal.classList.add('closing');
  if (window.LaiSound) window.LaiSound.play('close');
  modal.setAttribute('aria-hidden', 'true');
  window.setTimeout(() => {
    modal.classList.remove('open', 'closing');
    if (!document.querySelector('.modal.open')) document.body.classList.remove('modal-is-open');
  }, 190);
}

function closeDropdowns() {
  document.querySelectorAll('.dropdown-menu.open').forEach((menu) => menu.classList.remove('open'));
}

document.querySelectorAll('[data-open-modal]').forEach((button) => {
  button.addEventListener('click', () => openModal(button.dataset.openModal));
});

document.querySelectorAll('[data-close-modal]').forEach((button) => {
  button.addEventListener('click', () => {
    const modal = button.closest('.modal');
    if (modal) closeModal(modal);
  });
});

document.querySelectorAll('.modal-card').forEach((card) => {
  card.addEventListener('click', (event) => event.stopPropagation());
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    document.querySelectorAll('.modal.open').forEach(closeModal);
    closeDropdowns();
  }
});

document.querySelectorAll('[data-open-dropdown]').forEach((button) => {
  button.addEventListener('click', (event) => {
    event.stopPropagation();
    const menu = document.getElementById(button.dataset.openDropdown);
    if (!menu) return;
    const isOpen = menu.classList.contains('open');
    closeDropdowns();
    if (!isOpen) {
      menu.classList.add('open');
      if (window.LaiSound) window.LaiSound.play('dropdown');
    }
  });
});

document.querySelectorAll('.dropdown-menu').forEach((menu) => {
  menu.addEventListener('click', (event) => event.stopPropagation());
});

document.addEventListener('click', closeDropdowns);

document.querySelectorAll('form').forEach((form) => {
  form.addEventListener('submit', () => {
    if (window.LaiSound) window.LaiSound.play('submit');
  });
});

document.querySelectorAll('input, select').forEach((field) => {
  field.addEventListener('focus', () => {
    field.classList.remove('field-pop');
    void field.offsetWidth;
    field.classList.add('field-pop');
    if (window.LaiSound) window.LaiSound.play('focus');
  });
});

document.querySelectorAll('input[type="checkbox"]').forEach((box) => {
  box.addEventListener('change', () => {
    if (window.LaiSound) window.LaiSound.play(box.checked ? 'check' : 'uncheck');
  });
});

function soundForToast(toast) {
  const text = toast.textContent.toLowerCase();
  if (toast.classList.contains('error')) return 'error';
  if (text.includes('đăng xuất')) return 'logout';
  if (text.includes('đăng nhập')) return 'login';
  if (text.includes('đã duyệt')) return 'approve';
  if (text.includes('đã bỏ') || text.includes('bị bỏ')) return 'reject';
  return 'success';
}

function armToasts() {
  document.querySelectorAll('.toast').forEach((toast, index) => {
    const toastType = soundForToast(toast);
    toast.dataset.sound = toastType;

    const playToast = () => {
      if (window.LaiSound) window.LaiSound.play(toastType);
    };

    window.setTimeout(playToast, 80 + index * 90);

    const hide = () => {
      if (toast.classList.contains('leaving')) return;
      toast.classList.add('leaving');
      if (window.LaiSound) window.LaiSound.play('closeTiny');
      window.setTimeout(() => toast.remove(), 280);
    };

    toast.addEventListener('click', hide);
    toast.addEventListener('mouseenter', () => {
      if (window.LaiSound) window.LaiSound.play('toastHover');
    });
    window.setTimeout(hide, 3600 + index * 350);
  });
}

armToasts();

if (window.__OPEN_SUGGEST_MODAL__) {
  window.setTimeout(() => openModal('suggest-modal'), 80);
}


document.addEventListener('pointerdown', (event) => {
  const target = event.target.closest('button, .primary-btn, .ghost-btn, .danger-btn, .success-btn, .link-btn, .nav a, .logo, .dropdown-menu a, .toast');
  if (!target) return;
  target.classList.remove('press-pop');
  void target.offsetWidth;
  target.classList.add('press-pop');
});

document.addEventListener('animationend', (event) => {
  if (event.animationName === 'pressPop') event.target.classList.remove('press-pop');
});

function syncCheckboxVisual(box) {
  const holder = box.closest('.check-row, .check-chip');
  if (!holder) return;
  holder.classList.toggle('is-checked', box.checked);
}

function syncAllCheckboxVisuals() {
  document.querySelectorAll('input[type="checkbox"]').forEach(syncCheckboxVisual);
}

function syncRangeValue(range) {
  const root = range.closest('.range-field') || range.parentElement;
  const output = root ? root.querySelector('[data-range-value]') : null;
  if (output) output.textContent = range.value;
  const min = Number(range.min || 0);
  const max = Number(range.max || 100);
  const value = Number(range.value || 0);
  const percent = max === min ? 0 : ((value - min) / (max - min)) * 100;
  range.style.setProperty('--range-percent', `${Math.max(0, Math.min(100, percent))}%`);
}

document.querySelectorAll('input[type="checkbox"]').forEach((box) => {
  syncCheckboxVisual(box);
  box.addEventListener('change', () => syncCheckboxVisual(box));
});

document.querySelectorAll('[data-range-input]').forEach((range) => {
  syncRangeValue(range);
  range.addEventListener('input', () => {
    syncRangeValue(range);
    if (window.LaiSound && !range.dataset.soundTicking) {
      range.dataset.soundTicking = '1';
      window.LaiSound.play('focus');
      setTimeout(() => { delete range.dataset.soundTicking; }, 90);
    }
  });
});

syncAllCheckboxVisuals();

function setupInteractiveHomeToys() {
  const home = document.querySelector('.home-center');
  const layer = document.querySelector('.motion-layer');
  const hero = document.querySelector('.primary-btn.huge');
  if (!home || !layer || !hero || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  document.body.classList.add('interactive-home');
  const nodes = Array.from(layer.querySelectorAll('span'));
  if (!nodes.length) return;

  const safeTop = 84;
  const heroPadding = 42;

  function heroRectWithPadding() {
    const r = hero.getBoundingClientRect();
    return {
      left: r.left - heroPadding,
      right: r.right + heroPadding,
      top: r.top - heroPadding,
      bottom: r.bottom + heroPadding
    };
  }

  function overlapsRect(x, y, size, r) {
    return x < r.right && x + size > r.left && y < r.bottom && y + size > r.top;
  }

  function safeSpawn(x, y, size, index) {
    const w = window.innerWidth;
    const h = window.innerHeight;
    let nx = Math.max(12, Math.min(w - size - 12, x));
    let ny = Math.max(safeTop, Math.min(h - size - 12, y));
    const r = heroRectWithPadding();
    if (!overlapsRect(nx, ny, size, r)) return { x: nx, y: ny };

    const slots = [
      [24, safeTop + 22],
      [w - size - 28, safeTop + 28],
      [30, h - size - 34],
      [w - size - 36, h - size - 36],
      [Math.max(24, r.left - size - 64), Math.max(safeTop, r.top - 30)],
      [Math.min(w - size - 24, r.right + 64), Math.min(h - size - 24, r.bottom + 30)]
    ];
    for (let i = 0; i < slots.length; i += 1) {
      const [sx, sy] = slots[(index + i) % slots.length];
      if (!overlapsRect(sx, sy, size, r)) return { x: sx, y: sy };
    }
    return { x: 24 + (index * 73) % Math.max(120, w - size - 48), y: safeTop + (index * 59) % Math.max(120, h - size - safeTop - 24) };
  }

  const toys = nodes.map((el, index) => {
    const rect = el.getBoundingClientRect();
    const size = Math.max(rect.width || 44, rect.height || 44);
    const spawn = safeSpawn(rect.left, rect.top, size, index);
    el.style.animation = 'none';
    el.style.left = '0px';
    el.style.top = '0px';
    el.style.right = 'auto';
    el.style.bottom = 'auto';
    el.style.transform = `translate3d(${spawn.x}px, ${spawn.y}px, 0) rotate(${(index * 17) % 32 - 16}deg)`;
    return {
      el,
      x: spawn.x,
      y: spawn.y,
      vx: Math.cos(index * 1.91 + 0.7) * (0.42 + (index % 4) * 0.045),
      vy: Math.sin(index * 1.47 + 1.2) * (0.38 + (index % 3) * 0.05),
      size,
      rotation: (index * 17) % 32 - 16,
      vr: index % 2 ? 0.09 : -0.08,
      dragging: false,
      lastX: spawn.x,
      lastY: spawn.y,
      lastT: performance.now(),
      hitCooldown: 0,
      wanderPhase: index * 1.731 + 0.4,
      wanderSpeed: 0.012 + (index % 5) * 0.0025,
      layer: el.dataset.layer || 'main'
    };
  });

  let active = null;
  let rafId = 0;
  let lastFrame = performance.now();
  let lastHeroBumpAt = 0;
  let lastPhysicsAt = 0;
  let frameStep = 0;

  function clampToy(toy) {
    const w = window.innerWidth;
    const h = window.innerHeight;
    if (toy.x < 0) { toy.x = 0; toy.vx = Math.abs(toy.vx) * 0.68; }
    if (toy.y < safeTop) { toy.y = safeTop; toy.vy = Math.abs(toy.vy) * 0.68; }
    if (toy.x + toy.size > w) { toy.x = w - toy.size; toy.vx = -Math.abs(toy.vx) * 0.68; }
    if (toy.y + toy.size > h) { toy.y = h - toy.size; toy.vy = -Math.abs(toy.vy) * 0.68; }
  }

  function bumpHero() {
    const now = performance.now();
    if (now - lastHeroBumpAt < 420) return;
    lastHeroBumpAt = now;
    hero.classList.remove('bumped');
    void hero.offsetWidth;
    hero.classList.add('bumped');
    if (window.LaiSound) window.LaiSound.play('click');
  }

  function limitToySpeed(toy, maxSpeed = 1.85) {
    const speed = Math.hypot(toy.vx, toy.vy);
    if (speed <= maxSpeed || speed === 0) return;
    const scale = maxSpeed / speed;
    toy.vx *= scale;
    toy.vy *= scale;
  }

  function collideWithHero(toy) {
    const r = hero.getBoundingClientRect();
    const cx = toy.x + toy.size / 2;
    const cy = toy.y + toy.size / 2;
    const radius = Math.max(18, toy.size * 0.5);
    let nx = 0;
    let ny = 0;
    let push = 0;

    const insideX = cx >= r.left && cx <= r.right;
    const insideY = cy >= r.top && cy <= r.bottom;

    if (insideX && insideY) {
      const distances = [
        { n: [-1, 0], d: cx - r.left },
        { n: [1, 0], d: r.right - cx },
        { n: [0, -1], d: cy - r.top },
        { n: [0, 1], d: r.bottom - cy }
      ].sort((a, b) => a.d - b.d);
      nx = distances[0].n[0];
      ny = distances[0].n[1];
      push = Math.min(80, radius + distances[0].d + 8);
    } else {
      const nearestX = Math.max(r.left, Math.min(cx, r.right));
      const nearestY = Math.max(r.top, Math.min(cy, r.bottom));
      const dx = cx - nearestX;
      const dy = cy - nearestY;
      const d2 = dx * dx + dy * dy;
      if (d2 >= radius * radius) return false;
      const d = Math.sqrt(d2) || 1;
      nx = dx / d;
      ny = dy / d;
      push = Math.min(56, radius - d + 8);
    }

    toy.x += nx * push;
    toy.y += ny * push;
    clampToy(toy);

    const outwardSpeed = Math.max(1.05, Math.min(2.7, Math.hypot(toy.vx, toy.vy) * 0.75));
    const dot = toy.vx * nx + toy.vy * ny;
    if (dot < 0.2) {
      toy.vx -= 1.35 * dot * nx;
      toy.vy -= 1.35 * dot * ny;
      toy.vx += nx * outwardSpeed;
      toy.vy += ny * outwardSpeed;
    } else {
      toy.vx += nx * 0.22;
      toy.vy += ny * 0.22;
    }
    toy.vr += nx * 0.18 + ny * 0.08;
    limitToySpeed(toy);

    if (toy.hitCooldown <= 0 && Math.hypot(toy.vx, toy.vy) > 0.7) {
      toy.hitCooldown = 26;
      bumpHero();
    }
    return true;
  }

  function separateFromHeroUntilClear(toy) {
    for (let i = 0; i < 4; i += 1) {
      if (!collideWithHero(toy)) break;
    }
  }

  function collideToys(a, b) {
    if (a.layer !== b.layer) return;
    const ax = a.x + a.size / 2;
    const ay = a.y + a.size / 2;
    const bx = b.x + b.size / 2;
    const by = b.y + b.size / 2;
    const dx = bx - ax;
    const dy = by - ay;
    const minDist = (a.size + b.size) * 0.46;
    const dist2 = dx * dx + dy * dy;
    if (dist2 <= 0 || dist2 >= minDist * minDist) return;
    const dist = Math.sqrt(dist2);
    const nx = dx / dist;
    const ny = dy / dist;
    const overlap = Math.min(28, (minDist - dist) / 2 + 1.5);
    if (!a.dragging) { a.x -= nx * overlap; a.y -= ny * overlap; }
    if (!b.dragging) { b.x += nx * overlap; b.y += ny * overlap; }
    const av = a.vx * nx + a.vy * ny;
    const bv = b.vx * nx + b.vy * ny;
    const impulse = (av - bv) * 0.64;
    if (!a.dragging) { a.vx -= impulse * nx; a.vy -= impulse * ny; limitToySpeed(a); }
    if (!b.dragging) { b.vx += impulse * nx; b.vy += impulse * ny; limitToySpeed(b); }
  }

  function render(toy) {
    toy.el.style.transform = `translate3d(${toy.x}px, ${toy.y}px, 0) rotate(${toy.rotation}deg)`;
  }

  function findToyAt(clientX, clientY) {
    let best = null;
    let bestDist = Infinity;
    toys.forEach((toy) => {
      const cx = toy.x + toy.size / 2;
      const cy = toy.y + toy.size / 2;
      const dist = Math.hypot(clientX - cx, clientY - cy);
      const hitRadius = Math.max(34, toy.size * 0.82);
      if (dist < hitRadius && dist < bestDist) {
        best = toy;
        bestDist = dist;
      }
    });
    return best;
  }

  function canStartToyDrag(event) {
    if (document.body.classList.contains('modal-is-open')) return false;
    if (event.target.closest('button, a, input, select, textarea, label, .modal, .toast, .dropdown-menu')) return false;
    return true;
  }

  function startDrag(toy, event) {
    active = toy;
    toy.dragging = true;
    toy.el.classList.add('is-dragging');
    try { toy.el.setPointerCapture(event.pointerId); } catch (_) {}
    toy.lastX = event.clientX;
    toy.lastY = event.clientY;
    toy.lastT = performance.now();
    toy.vx = 0;
    toy.vy = 0;
    if (window.LaiSound) window.LaiSound.play('check');
  }

  function moveActive(event) {
    if (!active || !active.dragging) return;
    const toy = active;
    const now = performance.now();
    const dt = Math.max(8, now - toy.lastT);
    const dx = event.clientX - toy.lastX;
    const dy = event.clientY - toy.lastY;
    toy.x += dx;
    toy.y += dy;
    toy.vx = dx / dt * 16.67;
    toy.vy = dy / dt * 16.67;
    toy.vr = Math.max(-2.1, Math.min(2.1, toy.vx * 0.04));
    toy.lastX = event.clientX;
    toy.lastY = event.clientY;
    toy.lastT = now;
    clampToy(toy);
    separateFromHeroUntilClear(toy);
    render(toy);
  }

  function releaseActive(event) {
    if (!active) return;
    const toy = active;
    toy.dragging = false;
    toy.el.classList.remove('is-dragging');
    try { toy.el.releasePointerCapture(event.pointerId); } catch (_) {}
    active = null;
    toy.vx *= 1.12;
    toy.vy *= 1.12;
    limitToySpeed(toy, 2.35);
    separateFromHeroUntilClear(toy);
    if (window.LaiSound) window.LaiSound.play('uncheck');
  }

  function tick(now) {
    if (document.hidden) {
      lastFrame = now;
      rafId = requestAnimationFrame(tick);
      return;
    }
    if (now - lastPhysicsAt < 24) {
      rafId = requestAnimationFrame(tick);
      return;
    }
    lastPhysicsAt = now;
    const dt = Math.min(28, now - lastFrame) / 16.67;
    lastFrame = now;
    const modalOpen = document.body.classList.contains('modal-is-open');
    if (!modalOpen) {
      frameStep = (frameStep + 1) % 3;
      toys.forEach((toy) => {
        if (toy.hitCooldown > 0) toy.hitCooldown -= 1;
        if (!toy.dragging) {
          const t = now * toy.wanderSpeed + toy.wanderPhase;
          toy.vx += Math.cos(t) * 0.010 * dt;
          toy.vy += Math.sin(t * 1.13) * 0.010 * dt;
          toy.x += toy.vx * dt;
          toy.y += toy.vy * dt;
          toy.rotation += toy.vr * dt;
          toy.vx *= 0.985;
          toy.vy *= 0.985;
          toy.vr *= 0.992;
          limitToySpeed(toy);
          clampToy(toy);
          if (frameStep !== 1 || toy.hitCooldown <= 0) separateFromHeroUntilClear(toy);
        }
      });
      if (frameStep === 0) {
        for (let i = 0; i < toys.length; i += 1) {
          for (let j = i + 1; j < toys.length; j += 1) collideToys(toys[i], toys[j]);
        }
      }
      toys.forEach(render);
    }
    rafId = requestAnimationFrame(tick);
  }

  toys.forEach((toy) => {
    toy.el.addEventListener('pointerdown', (event) => {
      event.preventDefault();
      startDrag(toy, event);
    });
  });

  document.addEventListener('pointerdown', (event) => {
    if (!canStartToyDrag(event)) return;
    const toy = findToyAt(event.clientX, event.clientY);
    if (!toy) return;
    event.preventDefault();
    startDrag(toy, event);
  }, true);

  document.addEventListener('pointermove', (event) => moveActive(event), true);
  document.addEventListener('pointerup', (event) => releaseActive(event), true);
  document.addEventListener('pointercancel', (event) => releaseActive(event), true);

  window.addEventListener('resize', () => {
    toys.forEach((toy, index) => {
      clampToy(toy);
      separateFromHeroUntilClear(toy);
      const r = heroRectWithPadding();
      if (overlapsRect(toy.x, toy.y, toy.size, r)) {
        const spawn = safeSpawn(toy.x, toy.y, toy.size, index);
        toy.x = spawn.x;
        toy.y = spawn.y;
      }
      render(toy);
    });
  });
  rafId = requestAnimationFrame(tick);
  window.addEventListener('beforeunload', () => cancelAnimationFrame(rafId));
}

window.addEventListener('load', () => window.setTimeout(setupInteractiveHomeToys, 120));

function ensureConfirmModal() {
  let modal = document.getElementById('confirm-action-modal');
  if (modal) return modal;
  modal = document.createElement('div');
  modal.className = 'modal confirm-modal';
  modal.id = 'confirm-action-modal';
  modal.setAttribute('aria-hidden', 'true');
  modal.innerHTML = `
    <div class="modal-backdrop" data-close-modal></div>
    <div class="modal-card confirm-card" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
      <button class="modal-x" type="button" data-close-modal aria-label="Đóng">×</button>
      <h1 id="confirm-title">Xác nhận</h1>
      <p class="confirm-message">Bạn chắc chứ?</p>
      <div class="confirm-actions">
        <button class="ghost-btn" type="button" data-confirm-cancel>Hủy</button>
        <button class="danger-btn" type="button" data-confirm-ok>Gỡ</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
  modal.querySelectorAll('[data-close-modal], [data-confirm-cancel]').forEach((el) => {
    el.addEventListener('click', () => closeModal(modal));
  });
  modal.querySelector('.modal-card').addEventListener('click', (event) => event.stopPropagation());
  return modal;
}

let pendingConfirmForm = null;

document.addEventListener('submit', (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  const message = form.dataset.confirm;
  if (!message || form.dataset.confirmed === '1') return;
  event.preventDefault();
  event.stopPropagation();
  pendingConfirmForm = form;
  const modal = ensureConfirmModal();
  const title = form.dataset.confirmTitle || 'Xác nhận';
  modal.querySelector('#confirm-title').textContent = title;
  modal.querySelector('.confirm-message').textContent = message;
  openModal('confirm-action-modal');
  const okButton = modal.querySelector('[data-confirm-ok]');
  okButton.onclick = () => {
    if (!pendingConfirmForm) return;
    pendingConfirmForm.dataset.confirmed = '1';
    if (window.LaiSound) window.LaiSound.play('reject');
    closeModal(modal);
    pendingConfirmForm.requestSubmit ? pendingConfirmForm.requestSubmit() : pendingConfirmForm.submit();
    pendingConfirmForm = null;
  };
}, true);
