import re
import os

with open(r'c:\Users\simed\Downloads\AdminLTE-3.2.0-rc\proyectoDWA\templates\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace hardcoded static paths with django static tags (if not already done)
# Actually, the user's index.html might not have {% load static %} yet.
if '{% load static %}' not in content:
    content = '{% load static %}\n' + content
    # Replace href="plugins/ with href="{% static 'plugins/
    content = re.sub(r'href="(plugins/[^"]+)"', r'href="{% static \'\1\' %}"', content)
    content = re.sub(r'src="(plugins/[^"]+)"', r'src="{% static \'\1\' %}"', content)
    content = re.sub(r'href="(dist/[^"]+)"', r'href="{% static \'\1\' %}"', content)
    content = re.sub(r'src="(dist/[^"]+)"', r'src="{% static \'\1\' %}"', content)

# Find content-wrapper
start_content = content.find('<div class="content-wrapper">')
end_content = content.find('<footer class="main-footer">')

if start_content != -1 and end_content != -1:
    wrapper_content = content[start_content:end_content]
    
    # Create base.html
    base_html = content[:start_content] + """
  <div class="content-wrapper">
    <!-- Content Header (Page header) -->
    <div class="content-header">
      <div class="container-fluid">
        <div class="row mb-2">
          <div class="col-sm-6">
            <h1 class="m-0">{% block page_title %}{% endblock %}</h1>
          </div><!-- /.col -->
        </div><!-- /.row -->
      </div><!-- /.container-fluid -->
    </div>
    <!-- /.content-header -->

    <!-- Main content -->
    <section class="content">
      <div class="container-fluid">
        {% block content %}
        {% endblock %}
      </div>
    </section>
  </div>
""" + content[end_content:]

    # Add extra css/js blocks
    base_html = base_html.replace('</head>', '  {% block extra_css %}{% endblock %}\n</head>')
    base_html = base_html.replace('</body>', '  {% block extra_js %}{% endblock %}\n</body>')

    # Add the "Materias" link to the sidebar right after the dashboard links
    # Search for <ul class="nav nav-treeview"> inside the first nav-item
    insert_point = base_html.find('<li class="nav-header">EXAMPLES</li>')
    if insert_point != -1:
        materias_link = """
          <li class="nav-header">ESTUDIEN VAGOS</li>
          <li class="nav-item">
            <a href="{% url 'study:dashboard' %}" class="nav-link {% block nav_dashboard %}{% endblock %}">
              <i class="nav-icon fas fa-book"></i>
              <p>Materias / Dashboard</p>
            </a>
          </li>
"""
        base_html = base_html[:insert_point] + materias_link + base_html[insert_point:]

    with open(r'c:\Users\simed\Downloads\AdminLTE-3.2.0-rc\proyectoDWA\templates\base.html', 'w', encoding='utf-8') as f:
        f.write(base_html)

    # Now create home.html (the original dashboard content)
    home_html = """{% extends "base.html" %}
{% load static %}

{% block page_title %}Dashboard v1{% endblock %}

{% block content %}
""" + wrapper_content.replace('<div class="content-wrapper">', '').replace('<!-- /.content-wrapper -->', '') + """
{% endblock %}
"""
    with open(r'c:\Users\simed\Downloads\AdminLTE-3.2.0-rc\proyectoDWA\templates\home.html', 'w', encoding='utf-8') as f:
        f.write(home_html)
    
    print("Done generating base.html and home.html")
else:
    print("Could not find boundaries")
