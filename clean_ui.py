import re
import os

with open(r'c:\Users\simed\Downloads\AdminLTE-3.2.0-rc\proyectoDWA\templates\base.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Navbar cleanup
# Replace messages and notifications dropdowns with a Profile dropdown
navbar_profile = """
      <!-- User Profile Dropdown Menu -->
      {% if user.is_authenticated %}
      <li class="nav-item dropdown">
        <a class="nav-link" data-toggle="dropdown" href="#">
          <i class="far fa-user"></i> {{ user.username }}
        </a>
        <div class="dropdown-menu dropdown-menu-lg dropdown-menu-right">
          <span class="dropdown-item dropdown-header">Perfil de Usuario</span>
          <div class="dropdown-divider"></div>
          <a href="#" class="dropdown-item">
            <i class="fas fa-id-badge mr-2"></i> {% if user.is_staff %}Administrador{% else %}Estudiante{% endif %}
          </a>
          <div class="dropdown-divider"></div>
          <form action="{% url 'logout' %}" method="post" class="d-inline">
            {% csrf_token %}
            <button type="submit" class="dropdown-item dropdown-footer text-danger"><i class="fas fa-sign-out-alt"></i> Cerrar Sesión</button>
          </form>
        </div>
      </li>
      {% else %}
      <li class="nav-item">
        <a class="nav-link" href="{% url 'login' %}">
          <i class="fas fa-sign-in-alt"></i> Iniciar Sesión
        </a>
      </li>
      {% endif %}
      <li class="nav-item">
        <a class="nav-link" data-widget="fullscreen" href="#" role="button">
          <i class="fas fa-expand-arrows-alt"></i>
        </a>
      </li>
"""
# Find the start of Messages dropdown
msg_start = content.find('<!-- Messages Dropdown Menu -->')
# Find the fullscreen button (which we want to keep, or replace up to it)
fullscreen_start = content.find('<li class="nav-item">\n        <a class="nav-link" data-widget="fullscreen"')
if msg_start != -1 and fullscreen_start != -1:
    content = content[:msg_start] + navbar_profile + content[fullscreen_start + content[fullscreen_start:].find('</li>') + 5:]

# 2. Sidebar cleanup
# Find the end of Dashboard/Materias section
examples_header = content.find('<li class="nav-header">EXAMPLES</li>')
if examples_header != -1:
    # We want to comment everything from EXAMPLES down to the end of the sidebar ul
    # The end of the sidebar ul is right before <!-- /.sidebar-menu -->
    end_sidebar = content.find('</ul>\n      </nav>\n      <!-- /.sidebar-menu -->')
    if end_sidebar != -1:
        # Wrap in HTML comment
        commented_section = '<!-- [VISTAS DE EJEMPLO DE ADMINLTE OCULTAS A PETICION DEL USUARIO]\n' + content[examples_header:end_sidebar].replace('<!--', '<! --').replace('-->', '-- >') + '\n-->'
        content = content[:examples_header] + commented_section + content[end_sidebar:]

# 3. Add Dashboard (Stats) link for staff only
# Right before ESTUDIEN VAGOS
dashboard_link = """
          {% if user.is_staff %}
          <li class="nav-item">
            <a href="{% url 'home' %}" class="nav-link {% block nav_admin %}{% endblock %}">
              <i class="nav-icon fas fa-tachometer-alt"></i>
              <p>Panel Estadísticas</p>
            </a>
          </li>
          {% endif %}
"""
estudien_vagos = content.find('<li class="nav-header">ESTUDIEN VAGOS</li>')
if estudien_vagos != -1:
    content = content[:estudien_vagos] + dashboard_link + content[estudien_vagos:]

# 4. Hide "Nueva materia" in dashboard.html for non-staff
with open(r'c:\Users\simed\Downloads\AdminLTE-3.2.0-rc\proyectoDWA\study\templates\study\dashboard.html', 'r', encoding='utf-8') as f:
    dash_html = f.read()
dash_html = dash_html.replace('<button class="btn btn-primary" data-toggle="modal" data-target="#createSubjectModal">', 
                              '{% if user.is_staff %}<button class="btn btn-primary" data-toggle="modal" data-target="#createSubjectModal">')
dash_html = dash_html.replace('</button>\n  </div>\n</div>\n\n<div class="row">',
                              '</button>{% endif %}\n  </div>\n</div>\n\n<div class="row">')

with open(r'c:\Users\simed\Downloads\AdminLTE-3.2.0-rc\proyectoDWA\study\templates\study\dashboard.html', 'w', encoding='utf-8') as f:
    f.write(dash_html)

# 5. Hide upload form in subject_detail.html for non-staff
with open(r'c:\Users\simed\Downloads\AdminLTE-3.2.0-rc\proyectoDWA\study\templates\study\subject_detail.html', 'r', encoding='utf-8') as f:
    subj_html = f.read()

# The upload form is in a card: <div class="card card-primary"> ... <h3 class="card-title">Subir Archivo</h3>
upload_card_start = subj_html.find('<div class="card card-primary">')
if upload_card_start != -1:
    upload_card_end = subj_html.find('<!-- /.card -->', upload_card_start)
    if upload_card_end != -1:
        # Actually it's just `</div>` after `</form></div>`.
        # Let's just wrap the whole column if possible, or just string replace manually
        pass

# A simpler way to hide upload form:
subj_html = subj_html.replace('<div class="col-md-4">', '<div class="col-md-4">\n      {% if user.is_staff %}')
# The right col ends before <script> or {% endblock %}
subj_html = subj_html.replace('</section>\n</div>', '{% endif %}\n  </section>\n</div>') # This might be fragile, let's use regex
subj_html = re.sub(r'(<div class="card card-primary">.*?<!-- /\.card -->\n)', r'{% if user.is_staff %}\n\1{% endif %}\n', subj_html, flags=re.DOTALL)


with open(r'c:\Users\simed\Downloads\AdminLTE-3.2.0-rc\proyectoDWA\study\templates\study\subject_detail.html', 'w', encoding='utf-8') as f:
    f.write(subj_html)

with open(r'c:\Users\simed\Downloads\AdminLTE-3.2.0-rc\proyectoDWA\templates\base.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
