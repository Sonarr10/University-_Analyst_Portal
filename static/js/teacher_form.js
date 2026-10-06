(() => {
  const department = document.getElementById('id_department');
  const choices = document.getElementById('id_subjects_can_teach');
  const count = document.getElementById('teacher-subject-count');
  const data = document.getElementById('teacher-subject-data');
  if (!department || !choices || !count || !data) return;

  const subjectsByDepartment = JSON.parse(data.textContent);
  const limit = 3;

  function selectedInputs() {
    return [...choices.querySelectorAll('input[type="checkbox"]:checked')];
  }

  function updateCount() {
    const selected = selectedInputs().length;
    count.textContent = `Selected: ${selected} / ${limit}`;
    choices.querySelectorAll('input[type="checkbox"]:not(:checked)').forEach(input => {
      input.disabled = selected >= limit;
    });
  }

  function renderSubjects() {
    const selected = new Set(selectedInputs().map(input => input.value));
    const subjects = subjectsByDepartment[department.value] || [];
    choices.replaceChildren();

    if (!department.value) {
      choices.textContent = 'Choose a department to see its subjects.';
    } else if (!subjects.length) {
      choices.textContent = 'No subjects are set up for this department yet.';
    } else {
      subjects.forEach(subject => {
        const wrapper = document.createElement('div');
        const label = document.createElement('label');
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.name = 'subjects_can_teach';
        input.value = subject.id;
        input.checked = selected.has(subject.id);
        label.append(input, document.createTextNode(subject.label));
        wrapper.append(label);
        choices.append(wrapper);
      });
    }
    updateCount();
  }

  choices.addEventListener('change', event => {
    if (event.target.matches('input[type="checkbox"]') && selectedInputs().length > limit) {
      event.target.checked = false;
    }
    updateCount();
  });
  department.addEventListener('change', renderSubjects);
  renderSubjects();
})();
