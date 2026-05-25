class PollutantPopup {
    constructor() {
        this.popup = document.getElementById('pollutantPopup');
        this.closeBtn = document.getElementById('closePopup');
        this.bindEvents();
    }

    bindEvents() {
        this.closeBtn.addEventListener('click', () => {
            this.hide();
        });
    }

    show(data) {
        document.getElementById('popupCoords').textContent = 
            `经度: ${data.lon.toFixed(4)}°E, 纬度: ${data.lat.toFixed(4)}°N`;
        
        const aqiValue = document.getElementById('aqiValue');
        const aqiLevel = document.getElementById('aqiLevel');
        
        aqiValue.textContent = data.aqi;
        aqiValue.style.color = data.aqi_color;
        
        aqiLevel.textContent = data.aqi_level;
        aqiLevel.style.background = data.aqi_color;
        aqiLevel.style.color = '#fff';
        
        document.getElementById('primaryPollutant').textContent = 
            this.formatPollutantName(data.primary_pollutant);
        
        document.getElementById('pm25Value').textContent = 
            `${data.pollutants.PM25.value.toFixed(1)} ${data.pollutants.PM25.unit}`;
        document.getElementById('pm10Value').textContent = 
            `${data.pollutants.PM10.value.toFixed(1)} ${data.pollutants.PM10.unit}`;
        document.getElementById('o3Value').textContent = 
            `${data.pollutants.O3.value.toFixed(1)} ${data.pollutants.O3.unit}`;
        document.getElementById('no2Value').textContent = 
            `${data.pollutants.NO2.value.toFixed(1)} ${data.pollutants.NO2.unit}`;
        document.getElementById('so2Value').textContent = 
            `${data.pollutants.SO2.value.toFixed(1)} ${data.pollutants.SO2.unit}`;
        document.getElementById('coValue').textContent = 
            `${data.pollutants.CO.value.toFixed(2)} ${data.pollutants.CO.unit}`;
        
        this.popup.classList.remove('hidden');
    }

    hide() {
        this.popup.classList.add('hidden');
    }

    formatPollutantName(name) {
        const names = {
            'PM25': 'PM2.5',
            'PM10': 'PM10',
            'O3': 'O₃',
            'NO2': 'NO₂',
            'SO2': 'SO₂',
            'CO': 'CO'
        };
        return names[name] || name;
    }
}
