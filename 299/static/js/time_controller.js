class TimeController {
    constructor(options) {
        this.totalSteps = options.totalSteps || 72;
        this.currentStep = 0;
        this.isPlaying = false;
        this.playInterval = null;
        this.playSpeed = 1000;
        this.onTimeChange = options.onTimeChange || (() => {});
        this.startTime = null;
        
        this.initElements();
        this.bindEvents();
    }

    initElements() {
        this.slider = document.getElementById('timeSlider');
        this.playBtn = document.getElementById('playBtn');
        this.playIcon = document.getElementById('playIcon');
        this.pauseIcon = document.getElementById('pauseIcon');
        this.prevBtn = document.getElementById('prevBtn');
        this.nextBtn = document.getElementById('nextBtn');
        this.speedSelect = document.getElementById('speedSelect');
        this.startTimeLabel = document.getElementById('startTimeLabel');
        this.endTimeLabel = document.getElementById('endTimeLabel');
        this.currentForecastTime = document.getElementById('currentForecastTime');
        this.forecastHour = document.getElementById('forecastHour');
        
        this.slider.max = this.totalSteps - 1;
    }

    bindEvents() {
        this.slider.addEventListener('input', (e) => {
            this.setStep(parseInt(e.target.value));
        });

        this.playBtn.addEventListener('click', () => {
            this.togglePlay();
        });

        this.prevBtn.addEventListener('click', () => {
            this.prevStep();
        });

        this.nextBtn.addEventListener('click', () => {
            this.nextStep();
        });

        this.speedSelect.addEventListener('change', (e) => {
            this.setSpeed(parseInt(e.target.value));
        });
    }

    setStartTime(startTime) {
        this.startTime = new Date(startTime);
        this.updateTimeLabels();
    }

    updateTimeLabels() {
        if (!this.startTime) return;

        const endTime = new Date(this.startTime.getTime() + (this.totalSteps - 1) * 3600000);
        this.startTimeLabel.textContent = this.formatTime(this.startTime);
        this.endTimeLabel.textContent = this.formatTime(endTime);
        this.updateCurrentTime();
    }

    updateCurrentTime() {
        if (!this.startTime) return;

        const currentTime = new Date(this.startTime.getTime() + this.currentStep * 3600000);
        this.currentForecastTime.textContent = this.formatDateTime(currentTime);
        this.forecastHour.textContent = `T+${this.currentStep}h`;
    }

    formatTime(date) {
        return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours().toString().padStart(2, '0')}:00`;
    }

    formatDateTime(date) {
        return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:00`;
    }

    setStep(step) {
        this.currentStep = Math.max(0, Math.min(this.totalSteps - 1, step));
        this.slider.value = this.currentStep;
        this.updateCurrentTime();
        this.onTimeChange(this.currentStep);
    }

    prevStep() {
        if (this.currentStep > 0) {
            this.setStep(this.currentStep - 1);
        }
    }

    nextStep() {
        if (this.currentStep < this.totalSteps - 1) {
            this.setStep(this.currentStep + 1);
        } else {
            this.setStep(0);
        }
    }

    togglePlay() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }

    play() {
        this.isPlaying = true;
        this.playIcon.classList.add('hidden');
        this.pauseIcon.classList.remove('hidden');
        
        this.playInterval = setInterval(() => {
            this.nextStep();
        }, this.playSpeed);
    }

    pause() {
        this.isPlaying = false;
        this.playIcon.classList.remove('hidden');
        this.pauseIcon.classList.add('hidden');
        
        if (this.playInterval) {
            clearInterval(this.playInterval);
            this.playInterval = null;
        }
    }

    setSpeed(speed) {
        this.playSpeed = speed;
        if (this.isPlaying) {
            this.pause();
            this.play();
        }
    }

    getCurrentStep() {
        return this.currentStep;
    }
}
