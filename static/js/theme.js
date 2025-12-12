(function(){
  const key = 'theme:dark';
  const toggle = document.getElementById('themeToggle');
  const apply = () => {
    const dark = localStorage.getItem(key) === '1';
    document.body.classList.toggle('dark', dark);
    if (toggle) toggle.innerHTML = dark ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
  };
  document.addEventListener('DOMContentLoaded', function(){
    apply();
    if (toggle) toggle.addEventListener('click', function(){
      const next = localStorage.getItem(key) === '1' ? '0' : '1';
      localStorage.setItem(key, next);
      apply();
    });
  });
})();