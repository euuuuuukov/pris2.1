# app.py – расширенная версия с отображением вероятности (цвет вероятности изменён на оранжевый)
from flask import Flask, request, render_template_string, redirect, url_for
from datetime import datetime
import json

app = Flask(__name__)

# Хранилище данных (все введённые записи)
records = []


def calculate_fire_risk(temp, humidity, co2):
    """
    Расчёт вероятности пожара на основе эмпирических правил.
    Чем выше температура и CO2 и чем ниже влажность, тем больше риск.
    Формула даёт значение в диапазоне [0, 1].
    """
    temp_factor = max(0, min(1, (temp - 15) / 25))  # 15..40 -> 0..1
    humidity_factor = max(0, min(1, (50 - humidity) / 50))  # 50..0 -> 0..1
    co2_factor = max(0, min(1, (co2 - 400) / 600))  # 400..1000 -> 0..1
    risk = 0.4 * temp_factor + 0.4 * humidity_factor + 0.2 * co2_factor
    return min(1, max(0, risk))


def risk_level(risk):
    """Преобразование числовой вероятности в текстовую оценку угрозы."""
    if risk < 0.3:
        return "Низкая"
    if risk < 0.6:
        return "Средняя"
    return "Высокая"


@app.route('/', methods=['GET'])
def index():
    """Главная страница: форма ввода, таблица последних записей, график и оценка риска."""
    # Берём последние 10 записей (или все, если их меньше)
    last_10 = records[-10:] if records else []

    # Подготовка данных для графика (временные метки, температура, CO2, риск)
    if last_10:
        labels = [r['timestamp'].strftime('%H:%M:%S') for r in last_10]
        temp_data = [r['temperature'] for r in last_10]
        co2_data = [r['co2'] for r in last_10]
        # Вычисляем риск для каждой записи, чтобы отобразить на графике
        risk_data = [calculate_fire_risk(r['temperature'], r['humidity'], r['co2']) for r in last_10]
        # Обогащаем записи для таблицы полем risk (чтобы не вычислять дважды)
        enriched_records = []
        for r, risk in zip(last_10, risk_data):
            enriched_record = r.copy()
            enriched_record['risk'] = risk
            enriched_records.append(enriched_record)
    else:
        labels = temp_data = co2_data = risk_data = []
        enriched_records = []

    # Расчёт риска на основе самой последней записи (для карточки)
    if records:
        last = records[-1]
        current_risk = calculate_fire_risk(last['temperature'], last['humidity'], last['co2'])
        current_risk_text = risk_level(current_risk)
    else:
        current_risk = None
        current_risk_text = "Нет данных"

    return render_template_string(TEMPLATE,
                                  records=enriched_records,
                                  labels=json.dumps(labels),
                                  temp_data=json.dumps(temp_data),
                                  co2_data=json.dumps(co2_data),
                                  risk_data=json.dumps(risk_data),
                                  current_risk=current_risk,
                                  current_risk_text=current_risk_text)


@app.route('/add', methods=['POST'])
def add_record():
    """Обработка отправки формы: добавление новой записи в историю."""
    try:
        temp = float(request.form['temperature'])
        humidity = float(request.form['humidity'])
        co2 = float(request.form['co2'])
        # Простейшая проверка диапазонов (чтобы избежать явно некорректных данных)
        if not (-50 < temp < 100) or not (0 <= humidity <= 100) or not (0 < co2 < 10000):
            raise ValueError
        record = {
            'temperature': temp,
            'humidity': humidity,
            'co2': co2,
            'timestamp': datetime.now()  # фиксируем время измерения
        }
        records.append(record)
    except (ValueError, KeyError):
        # В случае ошибки просто игнорируем запись (можно добавить flash-сообщение)
        pass
    return redirect(url_for('index'))


# HTML-шаблон с использованием Bootstrap 5 и Chart.js
TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EcoGuardian – Мониторинг рисков</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container mt-4">
        <h1 class="mb-4">🌍 EcoGuardian: Анализ экологических рисков</h1>

        <!-- Карточка с формой ввода -->
        <div class="card mb-4">
            <div class="card-header">📡 Добавить показания датчиков</div>
            <div class="card-body">
                <form action="/add" method="post">
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label for="temperature" class="form-label">Температура (°C)</label>
                            <input type="number" step="0.1" class="form-control" id="temperature" name="temperature" required>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label for="humidity" class="form-label">Влажность (%)</label>
                            <input type="number" step="0.1" class="form-control" id="humidity" name="humidity" min="0" max="100" required>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label for="co2" class="form-label">CO₂ (ppm)</label>
                            <input type="number" step="1" class="form-control" id="co2" name="co2" min="0" required>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary">Отправить</button>
                </form>
            </div>
        </div>

        <!-- Карточка с текущей оценкой риска пожара -->
        <div class="card mb-4">
            <div class="card-header">🔥 Оценка риска пожара (по последним данным)</div>
            <div class="card-body">
                {% if current_risk is not none %}
                    <h3>Вероятность: {{ "%.2f"|format(current_risk) }}</h3>
                    <p>Уровень угрозы: <strong>{{ current_risk_text }}</strong></p>
                {% else %}
                    <p class="text-muted">Нет данных для оценки</p>
                {% endif %}
            </div>
        </div>

        <!-- Карточка с графиком динамики параметров (теперь с вероятностью) -->
        <div class="card mb-4">
            <div class="card-header">📈 Динамика температуры, CO₂ и вероятности пожара (последние 10 измерений)</div>
            <div class="card-body">
                <canvas id="ecoChart" width="400" height="200"></canvas>
            </div>
        </div>

        <!-- Карточка с таблицей последних записей (добавлен столбец вероятности) -->
        <div class="card mb-4">
            <div class="card-header">📋 Последние 10 записей</div>
            <div class="card-body">
                <table class="table table-striped table-hover">
                    <thead>
                        <tr>
                            <th>Время</th>
                            <th>Температура (°C)</th>
                            <th>Влажность (%)</th>
                            <th>CO₂ (ppm)</th>
                            <th>Вероятность пожара</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for record in records %}
                        <tr>
                            <td>{{ record.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                            <td>{{ record.temperature }}</td>
                            <td>{{ record.humidity }}</td>
                            <td>{{ record.co2 }}</td>
                            <td>{{ "%.3f"|format(record.risk) }}</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="5" class="text-center text-muted">Пока нет записей</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Скрипт для построения графика с тремя осями Y -->
    <script>
        const ctx = document.getElementById('ecoChart').getContext('2d');
        const labels = {{ labels | safe }};
        const tempData = {{ temp_data | safe }};
        const co2Data = {{ co2_data | safe }};
        const riskData = {{ risk_data | safe }};

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Температура (°C)',
                        data: tempData,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        yAxisID: 'y-temp',
                    },
                    {
                        label: 'CO₂ (ppm)',
                        data: co2Data,
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        yAxisID: 'y-co2',
                    },
                    {
                        label: 'Вероятность пожара',
                        data: riskData,
                        borderColor: 'rgb(255, 159, 64)',   // изменён на оранжевый
                        backgroundColor: 'rgba(255, 159, 64, 0.2)',
                        yAxisID: 'y-risk',
                    }
                ]
            },
            options: {
                responsive: true,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    'y-temp': {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Температура (°C)' }
                    },
                    'y-co2': {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'CO₂ (ppm)' },
                        grid: { drawOnChartArea: false }
                    },
                    'y-risk': {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Вероятность пожара' },
                        min: 0,
                        max: 1,
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    </script>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True)