import os

filepath = r'c:\Users\simed\Downloads\AdminLTE-3.2.0-rc\proyectoDWA\study\templates\study\subject_detail.html'

clean_html = """{% extends "base.html" %}

{% block title %}{{ subject.name }}{% endblock %}
{% block nav_dashboard %}active{% endblock %}
{% block page_title %}Materia: {{ subject.name }}{% endblock %}

{% block content %}
<div class="row mb-3">
  <div class="col-12">
    <a href="{% url 'study:dashboard' %}" class="btn btn-default">
      <i class="fas fa-arrow-left"></i> Volver al Dashboard
    </a>
  </div>
</div>

<div class="row">
  <!-- Archivos -->
  <div class="col-md-7">
    <div class="card card-primary card-outline">
      <div class="card-header">
        <h3 class="card-title"><i class="fas fa-database"></i> Archivos de preguntas</h3>
        <div class="card-tools">
          {% if user.is_staff %}
          <label class="btn btn-primary btn-sm mb-0">
            <i class="fas fa-upload"></i> Subir JSON/XML
            <input type="file" id="fileUpload" accept=".json,.xml" multiple hidden data-url="{% url 'study:upload_file' subject.id %}">
          </label>
          {% endif %}
        </div>
      </div>
      <div class="card-body p-0">
        <table class="table table-striped">
          <thead>
            <tr>
              <th style="width: 40px">Sel</th>
              <th>Nombre del archivo</th>
              <th>Fecha</th>
            </tr>
          </thead>
          <tbody id="fileList">
            {% for file in files %}
            <tr>
              <td>
                <div class="icheck-primary">
                  <input type="checkbox" value="{{ file.id }}" id="fileCheck{{ file.id }}" class="file-checkbox">
                  <label for="fileCheck{{ file.id }}"></label>
                </div>
              </td>
              <td>{{ file.name }}</td>
              <td>{{ file.created_at|date:"d M Y" }}</td>
            </tr>
            {% empty %}
            <tr>
              <td colspan="3" class="text-center">No hay archivos para esta materia.</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Configuración de Sesión -->
  <div class="col-md-5">
    <div class="card card-success card-outline">
      <div class="card-header">
        <h3 class="card-title"><i class="fas fa-sliders-h"></i> Configurar Sesión</h3>
      </div>
      <div class="card-body">
        <form id="sessionForm" action="{% url 'study:quiz_runner' subject.id %}" method="get">
          <input type="hidden" name="files" id="selectedFiles" value="">
          
          <div class="form-group">
            <label>Cantidad de preguntas</label>
            <div class="btn-group btn-group-toggle d-flex" data-toggle="buttons">
              <label class="btn btn-outline-success">
                <input type="radio" name="count" id="count10" value="10" autocomplete="off"> 10
              </label>
              <label class="btn btn-outline-success">
                <input type="radio" name="count" id="count20" value="20" autocomplete="off"> 20
              </label>
              <label class="btn btn-outline-success">
                <input type="radio" name="count" id="count30" value="30" autocomplete="off"> 30
              </label>
              <label class="btn btn-outline-success active">
                <input type="radio" name="count" id="countAll" value="all" autocomplete="off" checked> Todas
              </label>
            </div>
          </div>

          <div class="form-group mt-4">
            <label>Modo de sesión</label>
            <div class="btn-group btn-group-toggle d-flex" data-toggle="buttons">
              <label class="btn btn-outline-info active">
                <input type="radio" name="mode" id="modeTest" value="test" autocomplete="off" checked> Práctica
              </label>
              <label class="btn btn-outline-info">
                <input type="radio" name="mode" id="modeStudy" value="study" autocomplete="off"> Repaso
              </label>
            </div>
          </div>

          <button type="submit" class="btn btn-success btn-lg btn-block mt-4" id="btnStart" disabled>
            <i class="fas fa-play"></i> Comenzar Sesión
          </button>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}

{% block extra_js %}
<!-- Include iCheck bootstrap for custom checkboxes -->
<link rel="stylesheet" href="{% static 'plugins/icheck-bootstrap/icheck-bootstrap.min.css' %}">
<script>
$(function () {
  // Update selected files for the form
  $('.file-checkbox').on('change', function() {
    var selected = [];
    $('.file-checkbox:checked').each(function() {
      selected.push($(this).val());
    });
    $('#selectedFiles').val(selected.join(','));
    
    // Enable/Disable start button
    if (selected.length > 0) {
      $('#btnStart').removeAttr('disabled');
    } else {
      $('#btnStart').attr('disabled', 'disabled');
    }
  });

  // Handle File Upload via AJAX
  $('#fileUpload').on('change', function(e) {
    var files = e.target.files;
    if (files.length === 0) return;
    
    var url = $(this).data('url');
    var formData = new FormData();
    formData.append('file', files[0]);
    
    // Quick simple upload
    $.ajax({
      url: url,
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(res) {
        if(res.success) {
          location.reload();
        } else {
          alert("Error al subir: " + res.error);
        }
      },
      error: function() {
        alert("Fallo de conexión al subir el archivo.");
      }
    });
  });
});
</script>
{% endblock %}
"""

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(clean_html)

print("Fixed subject_detail.html")
