// =====================================================
// СОСТОЯНИЕ
// =====================================================
const state = {
  resources: {},      // {name: count}
  tasks: [],          // [{id, name, duration, deps: [], resources: {}}]
  lastResult: null,
  lastPayload: null,
  currentDepsTaskIndex: null,
};

const INITIAL_RESOURCE_COLUMNS = 5;
let resourceColumns = []; // [{name: '', count: ''}]
let ganttChart = null;    // Экземпляр диаграммы Ганта

// =====================================================
// УТИЛИТЫ
// =====================================================
function toast(msg, isError = false) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.background = isError ? '#e74c3c' : '#2c3e50';
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3000);
}

async function api(url, opts = {}) {
  const res = await fetch(url, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    let detail = await res.text();
    try { detail = JSON.parse(detail).detail || detail; } catch (e) {}
    if (typeof detail === 'object' && detail && detail.errors) {
      detail = detail.errors.join('\n');
    }
    throw new Error(detail);
  }
  return res;
}

// =====================================================
// ТАБЛИЦА РЕСУРСОВ
// =====================================================
function initResourceColumns() {
  if (resourceColumns.length === 0) {
    for (let i = 0; i < INITIAL_RESOURCE_COLUMNS; i++) {
      resourceColumns.push({ name: '', count: '' });
    }
  }
}

function renderResourcesTable() {
  initResourceColumns();
  const names = document.getElementById('resources-names');
  const counts = document.getElementById('resources-counts');

  names.innerHTML = '<td class="cell-label">Название</td>';
  counts.innerHTML = '<td class="cell-label">Количество</td>';

  resourceColumns.forEach((col, i) => {
    const tdName = document.createElement('td');
    const inputName = document.createElement('input');
    inputName.value = col.name;
    inputName.placeholder = 'Имя';
    inputName.oninput = (e) => {
      resourceColumns[i].name = e.target.value;
      onResourceColumnChange(i);
    };
    tdName.appendChild(inputName);
    names.appendChild(tdName);

    const tdCount = document.createElement('td');
    const inputCount = document.createElement('input');
    inputCount.type = 'number';
    inputCount.min = '0';
    inputCount.value = col.count;
    inputCount.placeholder = '0';
    inputCount.oninput = (e) => {
      resourceColumns[i].count = e.target.value;
      onResourceColumnChange(i);
    };
    tdCount.appendChild(inputCount);
    counts.appendChild(tdCount);
  });
}

function onResourceColumnChange(index) {
  if (index === resourceColumns.length - 1) {
    const last = resourceColumns[index];
    const hasName = (last.name || '').trim().length > 0;
    const hasCount = (last.count || '').trim().length > 0;
    if (hasName || hasCount) {
      const wrap = document.querySelector('#resources-table').parentElement;
      const savedScroll = wrap.scrollLeft;

      resourceColumns.push({ name: '', count: '' });
      renderResourcesTable();

      wrap.scrollLeft = savedScroll;
    }
  }
}

function saveResources() {
  const result = {};
  for (const col of resourceColumns) {
    const name = (col.name || '').trim();
    const count = parseInt(col.count, 10);
    if (name && count > 0) {
      result[name] = count;
    }
  }
  if (Object.keys(result).length === 0) {
    toast('Добавьте хотя бы один ресурс с количеством > 0', true);
    return;
  }
  state.resources = result;
  renderTasksTable();
  toast(`✅ Сохранено ресурсов: ${Object.keys(result).length}`);
}

// =====================================================
// ТАБЛИЦА ЗАДАЧ
// =====================================================
function renderTasksTable() {
  const header = document.getElementById('tasks-header');
  const body = document.getElementById('tasks-body');

  const resNames = Object.keys(state.resources);

  let html = `
    <th>ID</th>
    <th>Название</th>
    <th>Длит.</th>
    <th>Зависимости</th>
  `;
  resNames.forEach((rn) => {
    html += `<th>${rn}</th>`;
  });
  html += '<th></th>';
  header.innerHTML = html;

  body.innerHTML = '';

  state.tasks.forEach((task, i) => {
    const tr = document.createElement('tr');

    const tdId = document.createElement('td');
    tdId.className = 'row-id';
    tdId.textContent = task.id;
    tr.appendChild(tdId);

    const tdName = document.createElement('td');
    const inputName = document.createElement('input');
    inputName.value = task.name;
    inputName.oninput = (e) => { task.name = e.target.value; };
    tdName.appendChild(inputName);
    tr.appendChild(tdName);

    const tdDur = document.createElement('td');
    const inputDur = document.createElement('input');
    inputDur.type = 'number';
    inputDur.min = '1';
    inputDur.value = task.duration;
    inputDur.oninput = (e) => {
      task.duration = parseInt(e.target.value, 10) || 1;
    };
    tdDur.appendChild(inputDur);
    tr.appendChild(tdDur);

    const tdDeps = document.createElement('td');
    tdDeps.className = 'deps-cell';
    const depsTrigger = document.createElement('div');
    depsTrigger.className = 'deps-trigger';
    const depsText = task.deps && task.deps.length
      ? task.deps.join(', ')
      : '—';
    depsTrigger.innerHTML = `
      <span class="value">${depsText}</span>
      <span class="arrow">▼</span>
    `;
    depsTrigger.onclick = () => openDepsModal(i);
    tdDeps.appendChild(depsTrigger);
    tr.appendChild(tdDeps);

    resNames.forEach((rn) => {
      const tdRes = document.createElement('td');
      const inputRes = document.createElement('input');
      inputRes.type = 'number';
      inputRes.min = '0';
      inputRes.value = task.resources[rn] || 0;
      inputRes.oninput = (e) => {
        const val = parseInt(e.target.value, 10) || 0;
        if (val > 0) task.resources[rn] = val;
        else delete task.resources[rn];
      };
      tdRes.appendChild(inputRes);
      tr.appendChild(tdRes);
    });

    const tdDel = document.createElement('td');
    const delBtn = document.createElement('button');
    delBtn.className = 'delete-btn';
    delBtn.textContent = '✕';
    delBtn.onclick = () => removeTaskRow(i);
    tdDel.appendChild(delBtn);
    tr.appendChild(tdDel);

    body.appendChild(tr);
  });

  // Пустая строка
  const emptyTr = document.createElement('tr');
  emptyTr.className = 'empty-row';

  const emptyId = document.createElement('td');
  emptyId.className = 'row-id';
  emptyTr.appendChild(emptyId);

  const emptyName = document.createElement('td');
  const emptyNameInput = document.createElement('input');
  emptyNameInput.placeholder = 'Новая задача…';
  emptyNameInput.onkeydown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      createTaskFromEmptyRow(emptyNameInput.value);
    }
  };
  emptyNameInput.onblur = () => {
    if (emptyNameInput.value.trim()) {
      createTaskFromEmptyRow(emptyNameInput.value);
    }
  };
  emptyName.appendChild(emptyNameInput);
  emptyTr.appendChild(emptyName);

  const emptyDur = document.createElement('td');
  const emptyDurInput = document.createElement('input');
  emptyDurInput.type = 'number';
  emptyDurInput.min = '1';
  emptyDurInput.placeholder = '3';
  emptyDur.appendChild(emptyDurInput);
  emptyTr.appendChild(emptyDur);

  const emptyDeps = document.createElement('td');
  emptyDeps.className = 'deps-cell';
  emptyDeps.innerHTML = '<span style="color:#b0b0b0;padding:8px 10px;display:block">—</span>';
  emptyTr.appendChild(emptyDeps);

  resNames.forEach(() => {
    const tdRes = document.createElement('td');
    const inputRes = document.createElement('input');
    inputRes.type = 'number';
    inputRes.min = '0';
    inputRes.placeholder = '0';
    tdRes.appendChild(inputRes);
    emptyTr.appendChild(tdRes);
  });

  const emptyDel = document.createElement('td');
  emptyTr.appendChild(emptyDel);

  body.appendChild(emptyTr);
}

function createTaskFromEmptyRow(name) {
  const trimmed = (name || '').trim();
  if (!trimmed) return;

  const id = state.tasks.length
    ? Math.max(...state.tasks.map((t) => t.id)) + 1
    : 1;

  state.tasks.push({
    id,
    name: trimmed,
    duration: 3,
    deps: [],
    resources: {},
  });
  renderTasksTable();
}

function removeTaskRow(i) {
  const removedId = state.tasks[i].id;
  state.tasks.splice(i, 1);

  state.tasks.forEach((t) => {
    t.deps = (t.deps || []).filter((d) => d !== removedId);
  });

  renderTasksTable();
}

// =====================================================
// МОДАЛКА ЗАВИСИМОСТЕЙ
// =====================================================
function openDepsModal(taskIndex) {
  state.currentDepsTaskIndex = taskIndex;
  const task = state.tasks[taskIndex];
  document.getElementById('deps-task-id').textContent = task.id;

  const list = document.getElementById('deps-list');
  list.innerHTML = '';

  const candidates = state.tasks
    .map((t, i) => ({ t, i }))
    .filter(({ t, i }) => i !== taskIndex && (t.name || '').trim());

  if (candidates.length === 0) {
    list.innerHTML = '<em>Нет других задач для зависимостей</em>';
  } else {
    candidates.forEach(({ t }) => {
      const lbl = document.createElement('label');
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.value = t.id;
      cb.checked = (task.deps || []).includes(t.id);
      lbl.appendChild(cb);
      lbl.appendChild(document.createTextNode(`ID ${t.id}: ${t.name}`));
      list.appendChild(lbl);
    });
  }

  document.getElementById('deps-modal').style.display = 'flex';
}

function applyDeps() {
  const task = state.tasks[state.currentDepsTaskIndex];
  const checked = Array.from(
    document.querySelectorAll('#deps-list input[type="checkbox"]:checked')
  ).map((cb) => parseInt(cb.value, 10));
  task.deps = checked;
  closeDeps();
  renderTasksTable();
}

function closeDeps() {
  document.getElementById('deps-modal').style.display = 'none';
  state.currentDepsTaskIndex = null;
}

// =====================================================
// СБОРКА PAYLOAD
// =====================================================
function buildPayload() {
  const deps = {};
  state.tasks.forEach((t) => {
    if (t.deps && t.deps.length) deps[t.id] = t.deps;
  });
  return {
    name: 'Мой проект',
    resource_limits: state.resources,
    tasks: state.tasks.map((t) => ({
      id: t.id,
      name: t.name,
      duration: t.duration || 1,
      resources: t.resources || {},
    })),
    dependencies: deps,
  };
}

function applyPayload(p) {
  state.resources = p.resource_limits || {};

  resourceColumns = Object.entries(state.resources).map(([name, count]) => ({
    name,
    count: String(count),
  }));
  while (resourceColumns.length < INITIAL_RESOURCE_COLUMNS) {
    resourceColumns.push({ name: '', count: '' });
  }
  renderResourcesTable();

  const deps = p.dependencies || {};
  state.tasks = (p.tasks || []).map((t) => ({
    id: t.id,
    name: t.name,
    duration: t.duration,
    resources: Object.assign({}, t.resources || {}),
    deps: (deps[t.id] || []).slice(),
  }));
  renderTasksTable();
}

// =====================================================
// ЗАПУСК ПЛАНИРОВАНИЯ
// =====================================================
async function runScheduler() {
  if (state.tasks.length === 0) {
    toast('Добавьте хотя бы одну задачу', true);
    return;
  }
  if (Object.keys(state.resources).length === 0) {
    toast('Сохраните ресурсы (кнопка «💾 Сохранить»)', true);
    return;
  }

  const payload = buildPayload();
  state.lastPayload = payload;
  const method = document.getElementById('method').value;
  const rule = document.getElementById('rule').value;

  toast('⏳ Планирование...');
  try {
    const res = await api(
      `/api/schedule?method=${method}&rule=${rule}`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
    const data = await res.json();
    state.lastResult = data;
    showResults(data);
    toast(`✅ Готово: ${data.makespan} дней`);
  } catch (e) {
    toast('Ошибка: ' + e.message, true);
  }
}

function showResults(data) {
  document.getElementById('results-card').style.display = 'block';
  document.getElementById('makespan').textContent = data.makespan;
  const cacheBust = '?t=' + Date.now();

  document.getElementById('dashboard-img').src = data.dashboard_url + cacheBust;
  document.getElementById('resources-img').src = data.resources_url + cacheBust;

  // ===== Отрисовка интерактивного Ганта =====
  const tasksForGantt = [];
  const payload = state.lastPayload;

  // Словарь имен задач по ID
  const taskNames = {};
  payload.tasks.forEach(t => {
    taskNames[t.id] = t.name;
  });

  // Начальная дата для визуализации (не влияет на сам расчет, просто для сетки)
  const projectStart = new Date();
  projectStart.setHours(0, 0, 0, 0);

  for (const [taskId, dates] of Object.entries(data.schedule)) {
    const start = dates[0];
    const end = dates[1];

    const startDate = new Date(projectStart);
    startDate.setDate(startDate.getDate() + start);

    // end исключительно, поэтому для библиотеки (включающую дату) вычитаем 1 день
    const endDate = new Date(projectStart);
    endDate.setDate(endDate.getDate() + end - 1);

    const formatDate = (d) => {
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      return `${yyyy}-${mm}-${dd}`;
    };

    tasksForGantt.push({
      id: String(taskId),
      name: `ID ${taskId}: ${taskNames[taskId] || 'Задача'}`,
      start: formatDate(startDate),
      end: formatDate(endDate),
      progress: 100,
      dependencies: (payload.dependencies[taskId] || []).join(', ')
    });
  }

  // Очищаем старый график и создаем новый
  const ganttSvg = document.getElementById('gantt');
  ganttSvg.innerHTML = ''; // Очищаем SVG

  if (tasksForGantt.length > 0) {
    ganttChart = new Gantt("#gantt", tasksForGantt, {
      view_mode: 'Day', // Можно поменять на 'Week', 'Month'
      language: 'ru',
      custom_popup_html: function(task) {
        return `
          <div style="padding: 5px;">
            <strong>${task.name}</strong><br>
            Начало: ${task.start}<br>
            Конец: ${task.end}
          </div>
        `;
      }
    });
  }
}

// =====================================================
// ДЕМО / JSON / ЭКСПОРТ
// =====================================================
async function loadDemo() {
  try {
    const res = await api('/api/demo', { method: 'POST' });
    const data = await res.json();
    applyPayload(data);
    toast('🎲 Демо загружено');
  } catch (e) {
    toast('Ошибка: ' + e.message, true);
  }
}

async function exportJson() {
  if (state.tasks.length === 0) {
    toast('Нет данных', true);
    return;
  }
  const payload = buildPayload();
  try {
    const res = await api('/api/project/export', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'project.json';
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    toast('Ошибка: ' + e.message, true);
  }
}

document.getElementById('import-file').addEventListener('change', async (ev) => {
  const file = ev.target.files[0];
  if (!file) return;
  try {
    const text = await file.text();
    const json = JSON.parse(text);
    const res = await api('/api/project/import', {
      method: 'POST',
      body: JSON.stringify(json),
    });
    const data = await res.json();
    applyPayload(data);
    toast('✅ Проект загружен');
  } catch (e) {
    toast('Ошибка: ' + e.message, true);
  }
});

async function exportResourceTable(fmt) {
  if (!state.lastResult) {
    toast('Сначала запустите планирование', true);
    return;
  }
  const startDate = document.getElementById('start-date').value || null;
  try {
    const res = await api(
      '/api/export/resource-table?fmt=' + fmt +
      (startDate ? '&start_date=' + startDate : ''),
      {
        method: 'POST',
        body: JSON.stringify({
          payload: state.lastPayload,
          schedule: state.lastResult.schedule,
        }),
      }
    );
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'resource_table.' + (fmt === 'csv' ? 'csv' : 'txt');
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    toast('Ошибка: ' + e.message, true);
  }
}

// =====================================================
// АВТОРИЗАЦИЯ
// =====================================================
document.getElementById('btn-login').onclick = () =>
  document.getElementById('login-modal').style.display = 'flex';

document.getElementById('btn-logout').onclick = async () => {
  await api('/api/auth/logout', { method: 'POST' });
  updateAuthUI(null);
  toast('Вы вышли');
};

function closeLogin() {
  document.getElementById('login-modal').style.display = 'none';
}

async function doLogin() {
  const username = document.getElementById('login-username').value;
  const password = document.getElementById('login-password').value;
  try {
    const res = await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    updateAuthUI(data);
    closeLogin();
    toast('👤 Добро пожаловать, ' + data.username);
  } catch (e) {
    toast('Ошибка: ' + e.message, true);
  }
}

async function doRegister() {
  const username = document.getElementById('login-username').value;
  const password = document.getElementById('login-password').value;
  try {
    const res = await api('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    updateAuthUI(data);
    closeLogin();
    toast('✅ Зарегистрирован: ' + data.username);
  } catch (e) {
    toast('Ошибка: ' + e.message, true);
  }
}

function updateAuthUI(user) {
  const info = document.getElementById('user-info');
  const login = document.getElementById('btn-login');
  const logout = document.getElementById('btn-logout');
  if (user) {
    info.textContent = '👤 ' + user.username;
    login.style.display = 'none';
    logout.style.display = 'inline-block';
  } else {
    info.textContent = 'Не вошёл';
    login.style.display = 'inline-block';
    logout.style.display = 'none';
  }
}

// =====================================================
// ИНИЦИАЛИЗАЦИЯ
// =====================================================
initResourceColumns();
renderResourcesTable();
renderTasksTable();