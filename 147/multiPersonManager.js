class MultiPersonManager {
    constructor(maxPersons = 4) {
        this.maxPersons = maxPersons;
        this.persons = [];
        this.selectedPersonIndex = 0;
        this.personColors = [0x3498db, 0xe74c3c, 0x2ecc71, 0xf39c12];
        this.trackingThreshold = 0.3;
        this.historySize = 10;
        
        this.initializePersons();
    }
    
    initializePersons() {
        for (let i = 0; i < this.maxPersons; i++) {
            this.persons.push({
                id: i,
                active: i === 0,
                visible: i === 0,
                color: this.personColors[i],
                positionHistory: [],
                poseData: null,
                faceData: null,
                blendshapes: {},
                confidence: 0,
                lastSeen: 0,
                label: `人物 ${i + 1}`
            });
        }
    }
    
    processDetections(results, timestamp) {
        if (!results || !results.poseLandmarks) {
            this.updateLostPersons(timestamp);
            return this.persons;
        }
        
        const detections = this.extractDetections(results);
        
        for (const detection of detections) {
            const matchedPerson = this.findMatchingPerson(detection);
            
            if (matchedPerson) {
                this.updatePerson(matchedPerson, detection, timestamp);
            } else {
                const inactivePerson = this.findInactivePerson();
                if (inactivePerson) {
                    this.activatePerson(inactivePerson, detection, timestamp);
                }
            }
        }
        
        this.updateLostPersons(timestamp);
        return this.persons;
    }
    
    extractDetections(results) {
        const detections = [];
        
        if (results.poseLandmarks) {
            const centerPoint = this.calculateDetectionCenter(results.poseLandmarks);
            
            detections.push({
                center: centerPoint,
                poseLandmarks: results.poseLandmarks,
                faceLandmarks: results.faceLandmarks,
                leftHandLandmarks: results.leftHandLandmarks,
                rightHandLandmarks: results.rightHandLandmarks,
                smoothed: results.smoothed,
                confidence: this.calculateDetectionConfidence(results)
            });
        }
        
        return detections;
    }
    
    calculateDetectionCenter(poseLandmarks) {
        if (!poseLandmarks || poseLandmarks.length === 0) {
            return { x: 0.5, y: 0.5 };
        }
        
        const leftShoulder = poseLandmarks[11];
        const rightShoulder = poseLandmarks[12];
        const nose = poseLandmarks[0];
        
        if (leftShoulder && rightShoulder) {
            return {
                x: (leftShoulder.x + rightShoulder.x) / 2,
                y: (leftShoulder.y + rightShoulder.y) / 2
            };
        }
        
        if (nose) {
            return { x: nose.x, y: nose.y };
        }
        
        return { x: 0.5, y: 0.5 };
    }
    
    calculateDetectionConfidence(results) {
        let confidence = 0;
        let count = 0;
        
        if (results.poseLandmarks) {
            results.poseLandmarks.forEach(lm => {
                if (lm.visibility !== undefined) {
                    confidence += lm.visibility;
                    count++;
                }
            });
        }
        
        return count > 0 ? confidence / count : 0.5;
    }
    
    findMatchingPerson(detection) {
        let bestMatch = null;
        let bestDistance = Infinity;
        
        for (const person of this.persons) {
            if (!person.active || person.positionHistory.length === 0) continue;
            
            const lastPosition = person.positionHistory[person.positionHistory.length - 1];
            const distance = Math.sqrt(
                (detection.center.x - lastPosition.x) ** 2 +
                (detection.center.y - lastPosition.y) ** 2
            );
            
            if (distance < this.trackingThreshold && distance < bestDistance) {
                bestDistance = distance;
                bestMatch = person;
            }
        }
        
        return bestMatch;
    }
    
    findInactivePerson() {
        for (const person of this.persons) {
            if (!person.active) {
                return person;
            }
        }
        return null;
    }
    
    updatePerson(person, detection, timestamp) {
        person.positionHistory.push({ ...detection.center });
        if (person.positionHistory.length > this.historySize) {
            person.positionHistory.shift();
        }
        
        person.poseData = {
            poseLandmarks: detection.poseLandmarks,
            leftHandLandmarks: detection.leftHandLandmarks,
            rightHandLandmarks: detection.rightHandLandmarks,
            smoothed: detection.smoothed
        };
        
        person.faceData = detection.faceLandmarks;
        person.confidence = detection.confidence;
        person.lastSeen = timestamp;
        person.visible = true;
    }
    
    activatePerson(person, detection, timestamp) {
        person.active = true;
        person.positionHistory = [{ ...detection.center }];
        person.lastSeen = timestamp;
        person.confidence = detection.confidence;
        person.visible = true;
        
        person.poseData = {
            poseLandmarks: detection.poseLandmarks,
            leftHandLandmarks: detection.leftHandLandmarks,
            rightHandLandmarks: detection.rightHandLandmarks,
            smoothed: detection.smoothed
        };
        
        person.faceData = detection.faceLandmarks;
        
        this.log(`激活 ${person.label} (ID: ${person.id})`);
    }
    
    updateLostPersons(timestamp) {
        const timeout = 2000;
        
        for (const person of this.persons) {
            if (!person.active) continue;
            
            const timeSinceLastSeen = timestamp - person.lastSeen;
            
            if (timeSinceLastSeen > timeout) {
                this.deactivatePerson(person);
            }
        }
    }
    
    deactivatePerson(person) {
        person.active = false;
        person.visible = false;
        person.positionHistory = [];
        person.poseData = null;
        person.faceData = null;
        person.confidence = 0;
        
        this.log(`失去追踪 ${person.label} (ID: ${person.id})`);
    }
    
    selectPerson(index) {
        if (index < 0 || index >= this.maxPersons) return;
        
        this.persons[this.selectedPersonIndex].selected = false;
        this.selectedPersonIndex = index;
        this.persons[index].selected = true;
        
        this.log(`选中 ${this.persons[index].label}`);
        document.getElementById('selectedPerson').textContent = this.persons[index].label;
    }
    
    getSelectedPerson() {
        return this.persons[this.selectedPersonIndex];
    }
    
    getActivePersons() {
        return this.persons.filter(p => p.active);
    }
    
    getActiveCount() {
        return this.persons.filter(p => p.active).length;
    }
    
    setPersonBlendshapes(personIndex, blendshapes) {
        if (this.persons[personIndex]) {
            this.persons[personIndex].blendshapes = blendshapes;
        }
    }
    
    getPersonData(personIndex) {
        return this.persons[personIndex];
    }
    
    getSmoothedPosition(personIndex) {
        const person = this.persons[personIndex];
        if (!person || person.positionHistory.length === 0) {
            return null;
        }
        
        const history = person.positionHistory;
        const avgX = history.reduce((sum, p) => sum + p.x, 0) / history.length;
        const avgY = history.reduce((sum, p) => sum + p.y, 0) / history.length;
        
        return { x: avgX, y: avgY };
    }
    
    log(message) {
        const debugInfo = document.getElementById('debugInfo');
        if (debugInfo) {
            const timestamp = new Date().toLocaleTimeString();
            const newContent = `<div style="color: #ff9800">[${timestamp}] 多人追踪: ${message}</div>` + debugInfo.innerHTML;
            debugInfo.innerHTML = newContent.substring(0, 5000);
        }
    }
    
    getDebugInfo() {
        return this.persons.map(person => ({
            id: person.id,
            label: person.label,
            active: person.active,
            confidence: (person.confidence * 100).toFixed(1),
            visible: person.visible
        }));
    }
}