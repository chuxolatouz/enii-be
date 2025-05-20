from jinja2 import Template
import pdfkit

def generar_acta_finalizacion_pdf(proyecto, movements=[], logs=[], budgets=[]):
    html_template = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>Acta de Finalización</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1, h2 { text-align: center; }
            .section { margin-bottom: 20px; }
            .list { margin-left: 20px; }
        </style>
    </head>
    <body>
        <h1>Acta de Finalización del Proyecto</h1>
        <div class="section">
            <p><strong>Nombre:</strong> {{ nombre }}</p>
            <p><strong>Descripción:</strong> {{ descripcion }}</p>
            <p><strong>Fecha de Inicio:</strong> {{ fecha_inicio }}</p>
            <p><strong>Fecha de Finalización:</strong> {{ fecha_fin }}</p>
        </div>

        <div class="section">
            <h2>Objetivo General</h2>
            <p>{{ objetivo_general }}</p>
        </div>

        <div class="section">
            <h2>Objetivos Específicos</h2>
            {% if objetivos_especificos %}
                <ul class="list">
                    {% for objetivo in objetivos_especificos %}
                        <li>{{ objetivo }}</li>
                    {% endfor %}
                </ul>
            {% else %}
                <p>No se han definido objetivos específicos.</p>
            {% endif %}
        </div>

        <div class="section">
            <h2>Balance</h2>
            <p><strong>Saldo inicial:</strong> ${{ saldo_inicial }}</p>
            <p><strong>Saldo final:</strong> ${{ saldo_final }}</p>
        </div>

        <div class="section">
            <h2>Movimientos Monetarios</h2>
            {% if movements %}
                <ul class="list">
                    {% for mov in movements %}
                        <li>{{ mov.type }} por ${{ "%.2f"|format(mov.amount) }} - Usuario: {{ mov.user }}</li>
                    {% endfor %}
                </ul>
            {% else %}
                <p>No se registraron movimientos monetarios.</p>
            {% endif %}
        </div>

        <div class="section">
            <h2>Logs del Proyecto</h2>
            {% if logs %}
                <ul class="list">
                    {% for log in logs %}
                        <li>{{ log.fecha }} - {{ log.mensaje }}</li>
                    {% endfor %}
                </ul>
            {% else %}
                <p>No se registraron logs.</p>
            {% endif %}
        </div>

        <div class="section">
            <h2>Presupuestos Asociados</h2>
            {% if budgets %}
                <ul class="list">
                    {% for budget in budgets %}
                        <li>{{ budget.descripcion }} - ${{ "%.2f"|format(budget.monto_aprobado or 0) }}</li>
                    {% endfor %}
                </ul>
            {% else %}
                <p>No se registraron presupuestos asociados.</p>
            {% endif %}
        </div>
    </body>
    </html>
    """

    html = Template(html_template).render(
        nombre=proyecto.get("nombre", ""),
        descripcion=proyecto.get("descripcion", ""),
        fecha_inicio=str(proyecto.get("fecha_inicio", "")),
        fecha_fin=str(proyecto.get("fecha_fin", "")),
        objetivo_general=proyecto.get("objetivo_general", "No especificado"),
        objetivos_especificos=proyecto.get("objetivos_especificos", []),
        saldo_inicial=proyecto.get("balance_inicial", 0),
        saldo_final=proyecto.get("balance", 0),
        movements=movements,
        logs=logs,
        budgets=budgets
    )

    pdf_bytes = pdfkit.from_string(html, False)
    return pdf_bytes
