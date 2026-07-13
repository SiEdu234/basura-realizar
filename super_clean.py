import re
import os

base_path = r'c:\Users\simed\Downloads\AdminLTE-3.2.0-rc\proyectoDWA\templates\base.html'
with open(base_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Strip out the entire sidebar-menu and replace it with a clean one
start_menu = content.find('<nav class="mt-2">')
end_menu = content.find('<!-- /.sidebar-menu -->')

if start_menu != -1 and end_menu != -1:
    clean_menu = """<nav class="mt-2">
        <ul class="nav nav-pills nav-sidebar flex-column" data-widget="treeview" role="menu" data-accordion="false">
          
          {% if user.is_staff %}
          <li class="nav-header">ADMINISTRACIÓN</li>
          <li class="nav-item">
            <a href="{% url 'home' %}" class="nav-link {% block nav_admin %}{% endblock %}">
              <i class="nav-icon fas fa-tachometer-alt"></i>
              <p>Panel Estadísticas</p>
            </a>
          </li>
          {% endif %}
          
          <li class="nav-header">ESTUDIO</li>
          <li class="nav-item">
            <a href="{% url 'study:dashboard' %}" class="nav-link {% block nav_dashboard %}{% endblock %}">
              <i class="nav-icon fas fa-book"></i>
              <p>Materias / Dashboard</p>
            </a>
          </li>

        </ul>
      </nav>
      """
    content = content[:start_menu] + clean_menu + content[end_menu:]

# 2. Remove demo.js
content = content.replace('<script src="{% static \'dist/js/demo.js\' %}"></script>', '')
# Remove dashboard.js if it causes issues, but we might need it? No, dashboard.js is for the fake charts. Let's remove it just in case.
content = content.replace('<script src="{% static \'dist/js/pages/dashboard.js\' %}"></script>', '')

with open(base_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Cleaned base.html")
