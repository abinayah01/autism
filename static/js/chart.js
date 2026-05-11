const ctx = document.getElementById('weeklyChart').getContext('2d');

const weeklyData = {
  labels: ['Week 1','Week 2','Week 3','Week 4','Week 5','Week 6','Week 7'],
  datasets: [{
    label: 'Progress (%)',
    data: [25, 40, 55, 70, 80, 90, 100],
    backgroundColor: 'rgba(15, 26, 58, 0.2)',
    borderColor: 'rgba(15, 26, 58, 1)',
    borderWidth: 3,
    fill: true,
    tension: 0.4,
    pointBackgroundColor: '#0f1a3a',
    pointRadius: 6
  }]
};

const config = {
  type: 'line',
  data: weeklyData,
  options: {
    responsive: true,
    plugins: {
      legend: {
        display: true,
        position: 'top'
      },
      tooltip: {
        mode: 'index',
        intersect: false
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: value => value + '%'
        }
      }
    }
  }
};

const weeklyChart = new Chart(ctx, config);
