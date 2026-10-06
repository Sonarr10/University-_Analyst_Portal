const portalCharts = (() => {
  const blue = '#2563EB', blueSoft = 'rgba(37,99,235,.65)', grid = 'rgba(17,24,39,.08)';
  Chart.defaults.font.family = 'Inter, sans-serif'; Chart.defaults.color = '#6B7280';
  const data = id => JSON.parse(document.getElementById(id).textContent);
  const measures = {departmentChart:'Students',majorChart:'Students',shiftChart:'Students',requiredMajorChart:'Class groups',scoreChart:'Average score',subjectChart:'Average score',gradeChart:'Records',attendanceSubjectChart:'Attendance %'};
  const options = (horizontal=false, measure='') => {
    const scales = {x:{beginAtZero:true,grid:{color:grid}},y:{beginAtZero:true,grid:{color:grid}}};
    scales[horizontal?'x':'y'].title = {display:Boolean(measure),text:measure};
    return {responsive:true,maintainAspectRatio:false,indexAxis:horizontal?'y':'x',plugins:{legend:{display:false}},scales};
  };
  const bar = (id, payload, horizontal=false, color=blue) => new Chart(document.getElementById(id), {type:'bar',data:{labels:payload.labels,datasets:[{data:payload.values,backgroundColor:color,borderRadius:4}]},options:options(horizontal,measures[id])});
  const doughnut = (id,payload,colors) => new Chart(document.getElementById(id),{type:'doughnut',data:{labels:payload.labels,datasets:[{data:payload.values,backgroundColor:colors,borderWidth:2,borderColor:'#FFFDF8'}]},options:{responsive:true,maintainAspectRatio:false,cutout:'68%',plugins:{legend:{position:'bottom'}}}});
  const capacity = (id,payload) => new Chart(document.getElementById(id),{type:'bar',data:{labels:payload.labels,datasets:[{label:'Required class groups',data:payload.required,backgroundColor:blue},{label:'Teacher capacity',data:payload.teachers,backgroundColor:'#94A3B8'}]},options:{...options(false,'Class groups'),plugins:{legend:{display:true,position:'bottom'}}}});
  const rooms = (id,payload) => new Chart(document.getElementById(id),{type:'bar',data:{labels:payload.labels,datasets:[{label:'Required rooms',data:payload.required,backgroundColor:blue},{label:'Shared active rooms',data:payload.rooms,backgroundColor:'#94A3B8'}]},options:{...options(false,'Rooms'),plugins:{legend:{display:true,position:'bottom'}}}});
  const scatter = (id, payload) => new Chart(document.getElementById(id), {
    type: 'scatter',
    data: {
      datasets: [{
        label: 'Student / Subject',
        data: payload,
        backgroundColor: blueSoft,
        pointRadius: 4,
        pointHoverRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: {padding: {right: 12, top: 8}},
      plugins: {
        legend: {display: false},
        tooltip: {
          callbacks: {
            title: items => {
              const point = items[0]?.raw;
              return point?.student_id ? `${point.student_id} - ${point.student_name}` : 'Attendance vs Score';
            },
            label: item => {
              const point = item.raw;
              return [
                point.subject || 'Matched student / subject',
                `Attendance: ${point.x}%`,
                `Score: ${point.y}`,
                ...(point.status ? [`Status: ${point.status}`] : [])
              ];
            }
          }
        }
      },
      scales: {
        x: {title: {display: true, text: 'Attendance %'}, min: 0, max: 105, ticks: {stepSize: 25, includeBounds: false}, grid: {color: grid}},
        y: {title: {display: true, text: 'Score'}, min: 0, max: 105, ticks: {stepSize: 25, includeBounds: false}, grid: {color: grid}}
      }
    }
  });
  return {
    dashboard(){bar('departmentChart',data('department-data'));bar('majorChart',data('major-data'),true);bar('shiftChart',data('shift-data'));bar('requiredMajorChart',data('required-major-data'));capacity('capacityChart',data('capacity-data'));if(document.getElementById('scoreChart')){bar('scoreChart',data('score-data'),true);doughnut('passChart',data('pass-data'),[blue,'#D8D4C8']);}if(document.getElementById('attendanceChart'))doughnut('attendanceChart',data('attendance-data'),['#16A34A','#D97706','#EA580C','#DC2626']);if(document.getElementById('scatterChart'))scatter('scatterChart',data('scatter-data'));},
    enrollment(){bar('departmentChart',data('department-data'));bar('majorChart',data('major-data'),true);bar('shiftChart',data('shift-data'));bar('requiredMajorChart',data('required-major-data'));capacity('capacityChart',data('capacity-data'));rooms('roomChart',data('room-data'));},
    performance(){bar('subjectChart',data('subject-data'),true);bar('gradeChart',data('grade-data'));},
    attendance(){bar('attendanceSubjectChart',data('attendance-subject-data'),true);doughnut('attendanceStatusChart',data('attendance-status-data'),['#16A34A','#D97706','#EA580C','#DC2626']);if(document.getElementById('attendanceScatterChart'))scatter('attendanceScatterChart',data('attendance-scatter-data'));}
  };
})();
